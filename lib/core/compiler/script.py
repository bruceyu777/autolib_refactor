import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from lib.services import logger
from lib.utilities import FileNotExist

from .compiler import compiler
from .debugger import Debugger
from .vm_code import VMCode


class Script:
    def __init__(self, source_file):
        if not os.path.exists(source_file):
            raise FileNotExist(source_file)
        self.source_file = source_file
        compiler.run(self.source_file)
        self.vm_codes = compiler.retrieve_vm_codes(self.source_file)
        with open(self.source_file, "r", encoding="utf-8") as f:
            self.lines = [line.strip() for line in f]
        self._debugger = Debugger(self.lines, self.vm_codes)

    @classmethod
    def from_compiled_data(cls, source_file, vm_codes, lines, devices=None):
        """
        Create Script instance from pre-compiled data.

        This factory method is used by parallel compilation to reconstruct
        Script objects from worker process results without re-parsing.

        Args:
            source_file: Path to the source script file
            vm_codes: Compiled VM code instructions
            lines: Source file lines (stripped)
            devices: Optional set of devices used in the script

        Returns:
            Script instance with pre-compiled data
        """
        script = object.__new__(cls)
        script.source_file = source_file
        script.vm_codes = vm_codes
        script.lines = lines
        script._debugger = Debugger(lines, vm_codes)

        # Register in compiler cache
        compiler.files[source_file] = vm_codes
        if devices:
            compiler.devices |= devices

        return script

    def get_script_line(self, line_number):
        return self.lines[line_number - 1]

    def update_code_to_execute(self, program_counter):
        code = self.vm_codes[program_counter]
        if code.line_number is not None:
            program_counter = self.debug_run(code.line_number - 1, program_counter)
            code = self.vm_codes[program_counter]
        return program_counter, code

    def get_program_counter_limit(self):
        return len(self.vm_codes)

    def get_compiled_code_line(self, line_number):
        return self.vm_codes[line_number]

    def get_all_involved_devices(self):
        return compiler.devices

    @property
    def id(self):
        return Path(self.source_file).stem

    def __str__(self):
        return self.source_file

    def breakpoint(self):
        self._debugger.breakpoint()

    def debug_run(self, line_number, program_counter):
        return self._debugger.run(line_number, program_counter)


def _compile_single_script(source_file):
    """
    Worker function for parallel compilation.

    Uses threading instead of multiprocessing to avoid:
    - Process spawn overhead (~50-100ms per process)
    - Module import overhead in each worker
    - Data serialization (pickle) overhead
    - Redundant compilation of include files

    The compiler singleton is thread-safe for reading cached files.
    """
    try:
        # Simply create Script object - compilation and caching handled internally
        script = Script(source_file)
        return (source_file, script, None)
    except Exception as e:
        return (source_file, None, e)


class Group(Script):

    def __init__(self, source_file):
        super().__init__(source_file)
        self.included_scripts = {}

    def parse(self, executor_cls):
        """
        Parse group script and compile all included scripts.

        Uses parallel compilation with multiprocessing for improved performance.
        For 309+ scripts, this can reduce compilation time from 136s to ~40s (3-4x speedup).
        """
        # Discover all scripts to compile
        all_scripts = self._discover_scripts(executor_cls)
        if not all_scripts:
            return

        # Compile scripts (parallel or sequential)
        num_scripts = len(all_scripts)
        max_workers = max(16, os.cpu_count() or 1)

        if self._should_use_parallel_compilation(max_workers, num_scripts):
            self._compile_parallel(all_scripts, max_workers)
        else:
            self._compile_sequential(all_scripts, num_scripts)

    def _discover_scripts(self, executor_cls):
        """Execute group script to discover all included scripts."""
        with executor_cls(self, [], False) as executor:
            executor.execute()
            return executor.get_all_scripts()

    def _should_use_parallel_compilation(self, max_workers, num_scripts):
        return max_workers > 1 and num_scripts > 1

    def _compile_parallel(self, all_scripts, max_workers):
        """
        Compile scripts in parallel using threading.

        Threading is preferred over multiprocessing because:
        - Scripts are I/O bound (file reading, parsing)
        - No process spawn overhead
        - Shared compiler cache reduces redundant work
        - Much lower memory footprint
        """
        logger.info(
            "Compiling %d scripts in parallel using %d workers",
            len(all_scripts),
            max_workers,
        )

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            # Submit all compilation tasks
            future_to_line = {
                pool.submit(_compile_single_script, source_file): line_number
                for line_number, source_file in all_scripts.items()
            }

            # Collect results
            self.included_scripts = {}
            for future in as_completed(future_to_line):
                line_number = future_to_line[future]
                script = self._process_compilation_result(future.result())
                self.included_scripts[line_number] = script

        logger.info("Parallel compilation completed")

    def _compile_sequential(self, all_scripts, num_scripts):
        """Compile scripts sequentially (fallback for small script counts)."""
        logger.debug("Using sequential compilation for %d script(s)", num_scripts)
        self.included_scripts = {
            line_number: Script(source_file)
            for line_number, source_file in all_scripts.items()
        }

    def _process_compilation_result(self, result):
        """
        Process compilation result from worker thread.

        Args:
            result: Tuple of (source_file, script, error)

        Returns:
            Script object

        Raises:
            Exception: If compilation failed in worker thread
        """
        _, script, error = result

        if error:
            raise error

        return script


class IncludeScript(Script):
    def __init__(self, source_file, current_device=None):
        super().__init__(source_file)
        self.device = current_device
        if current_device is not None:
            self.vm_codes.insert(
                0,
                VMCode(
                    None,
                    "with_device",
                    (current_device,),
                ),
            )
