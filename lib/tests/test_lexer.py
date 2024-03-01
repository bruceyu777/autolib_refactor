from lib.core.compiler.lexer import (
    APIS_WITH_PARAS,
    APIS_WITHOUT_PARAS,
    KEYWORDS,
    FileParser,
    Token,
)

COMMENTED_LINE = {
    ("#This is a test", ()),
    ("##This is a test", ()),
}

BASIC_TESTCASES_DATA = (
    ("comment: this is a test", (("comment", "this is a test", 1),)),
    ("Comment: this is a test", (("comment", "this is a test", 1),)),
    ("comment this is a test", (("comment", "this is a test", 1),)),
    ("Comment this is a test", (("comment", "this is a test", 1),)),
    ("comments: this is a test", (("comment", "this is a test", 1),)),
    ("Comments: this is a test", (("comment", "this is a test", 1),)),
    ("comments this is a test", (("comment", "this is a test", 1),)),
    ("Comments this is a test", (("comment", "this is a test", 1),)),
    ("config system admin", (("command", "config system admin", 1),)),
    (
        "include /home/zhaodonglin/test.text",
        (("include", "/home/zhaodonglin/test.text", 1),),
    ),
)

KEYWORDS_TESTCASES_DATA = (
    (f"<{keyword}>", (("keyword", keyword, 1),)) for keyword in KEYWORDS
)
APIS_WITH_PARAS_TESTCASES_DATA = (
    (f"{api} 1", (("api", api, 1), ("number", "1", 1)))
    for api in APIS_WITH_PARAS
)
APIS_WITHOUT_PARAS_TESTCASES_DATA = (
    (f"{api}", (("api", api, 1),)) for api in APIS_WITHOUT_PARAS
)


class TestFileParser:
    def expect_line(self, file_parser, line, expected):
        tokens = file_parser.parse_line(line)

        if expected:
            assert tokens == [Token(*e) for e in expected]
        else:
            assert tokens == []

    def assert_with_data(self, data):
        for line, expected in data:
            file_parser = FileParser()
            self.expect_line(file_parser, line, expected)

    def test_commented_line(self):
        self.assert_with_data(COMMENTED_LINE)

    def test_basic(self):
        self.assert_with_data(BASIC_TESTCASES_DATA)

    def test_keyword(self):
        self.assert_with_data(KEYWORDS_TESTCASES_DATA)

    def test_api(self):
        self.assert_with_data(APIS_WITHOUT_PARAS_TESTCASES_DATA)
        self.assert_with_data(APIS_WITH_PARAS_TESTCASES_DATA)

    def test_commented_section(self):
        file_parser = FileParser()
        data = (
            ("#[FGT_A]", ()),
            ("config system admin", ()),
            ("[FGT_A]", (("section", "FGT_A", 1),)),
            (
                "config system admin",
                (
                    ("section", "FGT_A", 1),
                    ("command", "config system admin", 1),
                ),
            ),
        )
        for line, expected in data:
            self.expect_line(file_parser, line, expected)

    def test_tokenizer(self):
        data = (
            (
                "<if $x + {$y} eq 3>",
                (
                    ("keyword", "if", 1),
                    ("variable", "x", 1),
                    ("symbol", "+", 1),
                    ("variable", "y", 1),
                    ("operator", "eq", 1),
                    ("number", 3, 1),
                ),
            ),
            (
                '<if name_ eq "Rlease QA(FOS)">',
                (
                    ("keyword", "if", 1),
                    ("identifier", "name_", 1),
                    ("operator", "eq", 1),
                    ("string", '"Rlease QA(FOS)"', 1),
                ),
            ),
            (
                "<if model ne FortiGate-401F>",
                (
                    ("keyword", "if", 1),
                    ("identifier", "model", 1),
                    ("operator", "ne", 1),
                    ("identifier", "FortiGate-401F", 1),
                ),
            ),
            (
                "<strset ADDR 10.10.10.10>",
                (
                    ("keyword", "strset", 1),
                    ("identifier", "ADDR", 1),
                    ("identifier", "10.10.10.10", 1),
                ),
            ),
            (
                r'<strset ADDR "dstname=\"www.apple.com\"">',
                (
                    ("keyword", "strset", 1),
                    ("identifier", "ADDR", 1),
                    ("string", r'"dstname=\"www.apple.com\""', 1),
                ),
            ),
        )
        self.assert_with_data(data)

    def test_tokenize(self):
        file_parser = FileParser()
        file_parser.tokenize("model next FortiGate-401F")
