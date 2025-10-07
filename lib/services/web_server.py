import http.server
import logging
import os
import socket
import sys
from datetime import datetime
from urllib.parse import quote

import psutil
import setproctitle

from .log import logger
from .template_env import web_server_env


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

    def _load_response_with_file_content(self, safe_path):
        with open(safe_path, "r", encoding="utf-8") as file:
            file_content = file.read()
        if not safe_path.endswith((".html",)):
            file_content = (
                file_content.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            template = web_server_env.get_template("viewable_file.template")
        else:
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

    def format_size(self, size):
        for unit in ["B", "KiB", "MiB", "GiB"]:
            if size < 1024.0:
                break
            size /= 1024.0
        return f"{size:.1f} {unit}"

    def format_date(self, timestamp):
        return datetime.fromtimestamp(timestamp).strftime("%Y-%b-%d %H:%M")

    def _prepare_breadcrumbs(self):
        parts = self.path.strip(os.sep).split(os.sep)
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
        except OSError:
            self.send_error(404, "No permission to list directory")
        else:
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

    def do_GET(self):
        safe_path = self.translate_path(self.path)
        if CustomHandler._is_viewable(safe_path):
            self._load_response_with_file_content(safe_path)
        else:
            super().do_GET()

    # pylint: disable=redefined-builtin
    def log_message(self, format, *args):
        pass


class WebServer:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = int(port)
        self.process_name = "autotest-portal"

    def create(self):
        server_address = ("", self.port)
        try:
            httpd = http.server.HTTPServer(server_address, CustomHandler)
            httpd.serve_forever()
        except OSError as e:
            logger.error("Unable to start webserver as '%s'", e)
        else:
            logger.info(
                "Succeeded to start HTTP server on port %s",
                self.port,
            )

    def _is_port_available(self):
        # Try to create a socket on the specified port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("localhost", self.port))
                return True  # Port is open and available
            except OSError:
                return False  # Port is already in use

    def _is_webserver_exists(self):
        for process in psutil.process_iter(["pid", "name"]):
            if self.process_name in process.info["name"]:
                return True
        return False

    def _is_already_started(self):
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

    def start(self):
        try:
            pid = os.fork()
            if pid > 0:
                return
        except OSError as e:
            print(f"Fork failed: {e}")
            sys.exit(1)

        os.setsid()
        os.umask(0)

        sys.stdout.flush()
        sys.stderr.flush()
        with open("/dev/null", "r") as devnull:
            os.dup2(devnull.fileno(), sys.stdin.fileno())
            os.dup2(devnull.fileno(), sys.stdout.fileno())
            os.dup2(devnull.fileno(), sys.stderr.fileno())

        logging.getLogger("http.server").setLevel(logging.ERROR)
        setproctitle.setproctitle(self.process_name)
        self.create()

    def create_process(self):
        if self._is_already_started():
            return
        self.start()


def launch_webserver_on(ip_address, port):
    WebServer(ip_address, port).create_process()
