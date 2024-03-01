import argparse
import http.server
import socket
import psutil
import logging
import setproctitle
import os
from lib.services.log import logger
import sys


# Define a custom handler that suppresses logging messages
class SilentHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

class WebServer:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = int(port)
        self.process_name = "web_server_autotest"

    def create(self):
        server_address = ("", self.port)
        httpd = http.server.HTTPServer(
            server_address, SilentHandler
        )
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

    def start(self):
        logging.getLogger('http.server').setLevel(logging.ERROR)
        setproctitle.setproctitle(self.process_name)
        if not self._is_port_available():
            if self._is_webserver_exists():
                logger.info(
                    "HTTP server is already running on port %s",
                    self.port,
                )
                sys.exit(0)
            else:
                logger.notice(
                    "Another service is already on port %s, you can specify another port in your env file if you want to use web server.",
                    self.port,
                )
        else:
            self.create()
            logger.info(
                "Succeeded to start HTTP server on port %s",
                self.port,
            )

    def create_process(self):
        pid = os.fork()
        if pid == 0:
            setproctitle.setproctitle(self.process_name)
            self.start()
        else:
            logger.info('After creating web server for autotest.')


# def create_process(args):
#     pid = os.fork()
#     if pid == 0:
#         # while True:
#         print(f"subprocess pid: {os.getpid()}")
#         setproctitle.setproctitle("web_server_autotest")
#         WebServer(args.ip, args.port).start()

#     else:
#         print('parent process.')

# if __name__ == "__main__":
#     from multiprocessing import Process
#     import time, os

#     parser = argparse.ArgumentParser(description="Start AutoTest Web Server.")
#     parser.add_argument(
#         "-i",
#         "--ip",
#         dest="ip",
#         help="Host Ip Address",
#         required=True,
#     )
#     parser.add_argument(
#         "-p",
#         "--port",
#         dest="port",
#         help="Host Port",
#         required=True,
#     )

#     args = parser.parse_args()
#     create_process(args)

