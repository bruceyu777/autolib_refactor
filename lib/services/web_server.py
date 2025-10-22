import http.server
import logging
import os
import re
import signal
import socket
import socketserver
import subprocess
import sys
import threading
import time
import traceback

from datetime import datetime
from urllib.parse import parse_qs, quote, urlparse

import psutil
import setproctitle

from .log import logger
from .template_env import web_server_env

# File size constants
SMALL_FILE_LINE_LIMIT = 10000  # 10K lines - show entire file
DEFAULT_TAIL_LINES = 1000
DEFAULT_HEAD_LINES = 1000
MAX_VIEWABLE_SIZE = 10 * 1024 * 1024  # 10MB per chunk

# pylint: disable=broad-exception-raised


class FileReader:

    BLOCK_SIZE = 4096  # Block size for backward reading

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
        try:
            with open(filepath, "rb") as f:
                # Get file size
                f.seek(0, os.SEEK_END)
                file_size = f.tell()

                if file_size == 0:
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
        try:
            lines = []
            with open(filepath, "r", encoding=encoding) as f:
                for i, line in enumerate(f):
                    if i >= num_lines:
                        break
                    lines.append(line.rstrip("\n"))
            content = "\n".join(lines)
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
            # Range uses the provided start_line
            return content, start_line
        except Exception as e:
            logger.error("Error reading range of file %s: %s", filepath, e)
            raise

    @staticmethod
    def search_in_file(filepath, pattern, context_lines=5):
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

            if result.returncode == 0:
                return result.stdout
            if result.returncode == 1:
                return None
            raise Exception(f"grep failed: {result.stderr}")
        except subprocess.TimeoutExpired as e:
            raise Exception("Search timeout (30s exceeded)") from e
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

        for encoding in encodings:
            try:
                return read_func(filepath, *args, encoding=encoding)
            except (UnicodeDecodeError, LookupError) as e:
                last_error = e
                continue

        # All encodings failed, try binary
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
                return _count_lines(filepath)

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

                return count

            # Final fallback to Python counting
            return _count_lines(filepath)
        except Exception as e:
            logger.warning("Error counting lines in %s: %s", filepath, e)
            return None


# Define a custom handler that suppresses logging messages
class CustomHandler(http.server.SimpleHTTPRequestHandler):

    viewable_testfile_prefix = ("grp.",)
    viewable_testfile_extension = (
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

    @staticmethod
    def _is_viewable(safe_path):
        if os.path.isfile(safe_path):
            if os.path.basename(safe_path).startswith(
                CustomHandler.viewable_testfile_prefix
            ):
                return True
            file_extension = os.path.splitext(safe_path)[-1]
            return file_extension in CustomHandler.viewable_testfile_extension
        return False

    def _get_file_line_size_tier(self, line_count):
        # Small files: less than 10K lines, show everything
        if line_count is not None and line_count >= SMALL_FILE_LINE_LIMIT:
            return "large"
        return "non_large"

    def _escape_html(self, content):
        """Escape HTML special characters"""
        return content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _render_template_response(self, template_name, **kwargs):
        """Render a template and send HTTP response"""
        try:
            template = web_server_env.get_template(template_name)
            response_content = template.render(**kwargs)
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(response_content.encode("utf-8"))
        except Exception as e:
            logger.error(
                "Error rendering template %s: %s", template_name, e, exc_info=True
            )
            self.send_error(500, f"Template error: {type(e).__name__}")

    def _load_non_large_file(self, safe_path, file_size, line_count):
        try:
            file_content, start_line = FileReader.try_multiple_encodings(
                safe_path, FileReader.read_file_tail, line_count or DEFAULT_TAIL_LINES
            )
            file_content = self._escape_html(file_content)

            self._render_template_response(
                "large_file_viewer.template",
                path=self.path,
                breadcrumbs=self._prepare_breadcrumbs(),
                file_content=file_content,
                file_size=file_size,
                view_mode="full",
                num_lines=line_count,
                total_lines=line_count,
                start_line_number=start_line,
                show_file_controls=True,
            )
        except Exception as e:
            logger.error(
                "Error loading medium file %s: %s", safe_path, e, exc_info=True
            )
            raise

    def _load_large_file_options(self, safe_path, file_size):
        """Show options menu for large files (>100MB)"""
        total_lines = FileReader.count_lines(safe_path)

        self._render_template_response(
            "large_file_options.template",
            path=self.path,
            breadcrumbs=self._prepare_breadcrumbs(),
            file_size=file_size,
            total_lines=total_lines,
        )

    def _load_response_for_html_file(self, safe_path):
        with open(safe_path, "r", encoding="utf-8") as file:
            file_content = file.read()
        template = web_server_env.get_template("html_file.template")
        response_content = template.render(
            path=self.path,
            breadcrumbs=self._prepare_breadcrumbs(),
            file_content=file_content,
        )
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(response_content.encode("utf-8"))

    def _load_response_with_file_content(self, safe_path):
        """Load and display file content based on file size and line count"""
        try:
            file_size = os.path.getsize(safe_path)
            line_count = FileReader.count_lines(safe_path)
            tier = self._get_file_line_size_tier(line_count)

            if tier == "large":
                self._load_large_file_options(safe_path, file_size)
            else:
                self._load_non_large_file(safe_path, file_size, line_count)

        except FileNotFoundError:
            self.send_error(404, "File not found")
        except PermissionError:
            self.send_error(403, "Permission denied")
        except Exception as e:
            logger.error("Error loading file %s: %s", safe_path, e, exc_info=True)
            self.send_error(500, f"Internal server error: {type(e).__name__}")

    def format_size(self, size):
        for unit in ["B", "KiB", "MiB", "GiB"]:
            if size < 1024.0:
                break
            size /= 1024.0
        return f"{size:.1f} {unit}"

    def format_date(self, timestamp):
        return datetime.fromtimestamp(timestamp).strftime("%Y-%b-%d %H:%M")

    def _prepare_breadcrumbs(self, path=None):
        """Prepare breadcrumb navigation from a path

        Args:
            path: The path to create breadcrumbs for. If None, uses self.path
        """
        if path is None:
            path = self.path

        # Remove query parameters if present
        path = urlparse(path).path

        parts = path.strip(os.sep).split(os.sep)
        breadcrumbs = [("Home", os.sep)]
        link_path = os.sep
        for part in parts:
            if part:
                link_path = os.path.join(link_path, part)
                breadcrumbs.append((part, quote(link_path)))
        return breadcrumbs

    def _prepare_directory_meta(self, path):
        dir_list = os.listdir(path)
        directory_meta = []
        for name in dir_list:
            if name.startswith("."):
                continue
            full_path = os.path.join(path, name)
            display_name = name

            if os.path.isdir(full_path):
                display_name += os.sep
                icon_class = "folder"
                size = None
                mtime = os.path.getmtime(full_path)
            else:
                icon_class = "file"
                size = self.format_size(os.path.getsize(full_path))
                mtime = os.path.getmtime(full_path)
            date = self.format_date(mtime)

            directory_meta.append(
                {
                    "display_name": display_name,
                    "link": quote(display_name),
                    "icon": icon_class,
                    "size": size,
                    "date": date,
                    "mtime": mtime,
                }
            )
        # Sort by modification time, newest first
        directory_meta.sort(key=lambda x: x["mtime"], reverse=True)
        return directory_meta

    def list_directory(self, path):
        try:
            directory_meta = self._prepare_directory_meta(path)
            template = web_server_env.get_template("index.template")
            response_content = template.render(
                path=self.path,
                breadcrumbs=self._prepare_breadcrumbs(),
                directory_list=directory_meta,
            )
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(response_content.encode("utf-8"))
        except PermissionError:
            self.send_error(403, "No permission to list directory")
        except FileNotFoundError:
            self.send_error(404, "Directory not found")
        except Exception as e:
            logger.error("Error listing directory %s: %s", path, e, exc_info=True)
            self.send_error(500, f"Internal server error: {type(e).__name__}")

    def _parse_query_params(self):
        """Parse query parameters from URL"""
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        # Convert lists to single values for convenience
        return {k: v[0] if len(v) == 1 else v for k, v in params.items()}

    def _handle_tail_endpoint(self, safe_path, params):
        try:
            total_lines = FileReader.count_lines(safe_path)
            requested_lines = int(params.get("lines", DEFAULT_TAIL_LINES))
            num_lines = (
                min(total_lines, requested_lines) if total_lines else requested_lines
            )

            file_content, start_line = FileReader.try_multiple_encodings(
                safe_path, FileReader.read_file_tail, num_lines
            )
            file_content = self._escape_html(file_content)
            file_size = os.path.getsize(safe_path)

            self._render_template_response(
                "large_file_viewer.template",
                path=params.get("path"),
                breadcrumbs=self._prepare_breadcrumbs(params.get("path")),
                file_content=file_content,
                file_size=file_size,
                view_mode="tail",
                num_lines=num_lines,
                total_lines=total_lines,
                start_line_number=start_line,
                show_file_controls=True,
            )
        except Exception as e:
            logger.error("Error in tail endpoint: %s", e, exc_info=True)
            self.send_error(500, str(e))

    def _handle_head_endpoint(self, safe_path, params):
        try:
            total_lines = FileReader.count_lines(safe_path)
            requested_lines = int(params.get("lines", DEFAULT_HEAD_LINES))
            num_lines = (
                min(total_lines, requested_lines) if total_lines else requested_lines
            )

            file_content, start_line = FileReader.try_multiple_encodings(
                safe_path, FileReader.read_file_head, num_lines
            )
            file_content = self._escape_html(file_content)
            file_size = os.path.getsize(safe_path)

            self._render_template_response(
                "large_file_viewer.template",
                path=params.get("path"),
                breadcrumbs=self._prepare_breadcrumbs(params.get("path")),
                file_content=file_content,
                file_size=file_size,
                view_mode="head",
                num_lines=num_lines,
                total_lines=total_lines,
                start_line_number=start_line,
                show_file_controls=True,
            )
        except Exception as e:
            logger.error("Error in head endpoint: %s", e, exc_info=True)
            self.send_error(500, str(e))

    def _handle_range_endpoint(self, safe_path, params):
        try:
            start_line = int(params.get("start", 1))
            total_lines = FileReader.count_lines(safe_path)
            requested_end = int(params.get("end", start_line + 1000))
            end_line = min(total_lines, requested_end) if total_lines else requested_end

            file_content, line_start = FileReader.try_multiple_encodings(
                safe_path, FileReader.read_file_range, start_line, end_line
            )
            file_content = self._escape_html(file_content)
            file_size = os.path.getsize(safe_path)

            self._render_template_response(
                "large_file_viewer.template",
                path=params.get("path"),
                breadcrumbs=self._prepare_breadcrumbs(params.get("path")),
                file_content=file_content,
                file_size=file_size,
                view_mode="range",
                start_line=start_line,
                end_line=end_line,
                total_lines=total_lines,
                start_line_number=line_start,
                show_file_controls=True,
            )
        except Exception as e:
            logger.error("Error in range endpoint: %s", e, exc_info=True)
            self.send_error(500, str(e))

    def _handle_search_endpoint(self, safe_path, params):
        try:
            pattern = params.get("pattern", "")

            if not pattern:
                self.send_error(400, "Missing 'pattern' parameter")
                return

            search_result = FileReader.search_in_file(safe_path, pattern)
            if search_result is None:
                search_result = f"No matches found for pattern: {pattern}"
            else:
                search_result = self._escape_html(search_result)

            file_size = os.path.getsize(safe_path)
            total_lines = FileReader.count_lines(safe_path)

            self._render_template_response(
                "large_file_viewer.template",
                path=params.get("path"),
                breadcrumbs=self._prepare_breadcrumbs(params.get("path")),
                file_content=search_result,
                file_size=file_size,
                view_mode="search",
                search_pattern=pattern,
                total_lines=total_lines,
                start_line_number=None,  # grep includes line numbers already
                show_file_controls=True,
            )
        except Exception as e:
            logger.error("Error in search endpoint: %s", e, exc_info=True)
            self.send_error(500, str(e))

    def extract_api_endpoint(self):
        for api in self.api_endpoint_handlers:
            if f"__{api}__" in self.path:
                return api
        return None

    def _handle_health_check(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def _handle_download_endpoint(self, safe_path):
        try:
            with open(safe_path, "rb") as file:
                content = file.read()
            self.send_response(200)
            self.send_header(
                "Content-disposition",
                f"attachment; filename={os.path.basename(safe_path)}",
            )
            self.send_header("Content-length", str(len(content)))
            self.send_header("Content-type", "application/octet-stream")
            self.end_headers()
            self.wfile.write(content)

        except Exception as e:
            logger.error("Error in download endpoint: %s", e, exc_info=True)
            self.send_error(500, str(e))

    @property
    def api_endpoint_handlers(self):
        return  {
            "health": self._handle_health_check,
            "tail": self._handle_tail_endpoint,
            "head": self._handle_head_endpoint,
            "range": self._handle_range_endpoint,
            "search": self._handle_search_endpoint,
            "download": self._handle_download_endpoint,
        }

    def api_handling(self, api_endpoint, params):
        handler_func = self.api_endpoint_handlers.get(api_endpoint)
        if not handler_func:
            self.send_error(404, "API endpoint not found")
            return

        # Health check doesn't require a file path
        if api_endpoint == "health":
            handler_func()
            return

        filepath = params.get("path")
        if not filepath:
            self.send_error(400, "Missing 'path' parameter")
            return

        safe_path = self.translate_path(filepath)
        if not os.path.isfile(safe_path):
            self.send_error(404, "File not found: %s" % safe_path)
            return

        handler_func(safe_path, params)
        return

    def do_GET(self):
        try:
            api_endpoint = self.extract_api_endpoint()
            if api_endpoint:
                params = self._parse_query_params()
                self.api_handling(api_endpoint, params)
                return

            # Regular file serving
            safe_path = self.translate_path(self.path)
            if CustomHandler._is_viewable(safe_path):
                if safe_path.endswith(".html"):
                    self._load_response_for_html_file(safe_path)
                else:
                    self._load_response_with_file_content(safe_path)
            else:
                super().do_GET()
        except BrokenPipeError:
            pass
        except Exception as e:
            logger.error("Error in do_GET for path %s: %s", self.path, e, exc_info=True)
            try:
                self.send_error(
                    500, f"Internal server error: {traceback.format_exc()}, path: {self.path}"
                )
            except Exception:
                pass

    # pylint: disable=redefined-builtin
    def log_message(self, format, *args):
        pass


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """HTTP Server that handles requests in separate threads"""

    daemon_threads = True  # Threads will terminate when main thread exits
    request_queue_size = 10  # Limit concurrent connections


class WebServer:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = int(port) if port else 8080
        self.process_name = "autotest-portal"
        self.httpd = None
        self.shutdown_flag = threading.Event()

    def _create_server(self):
        """Create and configure the HTTP server"""
        server_address = (self.ip, self.port)
        httpd = ThreadedHTTPServer(server_address, CustomHandler)
        httpd.timeout = 1.0  # Timeout for serve_forever loop to check shutdown
        return httpd

    def create(self):
        """Start the HTTP server with error handling"""
        try:
            self.httpd = self._create_server()
            logger.info("HTTP server started on port %s", self.port)
            while not self.shutdown_flag.is_set():
                self.httpd.handle_request()
            self.httpd.serve_forever()
        except OSError as e:
            logger.error("Unable to start webserver: %s", e)
            raise
        except Exception as e:
            logger.error("Unexpected error in web server: %s", e, exc_info=True)
            raise
        finally:
            if self.httpd:
                self.httpd.server_close()
                logger.info("HTTP server stopped on port %s", self.port)

    def shutdown(self):
        """Gracefully shutdown the server"""
        if not self.shutdown_flag.is_set():
            logger.info("Shutting down web server...")
            self.shutdown_flag.set()
            if self.httpd:
                self.httpd.shutdown()

    def _is_process_running(self, pid):
        """Check if a process with given PID is running"""
        try:
            # Send signal 0 to check if process exists
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def _is_port_available(self):
        # Try to create a socket on the specified port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((self.ip, self.port))
                return True  # Port is open and available
            except OSError:
                return False  # Port is already in use

    def _get_pid_by_port(self):
        """Find the PID of the process listening on the server's port."""
        for conn in psutil.net_connections(kind="inet"):
            if conn.status == "LISTEN" and conn.laddr.port == self.port:
                try:
                    proc = psutil.Process(conn.pid)
                    # Be extra sure by checking if the process name matches
                    if self.process_name in proc.name():
                        return conn.pid
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        return None

    def _is_webserver_exists(self):
        for process in psutil.process_iter(["pid", "name"]):
            if self.process_name in process.info["name"]:
                return True
        return False

    def _is_already_started(self):
        """Check if web server is already running"""
        pid = self._get_pid_by_port()
        if pid:
            logger.info(
                "HTTP server is already running on port %s (PID: %d)",
                self.port,
                pid,
            )
            return True

        # if the port is used by another process
        if not self._is_port_available():
            if self._is_webserver_exists():
                logger.info(
                    "HTTP server is already running on port %s",
                    self.port,
                )
                return True

            logger.warning(
                (
                    "Another service is already on port %d, you can specify another port in"
                    " your env file if you want to use web server."
                ),
                self.port,
            )
            sys.exit(1)

        return False

    def _setup_signal_handlers(self, server_instance):
        """Setup signal handlers for graceful shutdown"""

        # pylint: disable=unused-argument
        def signal_handler(signum, frame):
            logger.info("Received signal %s, initiating graceful shutdown", signum)
            server_instance.shutdown()

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    def _run_with_watchdog(self, max_restarts=5, restart_window=300):
        restart_times = []
        consecutive_failures = 0

        while True:
            # Clean up old restart times outside the window
            cutoff = time.time() - restart_window
            restart_times = [t for t in restart_times if t > cutoff]

            # Check if we've exceeded max restarts
            if len(restart_times) >= max_restarts:
                logger.error(
                    "Max restart limit reached (%d in %ds), giving up",
                    max_restarts,
                    restart_window,
                )
                sys.exit(1)

            # Log restart information
            if restart_times:
                logger.info(
                    "Starting web server (restarts in last %ds: %d)",
                    restart_window,
                    len(restart_times),
                )
            else:
                logger.info("Starting web server for the first time")

            try:
                # Setup signal handlers
                self._setup_signal_handlers(self)

                # Start the server
                self.create()

                # If we get here, server stopped cleanly
                logger.info("Web server stopped cleanly")
                break

            except KeyboardInterrupt:
                logger.info("Web server interrupted by user")
                break

            except Exception as e:
                consecutive_failures += 1
                restart_times.append(time.time())

                logger.error(
                    "Web server crashed (consecutive failures: %d): %s",
                    consecutive_failures,
                    e,
                    exc_info=True,
                )

                # Exponential backoff for restart delay
                delay = min(5 * (2 ** (consecutive_failures - 1)), 60)
                logger.info("Waiting %d seconds before restart...", delay)
                time.sleep(delay)

        logger.info("Watchdog shutting down")

    def start(self):
        """Fork a daemon process and start the web server with watchdog"""
        try:
            pid = os.fork()
            if pid > 0:
                # Parent process returns
                logger.info("Web server daemon forked with PID %d", pid)
                return
        except OSError as e:
            logger.error("Fork failed: %s", e)
            sys.exit(1)

        # Child process (daemon)
        try:
            os.setsid()
            os.umask(0)

            # Redirect standard file descriptors
            sys.stdout.flush()
            sys.stderr.flush()
            with open("/dev/null", "r") as devnull:
                os.dup2(devnull.fileno(), sys.stdin.fileno())
                os.dup2(devnull.fileno(), sys.stdout.fileno())
                os.dup2(devnull.fileno(), sys.stderr.fileno())

            # Configure logging for daemon
            logging.getLogger("http.server").setLevel(logging.ERROR)
            setproctitle.setproctitle(self.process_name)
            # Run with watchdog
            self._run_with_watchdog(max_restarts=5, restart_window=300)

        except Exception as e:
            logger.error("Fatal error in daemon process: %s", e, exc_info=True)
            sys.exit(1)
        finally:
            pass

    def create_process(self):
        if self._is_already_started():
            return
        self.start()

    def stop(self):
        logger.info("Attempting to stop the web server on port %d...", self.port)
        pid = self._get_pid_by_port()
        if not pid:
            logger.info(
                "No '%s' process found listening on port %d.",
                self.process_name,
                self.port,
            )
            return

        logger.info("Sending SIGKILL to web server process (PID: %d)", pid)
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError as e:
            logger.error("Failed to send SIGKILL to PID %d: %s", pid, e)
            return

        # Poll for process termination and port availability
        stop_time = time.time() + 10  # 10-second timeout
        while time.time() < stop_time:
            if not self._is_process_running(pid):
                logger.info("Web server process (PID: %d) has terminated.", pid)
                time.sleep(1)
                if self._is_port_available():
                    logger.info("Port %d is now free. Shutdown successful.", self.port)
                    return
                logger.warning(
                    "Process terminated, but port %d is still in use.", self.port
                )
            time.sleep(0.5)

        logger.warning(
            (
                "Web server process (PID: %d) did not terminate gracefully within 10 seconds. "
                "It might require manual intervention."
            ),
            pid,
        )
        return

    def restart(self):
        logger.info("Restarting web server...")
        self.stop()
        time.sleep(2)  # Give a moment for resources to be released
        self.start()


def webserver_main(ip_address, port, _action="start"):
    if _action == "stop":
        WebServer(ip_address, port).stop()
    elif _action == "restart":
        WebServer(ip_address, port).restart()
    else:
        WebServer(ip_address, port).create_process()
