import http.server
import os
import traceback
from datetime import datetime
from urllib.parse import parse_qs, quote, urlparse

from ..log import logger
from .constants import (
    SMALL_FILE_LINE_LIMIT,
    VIEWABLE_TESTFILE_EXTENSION,
    VIEWABLE_TESTFILE_PREFIX,
)
from .file_reader import FileReader
from .templates_loader import web_server_template_env


class CustomHandler(http.server.SimpleHTTPRequestHandler):

    viewable_testfile_prefix = VIEWABLE_TESTFILE_PREFIX
    viewable_testfile_extension = VIEWABLE_TESTFILE_EXTENSION

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
            template = web_server_template_env.get_template(template_name)
            response_content = template.render(**kwargs)
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(response_content.encode("utf-8"))

            logger.debug("Rendered template: %s for path: %s", template_name, self.path)
        except Exception as e:
            logger.error(
                "Error rendering template %s: %s", template_name, e, exc_info=True
            )
            logger.error(
                "Template rendering failed: %s - %s: %s",
                template_name,
                type(e).__name__,
                e,
            )
            self.send_error(500, f"Template error: {type(e).__name__}")

    def _load_non_large_file(self, safe_path, file_size, line_count):
        try:
            logger.debug(
                "Loading non-large file: %s (size=%s, lines=%s)",
                safe_path,
                file_size,
                line_count,
            )

            file_content, start_line = FileReader.try_multiple_encodings(
                safe_path, FileReader.read_file_tail, line_count or 1000
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
            logger.error(
                "Failed to load non-large file: %s - %s: %s",
                safe_path,
                type(e).__name__,
                e,
            )
            raise

    def _load_large_file_options(self, safe_path, file_size):
        logger.debug("Loading large file options: %s (size=%s)", safe_path, file_size)
        total_lines = FileReader.count_lines(safe_path)
        self._render_template_response(
            "large_file_options.template",
            path=self.path,
            breadcrumbs=self._prepare_breadcrumbs(),
            file_size=file_size,
            total_lines=total_lines,
        )

    def _load_response_for_html_file(self, safe_path):
        logger.debug("Loading HTML file: %s", safe_path)
        with open(safe_path, "r", encoding="utf-8") as file:
            file_content = file.read()
        template = web_server_template_env.get_template("html_file.template")
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
        try:
            logger.info("Loading file: %s", safe_path)
            file_size = os.path.getsize(safe_path)
            line_count = FileReader.count_lines(safe_path)
            tier = self._get_file_line_size_tier(line_count)

            if tier == "large":
                self._load_large_file_options(safe_path, file_size)
            else:
                self._load_non_large_file(safe_path, file_size, line_count)

        except FileNotFoundError:
            logger.error("File not found: %s", safe_path)
            self.send_error(404, "File not found")
        except PermissionError:
            logger.error("Permission denied: %s", safe_path)
            self.send_error(403, "Permission denied")
        except Exception as e:
            logger.error("Error loading file %s: %s", safe_path, e, exc_info=True)
            logger.error(
                "Failed to load file: %s - %s: %s", safe_path, type(e).__name__, e
            )
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
            logger.debug("Listing directory: %s", path)
            directory_meta = self._prepare_directory_meta(path)
            template = web_server_template_env.get_template("index.template")
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
            logger.error("Permission denied listing directory: %s", path)
            self.send_error(403, "No permission to list directory")
        except FileNotFoundError:
            logger.error("Directory not found: %s", path)
            self.send_error(404, "Directory not found")
        except Exception as e:
            logger.error("Error listing directory %s: %s", path, e, exc_info=True)
            logger.error(
                "Failed to list directory: %s - %s: %s", path, type(e).__name__, e
            )
            self.send_error(500, f"Internal server error: {type(e).__name__}")

    def _parse_query_params(self):
        """Parse query parameters from URL"""
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        # Convert lists to single values for convenience
        return {k: v[0] if len(v) == 1 else v for k, v in params.items()}

    def _handle_tail_endpoint(self, safe_path, params):
        try:
            logger.info("API tail: %s - lines=%s", safe_path, params.get("lines", 1000))

            total_lines = FileReader.count_lines(safe_path)
            requested_lines = int(params.get("lines", 1000))
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
            logger.error("API tail failed: %s - %s: %s", safe_path, type(e).__name__, e)
            self.send_error(500, str(e))

    def _handle_head_endpoint(self, safe_path, params):
        try:
            logger.info("API head: %s - lines=%s", safe_path, params.get("lines", 1000))

            total_lines = FileReader.count_lines(safe_path)
            requested_lines = int(params.get("lines", 1000))
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
            logger.error("API head failed: %s - %s: %s", safe_path, type(e).__name__, e)
            self.send_error(500, str(e))

    def _handle_range_endpoint(self, safe_path, params):
        try:
            start_line = int(params.get("start", 1))
            requested_end = int(params.get("end", start_line + 1000))

            logger.info(
                "API range: %s - lines %s-%s", safe_path, start_line, requested_end
            )

            total_lines = FileReader.count_lines(safe_path)
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
            logger.error(
                "API range failed: %s - %s: %s", safe_path, type(e).__name__, e
            )
            self.send_error(500, str(e))

    def _handle_search_endpoint(self, safe_path, params):
        try:
            pattern = params.get("pattern", "")

            logger.info("API search: %s - pattern='%s'", safe_path, pattern)

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
            logger.error(
                "API search failed: %s - pattern='%s' - %s: %s",
                safe_path,
                pattern,
                type(e).__name__,
                e,
            )
            self.send_error(500, str(e))

    def extract_api_endpoint(self):
        for api in self.api_endpoint_handlers:
            if f"__{api}__" in self.path:
                return api
        return None

    def _handle_health_check(self):
        logger.debug("API health check")

        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def _handle_download_endpoint(self, safe_path, _params):
        try:
            logger.info("API download: %s", safe_path)

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
            logger.error(
                "API download failed: %s - %s: %s", safe_path, type(e).__name__, e
            )
            self.send_error(500, str(e))

    @property
    def api_endpoint_handlers(self):
        return {
            "health": self._handle_health_check,
            "tail": self._handle_tail_endpoint,
            "head": self._handle_head_endpoint,
            "range": self._handle_range_endpoint,
            "search": self._handle_search_endpoint,
            "download": self._handle_download_endpoint,
        }

    def api_handling(self, api_endpoint, params):
        logger.debug("API request: %s - params=%s", api_endpoint, params)

        handler_func = self.api_endpoint_handlers.get(api_endpoint)
        if not handler_func:
            logger.error("API endpoint not found: %s", api_endpoint)
            self.send_error(404, "API endpoint not found")
            return

        # Health check doesn't require a file path
        if api_endpoint == "health":
            handler_func()
            return

        filepath = params.get("path")
        if not filepath:
            logger.error("API %s: missing 'path' parameter", api_endpoint)
            self.send_error(400, "Missing 'path' parameter")
            return

        safe_path = self.translate_path(filepath)
        if not os.path.isfile(safe_path):
            logger.error("API %s: file not found - %s", api_endpoint, safe_path)
            self.send_error(404, "File not found: %s" % safe_path)
            return

        handler_func(safe_path, params)
        return

    def do_GET(self):
        try:
            logger.debug("GET request: %s", self.path)

            api_endpoint = self.extract_api_endpoint()
            if api_endpoint:
                params = self._parse_query_params()
                self.api_handling(api_endpoint, params)
                return

            # Regular file serving
            safe_path = self.translate_path(self.path)
            if CustomHandler._is_viewable(safe_path):
                if safe_path.endswith((".html", ".htm")):
                    self._load_response_for_html_file(safe_path)
                else:
                    self._load_response_with_file_content(safe_path)
            else:
                super().do_GET()
        except BrokenPipeError:
            pass
        except Exception as e:
            logger.error("Error in do_GET for path %s: %s", self.path, e, exc_info=True)
            logger.error(
                "do_GET failed: %s - %s: %s\n%s",
                self.path,
                type(e).__name__,
                e,
                traceback.format_exc(),
            )
            try:
                self.send_error(
                    500,
                    f"Internal server error: {traceback.format_exc()}, path: {self.path}",
                )
            except Exception:
                pass

    # pylint: disable=redefined-builtin
    def log_message(self, format, *args):
        pass
