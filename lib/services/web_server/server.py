import http.server
import logging
import os
import signal
import socket
import socketserver
import sys
import threading
import time

import psutil
import setproctitle

from ..log import logger
from .debug import setup_webserver_daemon_logging
from .handler import CustomHandler


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """HTTP Server that handles requests in separate threads"""

    daemon_threads = True  # Threads will terminate when main thread exits
    request_queue_size = 10  # Limit concurrent connections


class WebServer:
    def __init__(self, ip, port, log_level=0):
        self.ip = ip
        self.port = int(port) if port else 8080
        self.log_level = log_level
        self.process_name = "autotest-portal"
        self.httpd = None
        self.shutdown_flag = threading.Event()

        logger.debug("WebServer initialized: ip=%s, port=%s", ip, self.port)

    def _create_server(self):
        """Create and configure the HTTP server"""
        server_address = (self.ip, self.port)
        httpd = ThreadedHTTPServer(server_address, CustomHandler)
        httpd.timeout = 1.0  # Timeout for serve_forever loop to check shutdown
        logger.debug("HTTP server created: %s", server_address)
        return httpd

    def create(self):
        """Start the HTTP server with error handling"""
        try:
            logger.info("Starting HTTP server on port %s", self.port)
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
                available = True
            except OSError:
                available = False
        logger.debug("Port %s available: %s", self.port, available)
        return available

    def _get_pid_by_port(self):
        """Find the PID of the process listening on the server's port."""
        for conn in psutil.net_connections(kind="inet"):
            if conn.status == "LISTEN" and conn.laddr.port == self.port:
                try:
                    proc = psutil.Process(conn.pid)
                    # Be extra sure by checking if the process name matches
                    if self.process_name in proc.name():
                        logger.debug(
                            "Found process %s (PID %s) listening on port %s",
                            self.process_name,
                            conn.pid,
                            self.port,
                        )
                        return conn.pid
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        return None

    def _is_webserver_exists(self):
        for process in psutil.process_iter(["pid", "name"]):
            if self.process_name in process.info["name"]:
                logger.debug(
                    "Found webserver process: %s (PID %s)",
                    self.process_name,
                    process.info["pid"],
                )
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
        logger.info(
            "Starting watchdog: max_restarts=%s, restart_window=%ss",
            max_restarts,
            restart_window,
        )
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
            logger.debug("Forking daemon process for web server")

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

            # Close inherited file handlers from parent process
            # This prevents both parent and daemon from writing to the same files
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)

            # Set up daemon logging with its own log file
            # Separate from parent process to avoid file conflicts
            setup_webserver_daemon_logging(log_level=self.log_level)

            # Configure logging for daemon
            logging.getLogger("http.server").setLevel(logging.ERROR)
            setproctitle.setproctitle(self.process_name)

            logger.debug("Daemon process started with name: %s", self.process_name)

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


def webserver_main(ip_address, port, _action="start", log_level=0):
    """Main entry point for web server operations"""
    if log_level > 0:
        logger.info(
            "webserver_main called: action=%s, ip=%s, port=%s",
            _action,
            ip_address,
            port,
        )
    server = WebServer(ip_address, port, log_level=log_level)
    if _action == "stop":
        server.stop()
    elif _action == "restart":
        server.restart()
    else:
        server.create_process()
