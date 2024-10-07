import json
import re
from pathlib import Path

import chardet

from lib.services import output
from lib.utilities.exceptions import ScriptSyntaxError

from .syntax import script_syntax


class Token(dict):
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
    def __init__(self, file_name=None):
        self.file_name = file_name
        self.tokens = []
        self.section_commented = False
        self.line_number = 1
        self.cur_line = None
        self.cur_groupdict = {}

    def parse_line(self, line):
        self.cur_line = rf"{line}"
        m = script_syntax.line_pattern.match(self.cur_line)
        self.cur_groupdict = m.groupdict()
        if self.section_commented and self.cur_groupdict.get("section") is None:
            # commented lines are not included in tokens
            return []
        for line_type, matched_content in self.cur_groupdict.items():
            if matched_content is not None and script_syntax.is_a_valid_line_type(
                line_type
            ):
                func = getattr(self, line_type)
                func()
        self._dump_to_file()
        return self.tokens

    def add_token(self, _type, data):
        token = Token(_type, data, self.line_number)
        self.tokens.append(token)

    def commented_section(self):
        self.section_commented = True

    def commented_line(self):
        pass

    def section(self):
        self.section_commented = False
        section_name = self.cur_groupdict["section_name"]
        self.add_token("section", section_name)

    def command(self):
        self.add_token("command", self.cur_line)

    def comment(self):
        self.add_token("comment", self.cur_groupdict["comment_content"])

    def include(self):
        self.add_token("include", self.cur_groupdict["file_name"])

    def _process_token(self, matched_group_dict):
        for token_type, matched_content in matched_group_dict.items():
            if matched_content is not None and script_syntax.is_a_valid_token_type(
                token_type
            ):
                if token_type == "variable":
                    variable_name = matched_group_dict.get("variable_name", None)
                    self.add_token(token_type, variable_name)
                elif token_type == "number":
                    number = matched_group_dict.get("number_content", None)
                    self.add_token(token_type, number)
                elif token_type == "expect_double":
                    double_quote_str = matched_group_dict.get("double_quote_str", None)
                    self.add_token("identifier", "-e")
                    self.add_token("string", double_quote_str)
                elif token_type == "expect_single":
                    single_quote_str = matched_group_dict.get("single_quote_str", None)
                    self.add_token("identifier", "-e")
                    self.add_token("string", single_quote_str)
                elif token_type == "expect_string":
                    expect_str = matched_group_dict.get("expect_str", None)
                    self.add_token("identifier", "-e")
                    self.add_token("string", expect_str)
                else:
                    self.add_token(token_type, matched_content)

    def tokenize(self, string):
        pos = 0
        while pos < len(string):
            m = script_syntax.token_pattern.match(string, pos)
            if m is None:
                raise ScriptSyntaxError(
                    f"{self.line_number}: '{string[pos:]}' unsupported token"
                )
            matched_group_dict = m.groupdict()
            self._process_token(matched_group_dict)
            pos = m.end()

    def parse_api(self, _type, string):
        m = re.match(
            r"(?P<first>.+?)\s+(?P<leftover>.+)|(?P<second>.+)$",
            string,
        )
        if m.group("leftover") is not None:
            self.add_token(_type, m.group("first"))
            self.tokenize(m.group("leftover"))
        else:
            self.add_token(_type, m.group("second"))

    def api(self):
        self.parse_api("api", self.cur_line)

    def statement(self):
        content = self.cur_groupdict["statement_content"].strip()
        m = re.match(
            r"(?P<first>.+?)\s+(?P<leftover>.+)|(?P<second>.+)$",
            content,
        )
        if m.group("leftover") is not None:
            self.add_token("keyword", m.group("first"))
            if m.group("first") in ["intset", "strset", "listset"]:
                parts = m.group("leftover").split(maxsplit=1)
                self.add_token("identifier", parts[0])
                self.add_token("identifier", parts[1])
            elif m.group("first") in ["if", "elseif", "until", "intchange", "endwhile"]:
                self.tokenize(m.group("leftover"))
            else:
                self.add_token("identifier", m.group("leftover"))
        else:
            self.add_token("keyword", m.group("second"))
            if m.group("second") in ["loop", "while"]:
                self.add_token("identifier", "")

    def read(self):
        with open(self.file_name, "rb") as file:
            content = file.read()

        if not content:
            return ""

        encoding_info = chardet.detect(content)
        detected_encoding = encoding_info["encoding"] or "utf-8"
        try:
            content_decoded = content.decode(detected_encoding, errors="ignore")
        except UnicodeDecodeError:
            print(f"*** Unable to detect the encoding of file {self.file_name}. ***")
            content_decoded = ""
        return content_decoded

    def parse(self):
        content = self.read()
        lines = content.splitlines()
        for line in lines:
            line = line.strip()
            if line:
                self.parse_line(line)
            self.line_number += 1
        return self.tokens, lines

    def _compose_token_file_name(self):
        return output.compose_compiled_file(Path(self.file_name).stem, "tokens.json")

    def _dump_to_file(self):
        token_file = self._compose_token_file_name()
        with open(token_file, "w", encoding="utf-8") as f:
            json.dump({"tokens": self.tokens}, f, indent=4)
