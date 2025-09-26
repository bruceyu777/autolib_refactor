from functools import lru_cache

import regex

from lib.services import logger
from lib.settings import OUTPUT_SEARCH_WARN_THRESHOLD, OUTPUT_SEARCH_WINDOW_SIZE

from .common import clean_by_pattern

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
        # Replace greedy wildcards with line-safe equivalents
        r"\.\*": r"[^\n\r]*",
        r"\.\+": r"[^\n\r]+",
        # Normalize start-of-line anchors
        r"^\(\^": r"^(",
        r"^\^": r"(?:[\n\r]|^)",
        # Normalize end-of-line handling
        r"\$*\)\$*": r")",  # Remove surrounding $ around closing parens
        r"[\r\n\\r\\n$]*\$": r"[\r\n]*$",  # Normalize $ to allow EOL variations
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
    def __init__(self, clean_patterns=None):
        self.output = ""
        self.clean_patterns = clean_patterns or {}

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
        original_output = self.output + output
        self.output = clean_by_pattern(original_output, self.clean_patterns)

    def clear(self, pos=None):
        self.output = "" if pos is None else self.output[pos:]

    def _prepare_search_window(
        self,
        pos,
        warn_threshold=OUTPUT_SEARCH_WARN_THRESHOLD,
        window_size=OUTPUT_SEARCH_WINDOW_SIZE,
    ):
        """Prepare the search window and return (search_text, search_start).
        search_start is the index in the original buffer at which search_text begins.
        This instance method delegates to module-level helpers for testability.
        """
        total_len = len(self.output)
        search_start, warned = _compute_search_window(
            pos, total_len, warn_threshold, window_size
        )
        search_text = self.output[search_start:]
        if warned:
            _format_large_search_warning(total_len - pos)
        return search_text, search_start

    def search(self, pattern, pos=0):
        pattern = _convert_tcl_to_python_pattern(pattern)
        try:
            # Prepare a suitable search window and compute relative offset
            search_text, search_start = self._prepare_search_window(pos)
            result = regex.search(pattern, search_text, timeout=1)
            if result and search_start != pos:
                # Wrap to keep indices relative to the original pos
                return _RelativeOffsetMatch(result, search_start - pos)
            return result
        except TimeoutError as e:
            width = 70
            logger.warning(" Expect Timeout - Pattern is INVALID ".center(width, "*"))
            logger.warning("Expect pattern: %s", pattern)
            logger.warning("*" * width)
            raise ValueError(f"Invalid Expect Pattern '{pattern}'") from e

    def expect(self, pattern):
        m = self.search(pattern)
        if m is not None:
            self.clear(m.end())
        return m


class _RelativeOffsetMatch:
    """Wraps a regex match and adds a relative offset so that start/end
    remain relative to the original pos used by OutputBuffer.search().
    """

    def __init__(self, original_match, relative_offset):
        self._m = original_match
        self._off = relative_offset

    def group(self, *args):
        return self._m.group(*args)

    def start(self, group=0):
        return self._m.start(group) + self._off

    def end(self, group=0):
        return self._m.end(group) + self._off

    def span(self, group=0):
        return (self.start(group), self.end(group))

    def __bool__(self):
        return bool(self._m)

    def __repr__(self):
        return f"<RelativeOffsetMatch span={self.span()}>"

    # Provide attributes that may be accessed externally on Match
    @property
    def regs(self):
        # Not adjusting nested groups' spans; consumers in this codebase use start/end only
        return self._m.regs

    @property
    def re(self):
        return self._m.re

    @property
    def string(self):
        return self._m.string

    @property
    def pos(self):
        return self._m.pos

    @property
    def endpos(self):
        return self._m.endpos

    @property
    def lastindex(self):
        return self._m.lastindex

    @property
    def lastgroup(self):
        return self._m.lastgroup

    @property
    def fuzzy_counts(self):
        # regex module specific
        return getattr(self._m, "fuzzy_counts", None)

    @property
    def partial(self):
        return getattr(self._m, "partial", False)

    @property
    def captures(self):
        return getattr(self._m, "captures", None)

    @property
    def named_captures(self):
        return getattr(self._m, "named_captures", None)

    @property
    def fuzzy_changes(self):
        return getattr(self._m, "fuzzy_changes", None)

    @property
    def overlapped(self):
        return getattr(self._m, "overlapped", False)

    @property
    def capturesdict(self):
        return getattr(self._m, "capturesdict", None)

    @property
    def groupdict(self):
        return self._m.groupdict

    @property
    def groups(self):
        return self._m.groups

    @property
    def expand(self):
        return self._m.expand

    @property
    def __copy__(self):
        return getattr(self._m, "__copy__", None)

    @property
    def __deepcopy__(self):
        return getattr(self._m, "__deepcopy__", None)

    # End of compatibility proxying


def _compute_search_window(pos, total_len, warn_threshold=100000, window_size=50000):
    """Compute a search window given a pos within total_len. If the substring
    from pos is larger than warn_threshold, search only the last window_size
    characters of the entire buffer, but never before pos.
    Returns (search_start_index, warn: bool).
    """
    if total_len - pos <= warn_threshold:
        return pos, False
    search_start = max(pos, total_len - window_size)
    return search_start, True


def _truncate_for_search(text, warned):
    return text


def _format_large_search_warning(length):
    logger.warning(
        "Search text is very large (%d chars). This might indicate infinite output. "
        "Restricting search window to last 50000 characters.",
        length,
    )
