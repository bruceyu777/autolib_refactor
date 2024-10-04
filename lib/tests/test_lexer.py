from lib.core.compiler.lexer import APIS_WITH_PARAS, APIS_WITHOUT_PARAS, KEYWORDS

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
    (f"{api} 1", (("api", api, 1), ("number", "1", 1))) for api in APIS_WITH_PARAS
)
APIS_WITHOUT_PARAS_TESTCASES_DATA = (
    (f"{api}", (("api", api, 1),)) for api in APIS_WITHOUT_PARAS
)


class TestParser:
    """prevous testcases are out of date, need to redo the tests"""
