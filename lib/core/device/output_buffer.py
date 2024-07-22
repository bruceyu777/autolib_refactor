import regex
from lib.services.log import logger
import time

NOFLAG = 0


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
        self.output += self._remove_color_character(output)
        # self.output = self.output.replace("\r\n", "\n")

    def clear(self, pos=None):
        self.output = "" if pos is None else self.output[pos:]

    def search(self, pattern, pos=0):
        pattern = self._normalize_newline_sensitivity(pattern)
        logger.debug("-----------start match output----------")
        logger.debug("%s", self.output[pos:])
        logger.debug("------------end match output-----------")
        t1 = time.perf_counter()
        result =  regex.search(pattern, self.output[pos:])
        t2 = time.perf_counter()

        logger.debug("pattern match for %s takes %s s", pattern, t2-t1)

        return result

    def expect(self, pattern):
        m = self.search(pattern)
        if m is not None:
            self.clear(m.end())
        return m

    @staticmethod
    def _remove_color_character(output):
        return regex.sub(r"\x1B\[([0-9]{1,3}(;[0-9]{1,2})?)?[mGK]", "", output)

    @staticmethod
    def _normalize_newline_sensitivity(pattern):
        flag = regex.DOTALL | regex.MULTILINE
        m = regex.match(r"^\(\?n\)(.*)", pattern)
        logger.info("The original pattern is: %s", pattern)
        if m is not None:
            flag = regex.MULTILINE
            pattern = m.group(1)
        logger.info("The extracted pattern is: %s", pattern)
        return regex.compile(pattern, flag)
