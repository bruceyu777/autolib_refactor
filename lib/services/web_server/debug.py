import logging
from datetime import datetime
from pathlib import Path

_handler_added = False
_debug_level = 0


def is_debug_enabled(level=1):
    """Check if debug logging is enabled at the specified level."""
    return _debug_level >= level


def setup_webserver_daemon_logging(log_level=0):
    """Set up web server daemon logging.

    Creates a dedicated log file for the daemon process, separate from parent.

    Args:
        log_level: Debug level (0=errors only, 1=info, 2=debug)

    Based on log_level:
    - 0: ERROR level logs to webserver_daemon.log (errors only)
    - 1: INFO level logs to webserver_debug_daemon_TIMESTAMP.log
    - 2: DEBUG level logs to webserver_debug_daemon_TIMESTAMP.log
    """
    global _handler_added, _debug_level  # pylint: disable=global-statement

    # Set module-level debug level for is_debug_enabled()
    _debug_level = log_level

    # Only set up once
    if _handler_added:
        return

    from ..log import logger  # pylint: disable=import-outside-toplevel

    # Create log file in outputs directory
    outputs_dir = Path.cwd() / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    if log_level == 0:
        _level = logging.ERROR
        log_file = outputs_dir / "webserver_daemon.log"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = outputs_dir / f"webserver_debug_daemon_{timestamp}.log"
        _level = logging.DEBUG if log_level >= 2 else logging.INFO

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(_level)

    # Create formatter based on debug level
    if is_debug_enabled():
        formatter = logging.Formatter(
            "%(asctime)s - [%(levelname)s] - %(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - [%(levelname)s] - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Set logger level to capture messages at the desired level
    # No conditional needed - we're in isolated daemon process with fresh handlers
    logger.setLevel(_level)

    # Log initialization (only if debug mode)
    if log_level > 0:
        logger.info("=" * 80)
        logger.info("Web Server Daemon Logging Initialized (Level %d)", log_level)
        logger.info("Log file: %s", log_file)
        logger.info("=" * 80)

    _handler_added = True


# Keep backward compatibility
setup_webserver_debug_logging = setup_webserver_daemon_logging
