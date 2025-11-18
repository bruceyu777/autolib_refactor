import threading
from copy import deepcopy

from lib.services import env, logger

from .lexer import Lexer
from .parser import Parser
from .syntax import script_syntax


class Compiler:
    # Class-level flag for pattern refresh (shared across all instances)
    _patterns_refreshed = False
    _refresh_lock = threading.Lock()

    def __init__(self):
        self.files = {}
        self.devices = set()
        self._lock = threading.RLock()  # Reentrant lock for recursive compilation

    @classmethod
    def _ensure_patterns_refreshed(cls):
        """
        Ensure patterns include custom APIs (one-time operation per process).

        This is called before first compilation to discover custom APIs from
        plugins/apis/ and regenerate lexer patterns to include them.
        """
        if not cls._patterns_refreshed:
            with cls._refresh_lock:
                # Double-check after acquiring lock (thread safety)
                if not cls._patterns_refreshed:
                    logger.debug(
                        "First compilation - refreshing patterns for custom APIs"
                    )
                    script_syntax.refresh_patterns()
                    cls._patterns_refreshed = True

    def _compile_file(self, file_name):
        # Ensure patterns refreshed on first compilation (discovers custom APIs)
        self._ensure_patterns_refreshed()

        # Check cache without lock first (performance optimization)
        if file_name in self.files:
            return

        # Acquire lock for compilation and cache update
        with self._lock:
            # Double-check after acquiring lock (another thread may have compiled it)
            if file_name in self.files:
                return

            in_debug_mode = getattr(logger, "in_debug_mode", False)
            lexer = Lexer(file_name, dump_token=in_debug_mode)
            tokens, lines = lexer.parse()
            parser = Parser(file_name, tokens, lines)
            vm_codes, devices, called_files = parser.run(dump_code_flag=in_debug_mode)

            self.files[file_name] = vm_codes
            self.devices |= devices

            # Recursive compilation happens within the lock
            for f, current_device in called_files:
                f = env.variable_interpolation(f, current_device=current_device)
                self._compile_file(f)

    def run(self, file_name):
        self._compile_file(file_name)
        logger.info("Compiled %s", file_name)

    def retrieve_vm_codes(self, file_name):
        # NOTE:
        # a single script can be used by multiple device sections
        # so we need to return a copy, or it will cause wrong result
        return deepcopy(self.files[file_name])

    def retrieve_devices(self):
        return self.devices


compiler = Compiler()
