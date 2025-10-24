# File size and line constants
SMALL_FILE_LINE_LIMIT = 10000  # 10K lines - show entire file
DEFAULT_TAIL_LINES = 1000
DEFAULT_HEAD_LINES = 1000
MAX_VIEWABLE_SIZE = 10 * 1024 * 1024  # 10MB per chunk

# File reader block size
BLOCK_SIZE = 4096  # Block size for backward reading

# Viewable file patterns
VIEWABLE_TESTFILE_PREFIX = ("grp.",)

VIEWABLE_TESTFILE_EXTENSION = (
    ".log",
    ".txt",
    ".env",
    ".vm",
    "",
    ".conf",
    ".grp",
    ".html",
    ".py",
    ".md",
    ".json",
    ".yaml",
    ".sh",
)
