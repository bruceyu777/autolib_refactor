import re
from collections import UserString

from lib.utilities.exceptions import ParseException

KEYWORDS = (
    "if",
    "elseif",
    "fi",
    "intset",
    "loop",
    "intchange",
    "until",
    "setvar",
    "comment",
    "varexpect",
    "keep_running",
    "report",
    "expect",
    "Comment",
    "sleep",
    "forcelogin",
    "setlicense",
    "clearbuff",
    "include",
    "breakpoint"
)
SYMBOLS = (
    ".",
    "+",
    "-",
    "*",
    "/",
    "<",
    ">",
    "{",
    "$",
    "}",
    ":",
    "[",
    "]",
    "(",
    ")",
)

SPACE_DELIMETERS = (" ", "\r", "\n", "\t")

OPERATORS = ("eq",)


class SingleChar(UserString):
    def is_space_delimeter(self):
        return self.data in SPACE_DELIMETERS

    def is_symbol(self):
        return self.data in SYMBOLS

    def is_comment_indicator(self):
        return self.data == "#"

    def is_string_indicator(self):
        return self.data == '"'

    def is_variable_indicator(self):
        return self.data == "$"

    def is_braced_variable_indicator(self):
        return self.data == "{"

    def append(self, c):
        self.data += c

    def __str__(self):
        return str(self.data)


class Token(dict):
    def __init__(self, data, _type):
        self._data = data
        self._type = _type
        self._line_number = None
        dict.__init__(self, data=str(data), type=str(_type))

    @property
    def str(self):
        return str(self._data)

    @property
    def type(self):
        return self._type

    @property
    def line_number(self):
        return self._line_number

    @line_number.setter
    def line_number(self, line_number):
        self._line_number = line_number


class Tokenizer(dict):
    def __init__(self, line, line_number):
        self.line = line.strip()
        self.chars = list(self.line)
        self.tokens = []
        self.cursor = 0
        self.length = len(self.chars)
        self.line_number = line_number
        dict.__init__(self, line_number=line_number, tokens=self.tokens)

    def _compose_symbol(self, char):
        token_type = (
            "delimiter"
            if self._is_control_statement_delimiter(char)
            else "symbol"
        )
        self.tokens.append(Token(char, token_type))
        self._advance()

    def _is_start_of_line(self):
        return self.cursor == 0

    def _is_end_of_line(self):
        return self.cursor == self.length - 1

    def _is_control_statement_delimiter(self, char):
        return (char == "<" and self._is_start_of_line()) or (
            char == ">" and self._is_end_of_line()
        )

    def _look_ahead(self):
        if self.cursor + 1 < self.length:
            return self.chars[self.cursor + 1]
        return None

    def _compose_number(self, char):
        token = char
        while True:
            next_char = self._look_ahead()
            if next_char is None or not next_char.isdigit():
                break
            token.append(next_char)
            self._advance()
        self.tokens.append(Token(token, "integerConstant"))
        self._advance()

    def _compose_number_or_identifier(self, char):
        token = char
        while True:
            next_char = self._look_ahead()
            if (
                next_char is None
                or next_char in SPACE_DELIMETERS
                or next_char in SYMBOLS
            ):
                break
            token.append(next_char)
            self._advance()
        all_digits = all(c.isdigit() for c in token)
        token_type = "integerConstant" if all_digits else "identifier"
        self.tokens.append(Token(token, token_type))
        self._advance()

    def _compose_variable(self, char):
        while True:
            next_char = self._look_ahead()
            if next_char is None or not (
                next_char.isalpha() or next_char.isdigit() or next_char == "_"
            ):
                break
            char.append(next_char)
            self._advance()
        self.tokens.append(Token(char, "variable"))
        self._advance()

    def _compose_braced_variable(self, _):
        next_char = self._look_ahead()
        if next_char is None or not next_char == "$":
            raise ParseException(
                f"Line {self.line_number} expected $, but get next_char.",
            )
        self._advance()
        char = self._get_char()
        next_char = self._look_ahead()
        while next_char != "}":
            char.append(next_char)
            self._advance()
            next_char = self._look_ahead()
        self._advance()
        self.tokens.append(Token(char, "variable"))
        self._advance()

    def _parse_comment(self):
        token_chars = SingleChar("")
        while not self._is_end():
            char = self._get_char()
            if char == " " and len(token_chars) == 0:
                self._advance()
                continue
            if char == ":" and len(token_chars) == 0:
                self._advance()
                continue
            token_chars.append(char)
            self._advance()
        self.tokens.append(Token(token_chars, "stringConstant"))

    def _compose_identifier_or_keyword(self, char):
        while True:
            next_char = self._look_ahead()
            if next_char is None or not (
                next_char.isalpha()
                or next_char.isdigit()
                or next_char in ["_", "-", ":"]
            ):
                break
            char.append(next_char)
            self._advance()
        token_type = "identifier"
        if char in ["comment", "Comment", "comment:", "Comment:"]:
            char = "comment"
        if char in KEYWORDS:
            token_type = "keyword"
        if char in OPERATORS:
            token_type = "operator"
        self.tokens.append(Token(char, token_type))
        self._advance()
        if char == "comment":
            self._parse_comment()
            self._advance()

    def _compose_string(self, char):
        token_chars = SingleChar("")
        self._advance()
        while not self._is_end():
            char = self._get_char()
            if char.is_string_indicator():
                if token_chars and token_chars[-1] != "\\":
                    break
            token_chars.append(char)
            self._advance()
        self.tokens.append(Token(token_chars, "stringConstant"))
        self._advance()

    def _compose_command(self):
        token = Token(self.line, "command")
        token.line_number = self.line_number
        self.tokens.append(token)

    def _advance(self):
        self.cursor += 1

    def _is_end(self):
        return self.cursor >= self.length

    def _get_char(self):
        return SingleChar(self.chars[self.cursor])

    def _is_pc_command(self):
        return self.line.startswith("/")

    def is_group_command(self):
        return self.line.startswith("*")

    def _is_command_line(self):
        if self._is_pc_command():
            return True
        if self.is_group_command():
            return True
        return not self.line.startswith(
            KEYWORDS[7:]
        ) and not self.line.startswith(SYMBOLS)

    def is_section_line(self):
        return self.line.startswith("[")

    def _is_commented_line(self):
        return self.line.startswith("#")

    def is_section_commented(self):
        return re.match(r"#\s*\[", self.line)

    def _is_empty_line(self):
        return not self.line

    def parse(self):
        # breakpoint()
        if self._is_empty_line():
            return self.tokens
        if self._is_commented_line():
            return self.tokens
        if self._is_command_line():
            self._compose_command()
            return self.tokens
        while not self._is_end():
            char = self._get_char()
            if char.is_space_delimeter():
                self._advance()
            elif char.is_comment_indicator():
                return self.tokens
            elif char.is_variable_indicator():
                self._compose_variable(char)
            elif char.is_braced_variable_indicator():
                self._compose_braced_variable(char)
            elif char.is_symbol():
                self._compose_symbol(char)
            elif char.isdigit():
                self._compose_number_or_identifier(char)
            elif char.isalpha():
                self._compose_identifier_or_keyword(char)
            elif char.is_string_indicator():
                self._compose_string(char)
            else:
                self._advance()
        for token in self.tokens:
            token.line_number = self.line_number
        return self.tokens
