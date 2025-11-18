import logging
from datetime import datetime
from pathlib import Path

_handler_added = False


def new_log_filepath():
    outputs_dir = Path.cwd() / "outputs" / "webserver"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return str(outputs_dir / f"webserver_debug_daemon_{timestamp}.log")


def get_logging_level(log_level):
    if log_level <= 0:
        return logging.ERROR
    if log_level == 1:
        return logging.INFO
    return logging.DEBUG


def new_file_handler(log_file, log_level):
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    formatter = logging.Formatter(
        "%(asctime)s - [%(levelname)s] - %(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    return file_handler


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
    global _handler_added  # pylint: disable=global-statement

    # Only set up once
    if _handler_added:
        return

    from ..log import logger  # pylint: disable=import-outside-toplevel

    log_file = new_log_filepath()
    _level = get_logging_level(log_level)
    file_handler = new_file_handler(log_file, _level)
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
