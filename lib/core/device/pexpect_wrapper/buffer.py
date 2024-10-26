import re
from functools import lru_cache
from io import StringIO

from lib.services import logger


class CleanedBuffer(StringIO):

    COMPILED_CLEAN_PATTERN = {}

    def _clean(self, buffer_content):
        return (
            self._clean_by_pattern(buffer_content) if buffer_content else buffer_content
        )

    def getvalue(self):
        buffer_content = super().getvalue()
        return self._clean(buffer_content) if buffer_content else buffer_content

    def read(self):
        buffer_content = super().read()
        return self._clean(buffer_content) if buffer_content else buffer_content

    @lru_cache(maxsize=128, typed=True)
    def _clean_by_pattern(self, original_output):
        cleaned_output = original_output.encode("utf-8")
        for p_description, pattern in self.COMPILED_CLEAN_PATTERN.items():
            cleaned_output = re.sub(pattern, "", original_output)
            if original_output != cleaned_output:
                title = f"*** Clean Pattern '{p_description}' Matched ***"
                logger.notice(
                    "%s\nCleaned Content:\n'%s'\n%s",
                    title,
                    cleaned_output,
                    "*" * len(title),
                )
                original_output = cleaned_output
        return cleaned_output


def new_buffer_init_class(device_type, buffer_clean_pattern):
    if not buffer_clean_pattern:
        return StringIO
    cls = type(
        f"{device_type}CleanedBuffer",
        (CleanedBuffer,),
        {"COMPILED_CLEAN_PATTERN": buffer_clean_pattern},
    )  # pylint: disable=abstract-class-instantiated
    # I can't put COMPILED_CLEAN_PATTERN in __init__ because this class is used by pexpect.spawn
    # the class was an argument to pexpect.spawn and it will be called to initialize buffer without any args
    return cls
