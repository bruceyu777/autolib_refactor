import os
import subprocess
import time

from ..log import logger
from .constants import (
    BLOCK_SIZE,
    DEFAULT_HEAD_LINES,
    DEFAULT_TAIL_LINES,
    MAX_VIEWABLE_SIZE,
)


class FileReader:

    BLOCK_SIZE = BLOCK_SIZE

    @staticmethod
    def _read_backwards_until_lines(f, file_size, num_lines, encoding):
        """Read file backwards until we have enough lines

        Args:
            f: Open file handle (in binary mode)
            file_size: Total size of file in bytes
            num_lines: Number of lines needed
            encoding: Text encoding to use

        Returns:
            tuple: (lines_list, bytes_read)
        """
        start_time = time.time()

        blocks = []
        bytes_read = 0
        lines = []

        while bytes_read < file_size:
            # Calculate chunk size for this iteration
            chunk_size = min(FileReader.BLOCK_SIZE, file_size - bytes_read)

            # Read block from file
            f.seek(file_size - bytes_read - chunk_size)
            block = f.read(chunk_size)
            blocks.insert(0, block)
            bytes_read += chunk_size

            # Decode and split into lines
            try:
                text = b"".join(blocks).decode(encoding)
                lines = text.split("\n")

                # Remove trailing empty string if text ends with newline
                if lines and lines[-1] == "":
                    lines.pop()

                # Early termination: stop when we have enough lines
                if len(lines) > num_lines:
                    break

            except UnicodeDecodeError:
                # Continue reading if multi-byte char split across blocks
                if bytes_read >= file_size:
                    raise  # Can't decode entire file

        elapsed = time.time() - start_time
        logger.debug(
            "Read backwards: %d bytes, %d lines, encoding=%s, time=%.3fs",
            bytes_read,
            len(lines),
            encoding,
            elapsed,
        )

        return lines, bytes_read

    @staticmethod
    def _calculate_total_lines(
        filepath, lines, bytes_read, file_size, num_result_lines
    ):
        """Calculate total lines in file

        Args:
            filepath: Path to the file
            lines: Lines we've already read
            bytes_read: How many bytes we read
            file_size: Total file size
            num_result_lines: Number of lines we're returning

        Returns:
            int: Total line count
        """
        if bytes_read >= file_size:
            # We read the entire file, we have the exact count
            return len(lines)

        # Only read part of file, need full count
        total_lines = FileReader.count_lines(filepath)
        return total_lines if total_lines is not None else num_result_lines

    @staticmethod
    def read_file_tail(filepath, num_lines=DEFAULT_TAIL_LINES, encoding="utf-8"):
        """Read last N lines from a file efficiently

        Returns:
            tuple: (content, start_line_number)
        """
        start_time = time.time()

        try:
            with open(filepath, "rb") as f:
                # Get file size
                f.seek(0, os.SEEK_END)
                file_size = f.tell()

                if file_size == 0:
                    logger.debug("read_file_tail: %s is empty", filepath)
                    return "", 0

                # Read backwards until we have enough lines
                lines, bytes_read = FileReader._read_backwards_until_lines(
                    f, file_size, num_lines, encoding
                )

                # Extract the last N lines
                result_lines = lines[-num_lines:] if len(lines) > num_lines else lines
                content = "\n".join(result_lines)

                # Calculate total lines and starting line number
                total_lines = FileReader._calculate_total_lines(
                    filepath, lines, bytes_read, file_size, len(result_lines)
                )
                start_line = max(1, total_lines - len(result_lines) + 1)

                elapsed = time.time() - start_time
                logger.debug(
                    "read_file_tail: %s - %d lines (start=%d, total=%s), time=%.3fs",
                    filepath,
                    len(result_lines),
                    start_line,
                    total_lines,
                    elapsed,
                )

                return content, start_line

        except Exception as e:
            logger.error("Error reading tail of file %s: %s", filepath, e)
            raise

    @staticmethod
    def read_file_head(filepath, num_lines=DEFAULT_HEAD_LINES, encoding="utf-8"):
        """Read first N lines from a file

        Returns:
            tuple: (content, start_line_number, total_lines)
        """
        start_time = time.time()

        try:
            lines = []
            with open(filepath, "r", encoding=encoding) as f:
                for i, line in enumerate(f):
                    if i >= num_lines:
                        break
                    lines.append(line.rstrip("\n"))
            content = "\n".join(lines)

            elapsed = time.time() - start_time
            logger.debug(
                "read_file_head: %s - %d lines, time=%.3fs",
                filepath,
                len(lines),
                elapsed,
            )

            # Head always starts at line 1
            return content, 1
        except Exception as e:
            logger.error("Error reading head of file %s: %s", filepath, e)
            raise

    @staticmethod
    def read_file_range(filepath, start_line, end_line, encoding="utf-8"):
        """Read a specific range of lines from a file

        Returns:
            tuple: (content, start_line_number)
        """
        start_time = time.time()

        try:
            lines = []
            with open(filepath, "r", encoding=encoding) as f:
                for i, line in enumerate(f, start=1):
                    if i < start_line:
                        continue
                    if i > end_line:
                        break
                    lines.append(line.rstrip("\n"))
            content = "\n".join(lines)

            elapsed = time.time() - start_time
            logger.debug(
                "read_file_range: %s - lines %d-%d (%d lines), time=%.3fs",
                filepath,
                start_line,
                end_line,
                len(lines),
                elapsed,
            )

            # Range uses the provided start_line
            return content, start_line
        except Exception as e:
            logger.error("Error reading range of file %s: %s", filepath, e)
            raise

    @staticmethod
    def search_in_file(filepath, pattern, context_lines=5):
        start_time = time.time()

        try:
            cmd = [
                "grep",
                "-n",  # Line numbers
                f"-C{context_lines}",  # Context lines
                "-E",  # Extended regex
                "--",
                pattern,
                filepath,
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False, timeout=30
            )

            elapsed = time.time() - start_time
            logger.debug(
                "search_in_file: %s - pattern='%s', returncode=%d, time=%.3fs",
                filepath,
                pattern,
                result.returncode,
                elapsed,
            )

            if result.returncode == 0:
                return result.stdout
            if result.returncode == 1:
                return None
            raise RuntimeError(f"grep failed: {result.stderr}")
        except subprocess.TimeoutExpired as e:
            raise TimeoutError("Search timeout (30s exceeded)") from e
        except Exception as e:
            logger.error("Error searching file %s: %s", filepath, e)
            raise e

    @staticmethod
    def try_multiple_encodings(filepath, read_func, *args):
        """Try reading file with multiple encodings

        Returns:
            tuple: (content, start_line_number, total_lines) - from read_func
        """
        encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
        last_error = None

        logger.debug(
            "try_multiple_encodings: %s - trying %d encodings",
            filepath,
            len(encodings),
        )

        for encoding in encodings:
            try:
                result = read_func(filepath, *args, encoding=encoding)
                logger.debug(
                    "try_multiple_encodings: %s - success with %s",
                    filepath,
                    encoding,
                )
                return result
            except (UnicodeDecodeError, LookupError) as e:
                last_error = e
                logger.debug(
                    "try_multiple_encodings: %s - %s failed: %s",
                    filepath,
                    encoding,
                    e,
                )
                continue

        # All encodings failed, try binary
        logger.debug(
            "try_multiple_encodings: %s - all encodings failed, using binary",
            filepath,
        )

        try:
            with open(filepath, "rb") as f:
                content = f.read(MAX_VIEWABLE_SIZE)
                binary_msg = (
                    f"[Binary content - {len(content)} bytes shown]\n{content[:1000]}"
                )
                return binary_msg, 1, None  # Binary starts at line 1
        except Exception as e:
            raise last_error from e

    @staticmethod
    def count_lines(filepath):
        """Count total lines in a file efficiently

        Returns the number of lines matching Python's file iteration behavior.
        """
        start_time = time.time()

        def _count_lines(filepath):
            count = 0
            with open(filepath, "rb") as f:
                for _ in f:
                    count += 1
            return count

        try:
            # For files < 1MB, use direct Python counting (fast and accurate)
            file_size = os.path.getsize(filepath)
            if file_size < 1024 * 1024:  # 1MB
                count = _count_lines(filepath)
                elapsed = time.time() - start_time
                logger.debug(
                    "count_lines: %s - %d lines (Python method), time=%.3fs",
                    filepath,
                    count,
                    elapsed,
                )
                return count

            # For larger files, use wc -l with adjustment for Python semantics
            result = subprocess.run(
                ["wc", "-l", filepath],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            if result.returncode == 0:
                count = int(result.stdout.split()[0])

                # wc -l counts newline characters, not lines
                # If file doesn't end with newline, wc -l undercounts by 1
                # Check last byte to match Python's iteration behavior
                with open(filepath, "rb") as f:
                    f.seek(0, os.SEEK_END)
                    if f.tell() > 0:  # Non-empty file
                        f.seek(-1, os.SEEK_END)
                        last_byte = f.read(1)
                        if last_byte != b"\n":
                            count += 1

                elapsed = time.time() - start_time
                logger.debug(
                    "count_lines: %s - %d lines (wc method), time=%.3fs",
                    filepath,
                    count,
                    elapsed,
                )
                return count

            # Final fallback to Python counting
            count = _count_lines(filepath)
            elapsed = time.time() - start_time
            logger.debug(
                "count_lines: %s - %d lines (fallback method), time=%.3fs",
                filepath,
                count,
                elapsed,
            )
            return count
        except Exception as e:
            logger.warning("Error counting lines in %s: %s", filepath, e)
            return None
