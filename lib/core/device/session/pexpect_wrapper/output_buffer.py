from functools import lru_cache

import regex

from lib.services import logger

NOFLAG = 0


@lru_cache(maxsize=128, typed=True)
def _convert_tcl_to_python_pattern(pattern):
    logger.debug("The original pattern is: %s", pattern)
    flags, pattern = _split_flag_and_pattern(pattern)
    regex_flags = _to_regex_flags(flags)
    logger.debug("The converted pattern is: '%s', flags: '%s'", pattern, regex_flags)
    return regex.compile(pattern, flags=regex_flags)


def _to_regex_flags(flags):
    """Converts expect flags to regex flags."""
    flag_mapping = {
        "i": regex.IGNORECASE,
        "s": regex.DOTALL,
        "m": regex.MULTILINE,
        "a": regex.ASCII,
        "u": regex.UNICODE,
    }
    regex_flags = NOFLAG
    for f in flags:
        if f not in flag_mapping:
            continue
        regex_flags |= flag_mapping[f]
    return regex_flags


def _to_line_buffer_pattern(pattern):
    patterns_to_update = {
        r"\.\*": r"[^\n\r]*",
        r"^\(\^": r"^(",
        r"\$*\)\$*": r")",
        r"[\r\n\\r\\n$]*$": r"[^\r\n]",
        r"^\^": r"(?:[\n\r]|^)",
    }
    for original, target in patterns_to_update.items():
        pattern = regex.sub(original, target, pattern)
    return pattern


def _split_flag_and_pattern(pattern):
    """
    (?i) — Case Insensitive: Enables case-insensitive matching.
    (?m) — Multiline: Treats the string as multiple lines, allowing ^ to match
            the start of any line and $ to match the end of any line.
    (?s) — Dot Matches All (Singleline): Allows the . (dot) to match newline
            characters, treating the input as a single line.
    (?a) — ASCII-Only: Forces the pattern to only match ASCII characters (useful
            for portability when working with Unicode).
    (?u) — Unicode Matching: Enables Unicode matching (the default behavior since Python 3.x).
    (?t) — Template Mode: A special flag that forces the pattern to only match literals,
            without interpreting any special regex characters (used mostly in special cases).
    """
    match = regex.match(r"^\(\?(?P<flags>[imsautn]+)\)(?P<pattern>.*)", pattern)
    flags = ""
    if match:
        flags = match.group("flags")
        pattern = match.group("pattern")
    for flag in ("s", "m"):
        if flag not in flags:
            flags += flag
    if "n" in flags:
        # in tcl/tk, (?n) was used to disable newline matching
        flags = flags.replace("n", "")
        pattern = _to_line_buffer_pattern(pattern)
    return flags, pattern


class OutputBuffer:
    def __init__(self):
        self.output = ""

    def __str__(self):
        return self.output

    def __getitem__(self, index_or_slice):
        if isinstance(index_or_slice, slice):
            start, stop, step = index_or_slice.indices(len(self.output))
            return "".join([self.output[i] for i in range(start, stop, step)])

        return self.output[index_or_slice]

    def __len__(self):
        return len(self.output)

    def append(self, output):
        self.output += output

    def clear(self, pos=None):
        self.output = "" if pos is None else self.output[pos:]

    def search(self, pattern, pos=0):
        pattern = _convert_tcl_to_python_pattern(pattern)
        result = regex.search(pattern, self.output[pos:])
        return result

    def expect(self, pattern):
        m = self.search(pattern)
        if m is not None:
            self.clear(m.end())
        return m
