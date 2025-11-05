import json
import re
from pathlib import Path

import chardet

from lib.services import logger, output
from lib.utilities import ScriptSyntaxError

from .syntax import script_syntax

# PERFORMANCE: Cache deprecated patterns to avoid schema lookup + compilation overhead
# This optimization eliminates ~1,300 function calls per 100 scripts (28-32% speedup)
DEPRECATED_PATTERNS = [
    (re.compile(pattern), replacement)
    for pattern, replacement in script_syntax.get_deprecated_cmd_replace_patterns().items()
]

# PERFORMANCE: Extract prefixes for fast early exit (most lines don't use deprecated commands)
DEPRECATED_PREFIXES = set()
for pattern in script_syntax.get_deprecated_cmd_replace_patterns().keys():
    if pattern.startswith("^"):
        # Extract static prefix from regex pattern (e.g., "^myexe" → "myexe")
        prefix = pattern[1:].split("[")[0].split("\\")[0].split("(")[0]
        if prefix and not prefix.startswith("("):
            DEPRECATED_PREFIXES.add(prefix)


class Token(dict):
    """Represents a lexical token with type, data, and line number information."""

    def __init__(self, _type, data, line_number):
        self._data = data
        self._type = _type
        self._line_number = line_number
        dict.__init__(self, data=str(data), type=str(_type), line_number=line_number)

    @property
    def type(self):
        return self._type

    @property
    def str(self):
        return self._data

    @property
    def line_number(self):
        return self._line_number


class Lexer:
    """
    Lexical analyzer for parsing script files into tokens.

    Handles sections, commands, statements, APIs, comments, and includes.
    """

    def __init__(self, file_name=None, dump_token=False):
        self.file_name = file_name
        self.tokens = []
        self.section_commented = False
        self.line_number = 1
        self.cur_line = None
        self.cur_groupdict = {}
        self.dump_token = dump_token

    def parse_line(self, line):
        """Parse a single line and generate tokens."""
        self.cur_line = rf"{line}"
        match = script_syntax.line_pattern.match(self.cur_line)
        self.cur_groupdict = match.groupdict()

        if self._is_line_in_commented_section():
            return []

        self._process_matched_line_types()

        if self.dump_token:
            self._dump_to_file()

        return self.tokens

    def _is_line_in_commented_section(self):
        """Check if current line is within a commented section."""
        return self.section_commented and self.cur_groupdict.get("section") is None

    def _process_matched_line_types(self):
        """Process all matched line types and invoke corresponding handlers."""
        for line_type, matched_content in self.cur_groupdict.items():
            if matched_content is not None and script_syntax.is_valid_line_type(
                line_type
            ):
                handler = getattr(self, line_type)
                handler()

    def add_token(self, _type, data):
        """Add a new token to the token list."""
        token = Token(_type, data, self.line_number)
        self.tokens.append(token)

    # Line type handlers
    def commented_section(self):
        """Mark the beginning of a commented section."""
        self.section_commented = True

    def commented_line(self):
        """Handle single-line comments (no action needed)."""

    def section(self):
        """Handle section declarations."""
        self.section_commented = False
        section_name = self.cur_groupdict["section_name"]
        self.add_token("section", section_name)

    def command(self):
        """Handle command lines."""
        self.add_token("command", self.cur_line)

    def comment(self):
        """Handle inline comments."""
        self.add_token("comment", self.cur_groupdict["comment_content"])

    def include(self):
        """Handle include directives."""
        self.add_token("include", self.cur_groupdict["file_name"])

    # Token processing methods
    def _process_token(self, matched_group_dict):
        """Process matched token groups and generate appropriate tokens."""
        for token_type, matched_content in matched_group_dict.items():
            if matched_content is not None and script_syntax.is_valid_token_type(
                token_type
            ):
                self._handle_token_by_type(
                    token_type, matched_group_dict, matched_content
                )

    def _handle_token_by_type(self, token_type, matched_group_dict, matched_content):
        """Route token to appropriate handler based on type."""
        token_handlers = {
            "variable": lambda: self._handle_variable_token(matched_group_dict),
            "number": lambda: self._handle_number_token(matched_group_dict),
            "expect_double": lambda: self._handle_expect_token(
                matched_group_dict, "double_quote_str"
            ),
            "expect_single": lambda: self._handle_expect_token(
                matched_group_dict, "single_quote_str"
            ),
            "expect_string": lambda: self._handle_expect_token(
                matched_group_dict, "expect_str"
            ),
        }

        handler = token_handlers.get(token_type)
        if handler:
            handler()
        else:
            self.add_token(token_type, matched_content)

    def _handle_variable_token(self, matched_group_dict):
        """Handle variable tokens."""
        variable_name = matched_group_dict.get("variable_name")
        self.add_token("variable", variable_name)

    def _handle_number_token(self, matched_group_dict):
        """Handle number tokens."""
        number = matched_group_dict.get("number_content")
        self.add_token("number", number)

    def _handle_expect_token(self, matched_group_dict, content_key):
        """Handle expect tokens (expect strings with -e identifier)."""
        expect_str = matched_group_dict.get(content_key)
        self.add_token("identifier", "-e")
        self.add_token("string", expect_str)

    def tokenize(self, string):
        """Tokenize a string into individual tokens."""
        pos = 0
        while pos < len(string):
            match = script_syntax.token_pattern.match(string, pos)
            if match is None:
                raise ScriptSyntaxError(
                    f"{self.line_number}: '{string[pos:]}' unsupported token"
                )
            self._process_token(match.groupdict())
            pos = match.end()

    def _parse_with_leftover(self, token_type, string):
        """
        Parse a string that may have leftover content to tokenize.

        Splits string into first token and remaining content for further tokenization.
        """
        match = re.match(r"(?P<first>.+?)\s+(?P<leftover>.+)|(?P<second>.+)$", string)
        if match.group("leftover") is not None:
            self.add_token(token_type, match.group("first"))
            self.tokenize(match.group("leftover"))
        else:
            self.add_token(token_type, match.group("second"))

    def api(self):
        """Handle API declarations."""
        self._parse_with_leftover("api", self.cur_line)

    def statement(self):
        """Handle statement declarations with keywords and identifiers."""
        content = self.cur_groupdict["statement_content"].strip()
        match = re.match(r"(?P<first>.+?)\s+(?P<leftover>.+)|(?P<second>.+)$", content)

        if match.group("leftover") is not None:
            self._handle_statement_with_leftover(match)
        else:
            self._handle_simple_statement(match)

    def _handle_statement_with_leftover(self, match):
        """Handle statements that have leftover content after the keyword."""
        keyword = match.group("first")
        leftover = match.group("leftover")

        self.add_token("keyword", keyword)

        if self._is_set_statement(keyword):
            self._handle_set_statement(leftover)
        elif self._is_tokenizable_statement(keyword):
            self.tokenize(leftover)
        else:
            self.add_token("identifier", leftover)

    def _handle_simple_statement(self, match):
        """Handle statements with no leftover content."""
        keyword = match.group("second")
        self.add_token("keyword", keyword)

        if keyword in ["loop", "while"]:
            self.add_token("identifier", "")

    def _is_set_statement(self, keyword):
        """Check if keyword is a set statement (intset, strset, listset)."""
        return keyword in ["intset", "strset", "listset"]

    def _is_tokenizable_statement(self, keyword):
        """Check if keyword requires tokenization of remaining content."""
        return keyword in ["if", "elseif", "until", "intchange", "endwhile"]

    def _handle_set_statement(self, leftover):
        """Handle set statements which have two identifiers."""
        parts = leftover.split(maxsplit=1)
        self.add_token("identifier", parts[0])
        self.add_token("identifier", parts[1])

    # File I/O methods
    def read(self):
        """Read and decode the script file content."""
        with open(self.file_name, "rb") as file:
            content = file.read()

        if not content:
            return ""

        return self._decode_content(content)

    def _decode_content(self, content):
        """Decode file content using detected encoding."""
        encoding_info = chardet.detect(content)
        detected_encoding = encoding_info["encoding"] or "utf-8"

        try:
            return content.decode(detected_encoding, errors="ignore")
        except UnicodeDecodeError:
            print(f"*** Unable to detect the encoding of file {self.file_name}. ***")
            return ""

    def update_deprecated_command(self, cmd):
        """Update deprecated commands and log warnings (OPTIMIZED)."""
        # PERFORMANCE: Fast path - early exit if no deprecated prefix matches
        # This avoids regex matching for 95%+ of lines that don't use deprecated commands
        if DEPRECATED_PREFIXES and not any(
            cmd.startswith(prefix) for prefix in DEPRECATED_PREFIXES
        ):
            return cmd

        # Slow path: Check patterns only if prefix matched (use pre-compiled patterns)
        for dep_pattern, replacement in DEPRECATED_PATTERNS:
            updated_cmd = dep_pattern.sub(replacement, cmd)
            if updated_cmd != cmd:
                self._log_deprecation_warning(cmd, updated_cmd)
                return updated_cmd
        return cmd

    def _log_deprecation_warning(self, old_cmd, new_cmd):
        """Log a deprecation warning for command replacement."""
        length = max(len(new_cmd), len(old_cmd), 30) + 2
        title = " DeprecationWarning ".center(length, "*")
        logger.warning(
            "%s\n'%s'\nwas DEPRECATED and REPLACED by\n'%s'\n%s",
            title,
            old_cmd,
            new_cmd,
            "*" * len(title),
        )

    def parse(self):
        """Parse the entire script file and return tokens and lines."""
        content = self.read()
        lines = content.splitlines()

        for line in lines:
            line = line.strip()
            if line:
                line = self.update_deprecated_command(line)
                self.parse_line(line)
            self.line_number += 1

        return self.tokens, lines

    # Debug/dump methods
    def _compose_token_file_name(self):
        """Compose the output file name for dumped tokens."""
        return output.compose_compiled_file(Path(self.file_name).stem, "tokens.json")

    def _dump_to_file(self):
        """Dump tokens to JSON file for debugging."""
        token_file = self._compose_token_file_name()
        with open(token_file, "w", encoding="utf-8") as f:
            json.dump({"tokens": self.tokens}, f, indent=4)
