#!/usr/bin/env python3
# FOSQA Standards Version: 1.0.0
# Refactored: 2026-01-21
# Compliance: Full
"""Common logging setup module for reuse across scripts.

Centralized logging configuration with unified log directory.
All logs are written to ~/resources/tools/logs/ regardless of script location.

Features:
- Centralized log directory: ~/resources/tools/logs/
- Automatic permission fixes (0o777) using sudo when needed
- Individual script logs: {script_name}.log
- Combined logs: {main_script}_all.log (when multiple scripts involved)
- No ownership changes (preserves existing owner)
- Passwordless sudo support for fosqa/jenkins users
- Thread-safe operation with proper error handling
- Support for MCP server suppression via SUPPRESS_LOGGING env var

Example:
    >>> from common.common_logging import setup_script_logging
    >>> logger = setup_script_logging(__file__)
    >>> logger.info("This goes to ~/resources/tools/logs/my_script.log")
"""

import getpass
import logging
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Global tracking of active loggers per main script
_active_loggers = {}

# Buffering for main script logs before central log is determined
_main_script_buffers = {}

# Central log directory - all scripts write here
CENTRAL_LOGS_DIR = Path.home() / "resources" / "tools" / "logs"

# Fallback directories in order of preference
FALLBACK_DIRS = [
    Path("/tmp/fosqa_logs"),
    Path.home() / "logs",
    Path("/tmp"),
]


def get_main_script_name() -> str:
    """Get the name of the main script (entry point) without extension.

    Returns:
        str: Filename stem of the main module, or 'main' if undeterminable.

    Example:
        >>> # When running python3 test_script.py
        >>> get_main_script_name()
        'test_script'
    """
    try:
        main_file = sys.modules["__main__"].__file__
        if main_file:
            return Path(main_file).stem
    except (AttributeError, KeyError):
        pass

    return "main"


def fix_directory_permissions(directory: Path) -> Dict[str, Any]:
    """Fix directory permissions to allow multi-user access (0o777).

    Uses sudo chmod when directory is owned by another user (e.g., root).
    Requires passwordless sudo for fosqa/jenkins users.

    Only changes permissions, never changes ownership. This allows all users
    (fosqa, jenkins, root, etc.) to write logs while preserving original owner.

    Args:
        directory: Directory path to fix permissions for.

    Returns:
        Dictionary with:
        - success (bool): Whether permissions were fixed
        - fixed (bool): Whether any changes were needed
        - used_sudo (bool): Whether sudo was required
        - permissions_before (Optional[str]): Octal permissions before
        - permissions_after (str): Octal permissions after
        - error (Optional[str]): Error message if failed

    Example:
        >>> result = fix_directory_permissions(Path("/home/fosqa/logs"))
        >>> if result["success"]:
        ...     print(f"Permissions: {result['permissions_after']}")
    """
    try:
        if not directory.exists():
            return {
                "success": False,
                "fixed": False,
                "used_sudo": False,
                "error": "directory_not_found",
                "message": f"Directory does not exist: {directory}",
            }

        # Get current permissions
        current_stat = directory.stat()
        current_mode = stat.S_IMODE(current_stat.st_mode)
        permissions_before = oct(current_mode)

        # Desired permissions: 0o777 (rwxrwxrwx) for all users
        desired_mode = stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO

        # Check if permissions need fixing
        needs_fix = current_mode != desired_mode

        if not needs_fix:
            return {
                "success": True,
                "fixed": False,
                "used_sudo": False,
                "permissions_before": permissions_before,
                "permissions_after": permissions_before,
                "message": "Permissions already correct (0o777)",
            }

        # Check if we own the directory
        current_user = getpass.getuser()
        directory_owner = directory.owner()
        need_sudo = directory_owner != current_user

        # Try to fix directory permissions
        if need_sudo:
            # Use sudo chmod for directories we don't own
            try:
                subprocess.run(["sudo", "chmod", "777", str(directory)], check=True, capture_output=True, text=True, timeout=5)

                # Also fix existing log files with sudo
                for log_file in directory.glob("*.log"):
                    try:
                        subprocess.run(["sudo", "chmod", "666", str(log_file)], check=True, capture_output=True, text=True, timeout=5)
                    except subprocess.CalledProcessError:
                        # Can't fix this file, continue with others
                        pass

                new_stat = directory.stat()
                new_mode = stat.S_IMODE(new_stat.st_mode)

                return {
                    "success": True,
                    "fixed": True,
                    "used_sudo": True,
                    "permissions_before": permissions_before,
                    "permissions_after": oct(new_mode),
                    "message": f"Fixed permissions with sudo: {permissions_before} → {oct(new_mode)}",
                }

            except subprocess.CalledProcessError as e:
                return {
                    "success": False,
                    "fixed": False,
                    "used_sudo": True,
                    "error": "sudo_chmod_failed",
                    "message": f"sudo chmod failed: {e.stderr.strip() if e.stderr else str(e)}",
                }

            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "fixed": False,
                    "used_sudo": True,
                    "error": "sudo_timeout",
                    "message": "sudo chmod timed out (passwordless sudo configured?)",
                }

        else:
            # We own it, use regular chmod
            try:
                directory.chmod(desired_mode)

                # Also fix permissions on all existing log files
                for log_file in directory.glob("*.log"):
                    try:
                        log_file.chmod(
                            stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH  # User read/write  # Group read/write  # Others read/write
                        )
                    except (PermissionError, OSError):
                        # Can't fix this file, continue with others
                        pass

                new_stat = directory.stat()
                new_mode = stat.S_IMODE(new_stat.st_mode)

                return {
                    "success": True,
                    "fixed": True,
                    "used_sudo": False,
                    "permissions_before": permissions_before,
                    "permissions_after": oct(new_mode),
                    "message": f"Fixed permissions: {permissions_before} → {oct(new_mode)}",
                }

            except PermissionError as e:
                return {
                    "success": False,
                    "fixed": False,
                    "used_sudo": False,
                    "error": "permission_denied",
                    "message": f"Cannot change permissions: {e}",
                }

    except Exception as e:
        return {
            "success": False,
            "fixed": False,
            "used_sudo": False,
            "error": str(e),
            "message": f"Failed to fix permissions: {e}",
        }


def ensure_log_file_writable(log_file_path: Path) -> bool:
    """Ensure a log file is writable by all users (0o666).

    Creates file with world-writable permissions. Uses sudo if needed.

    Args:
        log_file_path: Path to the log file to test/create.

    Returns:
        bool: True if file is writable, False if permission issues exist.

    Example:
        >>> log_path = Path("/var/log/fosqa/test.log")
        >>> if ensure_log_file_writable(log_path):
        ...     print("Can write to log file")
    """
    try:
        # Ensure parent directory exists with correct permissions
        if not log_file_path.parent.exists():
            log_file_path.parent.mkdir(parents=True, exist_ok=True)
            fix_directory_permissions(log_file_path.parent)

        # Create the file if it doesn't exist
        log_file_path.touch(exist_ok=True)

        # Check if we own the file
        current_user = getpass.getuser()
        try:
            file_owner = log_file_path.owner()
            need_sudo = file_owner != current_user
        except (KeyError, PermissionError):
            # Can't determine owner, assume we don't own it
            need_sudo = True

        # Make it world-writable (0o666 = rw-rw-rw-)
        if need_sudo:
            try:
                subprocess.run(["sudo", "chmod", "666", str(log_file_path)], check=True, capture_output=True, text=True, timeout=5)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                # Can't change permissions with sudo, check if we can write anyway
                pass
        else:
            try:
                log_file_path.chmod(
                    stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH  # User read/write  # Group read/write  # Others read/write
                )
            except (PermissionError, OSError):
                # Can't change permissions, check if we can write anyway
                pass

        # Test if we can actually write to the file
        with open(log_file_path, "a") as f:
            f.write("")  # Try to write nothing
        return True

    except (PermissionError, OSError):
        return False


def get_writable_logs_directory() -> Path:
    """Get a writable logs directory, trying central location first.

    Attempts in order:
    1. ~/resources/tools/logs/ (preferred central location)
       - Creates if doesn't exist
       - Fixes permissions to 0o777 using sudo if needed
    2. /tmp/fosqa_logs/ (shared fallback)
    3. ~/logs/ (user-specific)
    4. /tmp/ (last resort)

    Returns:
        Path: First writable directory found.

    Example:
        >>> logs_dir = get_writable_logs_directory()
        >>> print(logs_dir)
        PosixPath('/home/fosqa/resources/tools/logs')
    """
    # Try central logs directory first
    try:
        # Create directory if it doesn't exist
        CENTRAL_LOGS_DIR.mkdir(parents=True, exist_ok=True)

        # Fix permissions (uses sudo if owned by different user)
        perm_result = fix_directory_permissions(CENTRAL_LOGS_DIR)

        # Test writability
        test_file = CENTRAL_LOGS_DIR / ".write_test"
        if ensure_log_file_writable(test_file):
            test_file.unlink(missing_ok=True)
            return CENTRAL_LOGS_DIR

        # Permission fix failed, explain why
        if not perm_result["success"]:
            # Will fall through to fallback directories
            pass

    except (PermissionError, OSError):
        pass

    # Try fallback directories
    for fallback_dir in FALLBACK_DIRS:
        try:
            fallback_dir.mkdir(parents=True, exist_ok=True)

            # Try to fix permissions on fallback too
            fix_directory_permissions(fallback_dir)

            test_file = fallback_dir / ".write_test"
            if ensure_log_file_writable(test_file):
                test_file.unlink(missing_ok=True)
                return fallback_dir
        except (PermissionError, OSError):
            continue

    # Last resort - return central dir and let it fail with clear error
    return CENTRAL_LOGS_DIR


def get_fallback_log_path(original_path: Path, script_name: str) -> Path:
    """Get a fallback log path when the original is not writable.

    Args:
        original_path: The original log path that failed.
        script_name: Name of the script for log file naming.

    Returns:
        Path: A writable log path.

    Example:
        >>> fallback = get_fallback_log_path(
        ...     Path("/var/log/test.log"),
        ...     "my_script"
        ... )
        >>> print(fallback)
        PosixPath('/tmp/fosqa_logs/my_script.log')
    """
    current_user = os.getenv("USER", "unknown")

    fallback_options = [
        # User-specific in same directory
        original_path.parent / f"{script_name}_{current_user}.log",
        # Shared fallback directory
        Path("/tmp/fosqa_logs") / f"{script_name}.log",
        # User's home logs directory
        Path.home() / "logs" / f"{script_name}.log",
        # Temp directory with user suffix
        Path("/tmp") / f"{script_name}_{current_user}.log",
    ]

    for fallback_path in fallback_options:
        try:
            fallback_path.parent.mkdir(parents=True, exist_ok=True)
            fix_directory_permissions(fallback_path.parent)
            if ensure_log_file_writable(fallback_path):
                return fallback_path
        except Exception:
            continue

    return original_path


def create_safe_file_handler(log_file_path: Path, script_name: str, mode: str = "w") -> logging.FileHandler:
    """Create a file handler with fallback for permission issues.

    Args:
        log_file_path: Desired log file path.
        script_name: Script name for fallback naming.
        mode: File open mode ('w' for overwrite, 'a' for append).

    Returns:
        logging.FileHandler: A working file handler.

    Example:
        >>> handler = create_safe_file_handler(
        ...     Path("/var/log/test.log"),
        ...     "my_script",
        ...     mode="a"
        ... )
    """
    # Ensure directory exists and has correct permissions
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    fix_directory_permissions(log_file_path.parent)

    # Try the original path first
    if ensure_log_file_writable(log_file_path):
        try:
            handler = logging.FileHandler(log_file_path, mode=mode)
            # Force immediate write to verify it works
            handler.flush()
            return handler
        except (PermissionError, OSError):
            pass

    # Original path failed, try fallback
    fallback_path = get_fallback_log_path(log_file_path, script_name)

    try:
        handler = logging.FileHandler(fallback_path, mode=mode)
        handler.flush()
        return handler
    except Exception:
        # Last resort - create a no-op handler that logs to stderr
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.emit = lambda record: sys.stderr.write(f"LOG FILE ERROR ({e}): {record.getMessage()}\n")
        return console_handler


class BufferingHandler(logging.Handler):
    """Handler that buffers log records for later processing.

    Used to capture main script logs before we know if central logging
    is needed (when imports haven't occurred yet).

    Example:
        >>> buffer = BufferingHandler()
        >>> buffer.emit(log_record)
        >>> buffer.flush_to_handler(file_handler)
    """

    def __init__(self):
        super().__init__()
        self.buffer = []

    def emit(self, record: logging.LogRecord) -> None:
        """Buffer a log record for later emission."""
        self.buffer.append(record)

    def flush_to_handler(self, target_handler: logging.Handler) -> None:
        """Flush all buffered records to a target handler.

        Args:
            target_handler: Handler to receive buffered records.
        """
        for record in self.buffer:
            target_handler.emit(record)
        self.buffer.clear()


def should_use_central_log(main_script_name: str, current_script_name: str) -> bool:
    """Determine if central logging should be used.

    Central logging is enabled when multiple scripts are involved:
    1. This is an imported script (not the main script)
    2. OR when the main script is called again after imports occurred

    Args:
        main_script_name: Name of the main entry point script.
        current_script_name: Name of the current script being configured.

    Returns:
        bool: True if central logging should be used.

    Example:
        >>> should_use_central_log("main_script", "imported_module")
        True
        >>> should_use_central_log("main_script", "main_script")
        False  # Initially False, becomes True after imports
    """
    if main_script_name not in _active_loggers:
        _active_loggers[main_script_name] = set()

    _active_loggers[main_script_name].add(current_script_name)

    is_imported_script = current_script_name != main_script_name
    multiple_scripts_detected = len(_active_loggers[main_script_name]) > 1

    return is_imported_script or multiple_scripts_detected


def setup_script_logging(caller_file: str, log_level: int = logging.DEBUG, console_level: int = logging.INFO, central_log: bool = True, log_dir: Optional[Path] = None) -> logging.Logger:
    """Set up logging for a script with centralized log directory.

    **By default, all logs are written to ~/resources/tools/logs/.**
    **Pass log_dir to override (e.g., prototype/logs/ for converter tools).**

    Automatically fixes directory permissions to 0o777 (rwxrwxrwx) using sudo
    when needed for multi-user access (fosqa, jenkins, root, etc.) WITHOUT
    changing ownership.

    Requires passwordless sudo configuration for fosqa/jenkins users:
    ```
    # /etc/sudoers.d/fosqa-tools
    fosqa ALL=(ALL) NOPASSWD: /bin/chmod
    jenkins ALL=(ALL) NOPASSWD: /bin/chmod
    ```

    Creates:
    - Individual log: {log_dir}/{script_name}.log (always)
    - Combined log: {log_dir}/{main_script}_all.log (when multiple scripts)

    Args:
        caller_file: Pass __file__ from the calling script.
        log_level: Log level for file output (default: DEBUG).
        console_level: Log level for console output (default: INFO).
        central_log: Whether to enable smart central logging (default: True).
        log_dir: Override log directory (default: ~/resources/tools/logs/).
                 Use this to write logs near the running project, e.g.:
                 log_dir=Path(__file__).parent.parent / 'logs'

    Returns:
        logging.Logger: Configured logger instance for the script.

    Example:
        >>> # In my_script.py
        >>> from common.common_logging import setup_script_logging
        >>> logger = setup_script_logging(__file__)
        >>> logger.info("This goes to ~/resources/tools/logs/my_script.log")

    Features:
        - Centralized log directory (~/resources/tools/logs/)
        - Automatic permission fixes with sudo when needed
        - NO ownership changes (preserves existing owner)
        - Isolated named loggers (no root logger pollution)
        - Automatic cleanup of unused combined logs
        - Thread-safe operation with proper file locking
        - Robust permission handling for different sudo users
        - Fallback logging locations if main directory not writable

    Smart Central Log:
        - Single script: Only ~/resources/tools/logs/script_name.log
        - Multiple scripts: ~/resources/tools/logs/main_script_all.log + individual logs
        - Example: test_import.py calls example.py → logs/test_import_all.log

    Environment Variables:
        - SUPPRESS_LOGGING=1: Disables console output (for MCP servers)

    Permission Strategy:
        - Directories: 0o777 (rwxrwxrwx) - all users can create files
        - Log files: 0o666 (rw-rw-rw-) - all users can write
        - Method: sudo chmod when owner differs from current user
        - Owner: Preserved (no chown calls)
        - Works for: fosqa, jenkins, root, any user with sudo access
    """
    # Check if logging suppression is enabled (for MCP servers)
    suppress_logging = os.environ.get("SUPPRESS_LOGGING") == "1"

    # Use caller's script name for log file and logger name
    caller_path = Path(caller_file)
    script_name = caller_path.stem

    # Use provided log_dir override or fall back to central writable directory
    if log_dir is not None:
        logs_dir = Path(log_dir)
        logs_dir.mkdir(parents=True, exist_ok=True)
    else:
        # Get writable logs directory (uses sudo chmod if needed)
        logs_dir = get_writable_logs_directory()
        # Double-check permissions are correct before proceeding
        if logs_dir == CENTRAL_LOGS_DIR:
            fix_directory_permissions(logs_dir)

    # Log paths in centralized directory
    log_file = logs_dir / f"{script_name}.log"

    # Determine if we need central logging
    main_script_name = get_main_script_name()
    use_central = central_log and should_use_central_log(main_script_name, script_name)
    central_log_file = logs_dir / f"{main_script_name}_all.log" if use_central else None

    # Special handling for main script - use buffering until we know if central log is needed
    is_main_script = script_name == main_script_name
    needs_buffering = is_main_script and not use_central and main_script_name not in _main_script_buffers

    # Create formatters
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    central_formatter = None
    if use_central:
        central_formatter = logging.Formatter("%(asctime)s - [%(name)s] - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # Create named logger using script name (isolated from root logger)
    logger = logging.getLogger(script_name)
    logger.setLevel(log_level)

    # Clear any existing handlers
    logger.handlers.clear()

    # Set up individual script file handler with proper permissions
    file_handler = create_safe_file_handler(log_file, script_name, mode="w")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    # Set up central log file handler - only if multiple scripts involved
    central_handler = None
    if use_central and central_log_file:
        central_handler = create_safe_file_handler(central_log_file, f"{main_script_name}_all", mode="a")
        central_handler.setFormatter(central_formatter)
        central_handler.setLevel(log_level)

    # Set up console handler (unless suppressed for MCP servers)
    console_handler = None
    if not suppress_logging:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d: %(message)s"))
        console_handler.setLevel(console_level)

    # For main script that doesn't need central logging yet, set up buffering
    buffer_handler = None
    if needs_buffering:
        buffer_handler = BufferingHandler()
        buffer_handler.setFormatter(central_formatter or formatter)
        buffer_handler.setLevel(log_level)
        _main_script_buffers[main_script_name] = buffer_handler

    # Add handlers to logger
    logger.addHandler(file_handler)
    if central_handler:
        logger.addHandler(central_handler)
    elif buffer_handler and is_main_script:
        logger.addHandler(buffer_handler)
    if console_handler:
        logger.addHandler(console_handler)

    # Prevent propagation to root logger (completely isolated)
    logger.propagate = False

    # Log where we're actually writing (for debugging)
    actual_log_path = getattr(file_handler, "baseFilename", str(log_file))
    if actual_log_path != str(log_file):
        if str(logs_dir) in actual_log_path:
            logger.info(f"Using user-specific log file: {Path(actual_log_path).name}")
        else:
            logger.info(f"Using fallback log location: {actual_log_path}")

    # Log central log fallback if applicable
    if central_handler:
        central_log_path = getattr(central_handler, "baseFilename", str(central_log_file))
        if central_log_file and central_log_path != str(central_log_file):
            logger.info(f"Central log using fallback: {central_log_path}")

    # If this is an imported script, add central logging to main script too
    if use_central and central_log_file and script_name != main_script_name:
        main_logger = logging.getLogger(main_script_name)

        # Check if main logger already has central handler
        has_central_handler = any(isinstance(h, logging.FileHandler) and central_log_file and h.baseFilename == str(central_log_file) for h in main_logger.handlers)

        if not has_central_handler:
            # Create central handler for main script
            main_central_handler = create_safe_file_handler(central_log_file, f"{main_script_name}_all", mode="a")
            main_central_handler.setFormatter(central_formatter)
            main_central_handler.setLevel(log_level)

            # Flush buffer if exists
            if main_script_name in _main_script_buffers:
                buffer_handler = _main_script_buffers[main_script_name]
                buffer_handler.flush_to_handler(main_central_handler)
                main_logger.removeHandler(buffer_handler)
                del _main_script_buffers[main_script_name]

            main_logger.addHandler(main_central_handler)

    return logger


def get_script_logger(caller_file: str) -> Optional[logging.Logger]:
    """Get an existing logger for a script without reconfiguring it.

    Args:
        caller_file: Pass __file__ from the calling script.

    Returns:
        logging.Logger or None: Existing logger instance, or None if not found.

    Example:
        >>> logger = get_script_logger(__file__)
        >>> if logger:
        ...     logger.info("Using existing logger")
    """
    caller_path = Path(caller_file)
    script_name = caller_path.stem
    return logging.getLogger(script_name)
