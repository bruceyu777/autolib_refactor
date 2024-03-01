#!/usr/bin/python
import json
import os
from pathlib import Path

from lib.services import output

from .tokenizer import Tokenizer


class Parser:
    TOKENS_FILE = "tokens.json"

    def __init__(self, path):
        self.path = Path(path)
        self.files = {}
        self.tokens = {}

    def _add_file(self, file_path):
        with open(file_path, "r") as f:
            lines = f.readlines()
            stem = file_path.stem
            self.files[stem] = lines

    def _load_files(self):
        if self.path.is_file():
            self._add_file(self.path)
        elif self.path.is_dir():
            files = os.listdir(self.path)
            for file in files:
                f = Path(file)
                if f.suffix == ".txt":
                    self._add_file(f)

    def _compose_token_file_name(self, file_name):
        return output.compose_compiled_file(file_name, self.TOKENS_FILE)

    def _dump_to_file(self, file_name, tokens):
        token_file = self._compose_token_file_name(file_name)
        with open(token_file, "w") as f:
            json.dump({"tokens": tokens}, f, indent=4)

    def parse(self):
        self._load_files()

        for file_name, lines in self.files.items():
            file_tokens = []
            section_commented = False
            for index, line in enumerate(lines):
                tokenizer = Tokenizer(line, index + 1)
                if tokenizer.is_section_line():
                    section_commented = False
                if tokenizer.is_section_commented():
                    # breakpoint()
                    section_commented = True
                if not section_commented:
                    tokenizer.parse()
                    file_tokens.append(tokenizer)
            self.tokens[file_name] = [
                token for t in file_tokens for token in t.tokens
            ]
            self._dump_to_file(file_name, file_tokens)
        return self.tokens

    def parse_file(self, file_name):
        with open(file_name, "r") as f:
            lines = f.readlines()
            file_tokens = []
            for index, line in enumerate(lines):
                tokenizer = Tokenizer(line, index + 1)
                tokenizer.parse()
                file_tokens.append(tokenizer)
            self.tokens[file_name] = [
                token for t in file_tokens for token in t.tokens
            ]
            self._dump_to_file(file_name, file_tokens)
        return self.tokens


if __name__ == "__main__":
    Parser("./testcases/704319.txt").parse()
