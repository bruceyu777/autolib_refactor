import json
import os
import re
from pathlib import Path
import chardet

from lib.services import output

APIS_WITH_PARAS = (
    "setvar",
    "varexpect",
    "keep_running",
    "report",
    "expect",
    "expect_ctrl_c",
    "sleep",
    "setlicense",
    "myftp",
    "mytelnet",
    "setenv",
    "compare",
    "expect_OR",
    "collect_dev_info"

)
APIS_WITHOUT_PARAS = ("forcelogin", "clearbuff", "clear_buffer", "clean_buffer", "breakpoint", "resetFirewall")
APIS_WITH_PARAS_PATTERN = "|".join(rf"{api}\s+.+" for api in APIS_WITH_PARAS)
APIS_WITHOUT_PARAS_PATTERN = "|".join(rf"{api}" for api in APIS_WITHOUT_PARAS)
APIS_PATTERN = rf"{APIS_WITH_PARAS_PATTERN}|{APIS_WITHOUT_PARAS_PATTERN}"

KEYWORDS = (
    "if",
    "elseif",
    "fi",
    "else",
    "strset",
    "listset",
    "intset",
    "loop",
    "intchange",
    "until",
    "while",
    "endwhile",
)

KEYWORDS_PATTERN = "|".join(rf"{keyword}" for keyword in KEYWORDS)

LINE_PATTERN_TABLE = {
    "commented_section": r"#\s*\[.*\]",
    "commented_line": r"#.*",
    "section": r"\[(?P<section_name>.+)\]",
    "statement": rf"\<\s*(?P<statement_content>({KEYWORDS_PATTERN}).*)\>",
    "comment": r"[Cc]omment[s]*\s*:*\s*(?P<comment_content>.*)",
    "include": r"include\s+(?P<file_name>.+)",
    "api": rf"{APIS_PATTERN}",
    "command": r".+",
}

LINE_PATTERN = re.compile(
    r"|".join(
        rf"(?P<{type}>{pattern})"
        for type, pattern in LINE_PATTERN_TABLE.items()
    )
)

TOKEN_PATTERN_TABLE = {
    "variable": r"\{?\$(?P<variable_name>[^\s]+?)\s*\}?",
    "symbol": r"==|[-()[\]{}<>+*/=]",
    "number": r"(?P<number_content>\d+)",
    "operator": r"eq|ne|lt",
    "string": r'"(?:\"|[^"\\]|\\.)*?"',
    "identifier": r"\{.+\}|.+?",
}

TOEKN_PATTERN = re.compile(
    r"|".join(
        rf"(?P<{type}>{pattern})(\s+|$)"
        for type, pattern in TOKEN_PATTERN_TABLE.items()
    )
)


class Token(dict):
    def __init__(self, _type, data, line_number):
        self._data = data
        self._type = _type
        self._line_number = line_number
        dict.__init__(
            self, data=str(data), type=str(_type), line_number=line_number
        )

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
        # if "#" in line and '"' not in line:
        #     line = re.sub(r"#.*", "", line)
        #     if not line:
        #         return []

        self.cur_line = rf"{line}"
        # print("cur line is", self.cur_line)
        # line_without_comments = re.sub(r'#.*', '', line)
        m = re.match(LINE_PATTERN, self.cur_line)
        if m is None:
            print(f"{self.line_number}: {self.cur_line}")
        self.cur_groupdict = m.groupdict()
        if self.section_commented:
            if self.cur_groupdict.get("section") is None:
                return []
        for line_type, matched_content in self.cur_groupdict.items():
            if matched_content is not None and line_type in LINE_PATTERN_TABLE:
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

    def tokenize(self, string):
        pos = 0
        while pos < len(string):
            m = TOEKN_PATTERN.match(string, pos)
            if m is None:
                print(f"{self.line_number}: {string[pos:]}")
            matched_group = m.groupdict()
            variable_name = (
                matched_group["variable_name"]
                if matched_group is not None
                else None
            )
            number = (
                matched_group["number_content"]
                if matched_group is not None
                else None
            )
            if m is None:
                print(f"{self.line_number}: {string[pos:]}")
            for token_type, matched_content in m.groupdict().items():
                if (
                    matched_content is not None
                    and token_type in TOKEN_PATTERN_TABLE
                ):
                    if token_type == "variable":
                        self.add_token(token_type, variable_name)
                    elif token_type == "number":
                        self.add_token(token_type, number)
                    else:
                        self.add_token(token_type, matched_content)
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
        # self.parse_api_or_statement("keyword", content)

        m = re.match(
            r"(?P<first>.+?)\s+(?P<leftover>.+)|(?P<second>.+)$",
            content,
        )
        # print("content is", content)
        # print("leftover is", m.group("leftover"))
        if m.group("leftover") is not None:
            # keyword = m.group("first")
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
        if len(content) == 0:
            path_parts = self.file_name.split(os.path.sep)
            remaining_path_parts = "/".join(path_parts[2:])
            svn_path = r"https://qa-svn.corp.fortinet.com/svn/qa/FOS/testcase"
            # print(f"{svn_path}/{remaining_path_parts}")
            return ""
        encoding_info = chardet.detect(content)
        detected_encoding = encoding_info["encoding"]
        # print("encoding is", detected_encoding)

        if detected_encoding == "utf-8":
            content_decoded = content.decode("utf-8", errors="ignore")
        elif detected_encoding:
            content_decoded = content.decode(detected_encoding, errors="ignore")
        else:
            print("Unable to detect the encoding.")
        # print(content_decoded)
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
