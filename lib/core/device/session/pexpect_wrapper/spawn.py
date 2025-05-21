import re
from functools import lru_cache

import pexpect
from pexpect._async import expect_async
from pexpect.spawnbase import EOF, TIMEOUT, Expecter, searcher_re, searcher_string

from lib.services import logger


class ExpecterCleaned(Expecter):

    def __init__(self, spawn, searcher, searchwindowsize=-1, clean_patterns=None):
        super().__init__(spawn, searcher, searchwindowsize)
        self.clean_patterns = clean_patterns or {}

    def do_search(self, window, freshlen):
        if window:
            window = self._clean_by_pattern(window)
        return super().do_search(window, freshlen)

    @lru_cache(maxsize=128, typed=True)
    def _clean_by_pattern(self, original_output):
        cleaned_output = original_output.encode("utf-8")
        for p_description, pattern in self.clean_patterns.items():
            cleaned_output = re.sub(pattern, "", original_output)
            if original_output != cleaned_output:
                title = f"*** Clean Pattern '{p_description}' Matched ***"
                delimiter = "*" * len(title)
                logger.debug(
                    "\n%s\n%s\nCleaned Content:\n'%s'\n%s",
                    delimiter,
                    title,
                    cleaned_output,
                    delimiter,
                )
                original_output = cleaned_output
        return cleaned_output


def init_expecter(spawn, *args, **kwargs):
    clean_patterns = getattr(spawn, "clean_patterns")
    logger.debug("*** clean_patterns ***:\n'%s'", clean_patterns)
    if clean_patterns:
        return ExpecterCleaned(spawn, *args, **kwargs, clean_patterns=clean_patterns)
    return Expecter(spawn, *args, **kwargs)


class Spawn(pexpect.spawn):

    def __init__(
        self,
        command,
        clean_patterns,
        job_log_handler,
        encoding="utf-8",
        codec_errors="ignore",
        **kwargs,
    ):
        self.job_log_handler = job_log_handler
        super().__init__(
            command, encoding=encoding, codec_errors=codec_errors, **kwargs
        )
        self.clean_patterns = clean_patterns

    def _log(self, s, direction):
        super()._log(s, direction)
        if self.job_log_handler is not None:
            self.job_log_handler.stream.write(s)
            self.job_log_handler.flush()

    ###########################################################################
    # Below codes was copied from pexpect.spwan
    # In order to override Expecter for cleaning buffer completely
    # pylint: disable=arguments-differ,no-else-return, inconsistent-return-statements
    ###########################################################################
    def expect_list(
        self, pattern_list, timeout=-1, searchwindowsize=-1, async_=False, **kw
    ):
        """This takes a list of compiled regular expressions and returns the
        index into the pattern_list that matched the child output. The list may
        also contain EOF or TIMEOUT(which are not compiled regular
        expressions). This method is similar to the expect() method except that
        expect_list() does not recompile the pattern list on every call. This
        may help if you are trying to optimize for speed, otherwise just use
        the expect() method.  This is called by expect().


        Like :meth:`expect`, passing ``async_=True`` will make this return an
        asyncio coroutine.
        """
        if timeout == -1:
            timeout = self.timeout
        if "async" in kw:
            async_ = kw.pop("async")
        if kw:
            raise TypeError("Unknown keyword arguments: {}".format(kw))

        exp = init_expecter(
            self, searcher_re(pattern_list), searchwindowsize=searchwindowsize
        )
        if async_:
            return expect_async(exp, timeout)
        else:
            return exp.expect_loop(timeout)

    def expect_exact(
        self, pattern_list, timeout=-1, searchwindowsize=-1, async_=False, **kw
    ):
        """This is similar to expect(), but uses plain string matching instead
        of compiled regular expressions in 'pattern_list'. The 'pattern_list'
        may be a string; a list or other sequence of strings; or TIMEOUT and
        EOF.

        This call might be faster than expect() for two reasons: string
        searching is faster than RE matching and it is possible to limit the
        search to just the end of the input buffer.

        This method is also useful when you don't want to have to worry about
        escaping regular expression characters that you want to match.

        Like :meth:`expect`, passing ``async_=True`` will make this return an
        asyncio coroutine.
        """
        if timeout == -1:
            timeout = self.timeout
        if "async" in kw:
            async_ = kw.pop("async")
        if kw:
            raise TypeError("Unknown keyword arguments: {}".format(kw))

        if isinstance(pattern_list, self.allowed_string_types) or pattern_list in (
            TIMEOUT,
            EOF,
        ):
            pattern_list = [pattern_list]

        def prepare_pattern(pattern):
            if pattern in (TIMEOUT, EOF):
                return pattern
            if isinstance(pattern, self.allowed_string_types):
                return self._coerce_expect_string(pattern)
            self._pattern_type_err(pattern)

        try:
            pattern_list = iter(pattern_list)
        except TypeError:
            self._pattern_type_err(pattern_list)
        pattern_list = [prepare_pattern(p) for p in pattern_list]

        exp = init_expecter(
            self, searcher_string(pattern_list), searchwindowsize=searchwindowsize
        )
        if async_:
            return expect_async(exp, timeout)
        else:
            return exp.expect_loop(timeout)

    def expect_loop(self, searcher, timeout=-1, searchwindowsize=-1):
        """This is the common loop used inside expect. The 'searcher' should be
        an instance of searcher_re or searcher_string, which describes how and
        what to search for in the input.

        See expect() for other arguments, return value and exceptions."""

        exp = init_expecter(self, searcher, searchwindowsize=searchwindowsize)
        return exp.expect_loop(timeout)

    ###########################################################################
    # Above codes was copied from pexpect.spwan
    # In order to override Expecter for cleaning buffer completely
    ###########################################################################
