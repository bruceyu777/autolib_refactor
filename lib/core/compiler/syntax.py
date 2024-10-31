import json
import re
from collections import OrderedDict
from pathlib import Path


class ScriptSyntax:

    TOKEN_PATTERN_TABLE = {
        "variable": r"\{?\$(?P<variable_name>[^\s]+?)\s*\}?",
        "symbol": r"==|[-()[\]{}<>+*\/=]",
        "number": r"(?P<number_content>\d+)",
        "operator": r"eq|ne|lt",
        "expect_double": r'\-e\s+"(?P<double_quote_str>[^\"]*)"(?=\s+\-)',
        "expect_single": r"\-e\s+'(?P<single_quote_str>[^\']*)'(?=\s+\-)",
        "expect_string": r"\-e\s+(?P<expect_str>\S*)(?=\s+\-)",
        "string": r'"(?:\"|[^"\\]|\\.)*?"',
        "identifier": r"\{.+\}|.+?",
    }

    LINE_PATTERN_TABLE = {
        "commented_section": r"#\s*\[.*\]",
        "commented_line": r"#.*",
        "section": r"\[(?P<section_name>.+)\]",
        "statement": "",
        "comment": r"[Cc]omment[s]*\s*:*\s*(?P<comment_content>.*)",
        "include": r"include\s+(?P<file_name>.+)",
        "api": "",
        "command": r".+",
    }

    OPERATOR_TOKEN_TYPE = ["operator", "symbol"]

    def __init__(self, syntax_filepath):
        with open(syntax_filepath, "r", encoding="utf-8") as f:
            self.syntax = json.load(f, object_pairs_hook=OrderedDict)
        self.line_pattern = self.generate_line_pattern()
        self.token_pattern = self.generate_token_pattern()

    def get_deprecated_cmd_replace_patterns(self):
        return self.syntax.get("deprecated_commands_replacement", {})

    def is_valid_command(self, command):
        return command.startswith(tuple(self.syntax["valid_commands"]))

    def is_valid_script_type(self, script_type):
        return script_type in self.syntax["script"]

    def is_valid_line_type(self, line_type):
        return line_type in self.LINE_PATTERN_TABLE

    def is_valid_token_type(self, token_type):
        return token_type in self.TOKEN_PATTERN_TABLE

    def at_top_level_category(self, category):
        return category in self.syntax

    def get_token_syntax_definition(self, token, fallback=None):
        try:
            return self.syntax[token.type][token.str]
        except KeyError:
            return fallback

    def get_keyword_cli_syntax(self, keyword):
        return self.syntax["keyword"][keyword][-1]

    def _generate_keyword_pattern(self):
        keywords = self.syntax["keyword"].keys()
        sorted_keywords = sorted(keywords, key=len, reverse=True)
        return "|".join(rf"{keyword}" for keyword in sorted_keywords)

    def _generate_statement_pattern(self):
        keyword_pattern = self._generate_keyword_pattern()
        return rf"\<\s*(?P<statement_content>({keyword_pattern}).*)\>"

    def _generate_api_pattern(self):
        api_pattern_list = []
        for api, syntax_list in self.syntax["api"].items():
            _, args_definition, *_ = syntax_list
            if args_definition:
                api_pattern_list.append(rf"{api}\s+.+")
            else:
                api_pattern_list.append(rf"{api}")
        api_pattern_list = sorted(api_pattern_list, key=len, reverse=True)
        return r"|".join(api_pattern_list)

    def generate_line_pattern(self):
        ScriptSyntax.LINE_PATTERN_TABLE["statement"] = (
            self._generate_statement_pattern()
        )
        ScriptSyntax.LINE_PATTERN_TABLE["api"] = self._generate_api_pattern()
        line_pattern = re.compile(
            r"|".join(
                rf"(?P<{type}>{pattern})"
                for type, pattern in ScriptSyntax.LINE_PATTERN_TABLE.items()
            )
        )
        return line_pattern

    def generate_token_pattern(self):
        token_pattern_table = ScriptSyntax.TOKEN_PATTERN_TABLE
        token_pattern = re.compile(
            r"|".join(
                rf"(?P<{type}>{pattern})(\s+|$)"
                for type, pattern in token_pattern_table.items()
            )
        )
        return token_pattern


SYNTAX_DEFINITION_FILEPAHT = (
    Path(__file__).resolve().parent / "static" / "cli_syntax.json"
)
script_syntax = ScriptSyntax(SYNTAX_DEFINITION_FILEPAHT)
