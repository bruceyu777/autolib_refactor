"""
Web Server Package for Autolib

Provides a web interface for browsing and viewing test files.

Debug Logging:
    Set WEBSERVER_DEBUG_LEVEL environment variable:
    - 0 (default): No debug logging
    - 1: INFO level logs to webserver_debug_daemon_TIMESTAMP.log
    - 2: DEBUG level logs to webserver_debug_daemon_TIMESTAMP.log

    Note: Debug logging is set up in the daemon process only, not in the parent.

Usage:
    from lib.services.web_server import webserver_main, WebServer

    # Start the web server
    webserver_main("0.0.0.0", 8080, "start")

    # Stop the web server
    webserver_main("0.0.0.0", 8080, "stop")

    # Restart the web server
    webserver_main("0.0.0.0", 8080, "restart")
"""

# Import public API
from .server import WebServer, webserver_main

# Expose public API
__all__ = ["webserver_main", "WebServer"]
