import http.server
import logging
import os
import socket
import sys

import psutil
import setproctitle

from lib.services.log import logger


# Define a custom handler that suppresses logging messages
class CustomHandler(http.server.SimpleHTTPRequestHandler):

    @staticmethod
    def _is_viewable(safe_path):

        file_extension = not os.path.splitext(safe_path)[1]
        return file_extension in (".log", ".txt", ".env", ".vm", "")

    def _load_response_with_file_content(self, safe_path):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        with open(safe_path, "rb") as file:
            self.wfile.write(file.read())

    def do_GET(self):
        safe_path = self.translate_path(self.path)
        if self._is_viewable(safe_path):
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
        self.process_name = "web_server_autotest"

    def create(self):
        server_address = ("", self.port)
        httpd = http.server.HTTPServer(server_address, CustomHandler)
        httpd.serve_forever()

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
            logger.notice(
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
        logger.info(
            "Succeeded to start HTTP server on port %s",
            self.port,
        )

    def create_process(self):
        if self._is_already_started():
            return
        self.start()
