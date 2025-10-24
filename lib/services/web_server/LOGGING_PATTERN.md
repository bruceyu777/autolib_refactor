# Web Server Logging Pattern

## ⚠️ CRITICAL: Fork-Safe Logging

The web server runs as a **forked daemon process**. Logging must be configured carefully to avoid:

- **File conflicts**: Parent and child writing to same files
- **Log corruption**: Interleaved writes from multiple processes
- **Lost logs**: File handles closed in one process affecting another

## Architecture

### Parent Process (autotest)

- Uses main logger with its handlers
- Forks daemon and returns immediately
- Logs to: `outputs/.../summary/autotest.log`

### Daemon Process (web server)

1. **Closes inherited handlers** from parent
2. **Creates new log file** specific to daemon
3. Logs go to daemon file ONLY, not parent's files

## Single Logger Approach

We use **only the main logger** (`logger` from `lib.services.log`).

### How It Works

**When daemon starts** (in `server.py`):

```python
# After fork, in child process:
for handler in logger.handlers[:]:
    handler.close()
    logger.removeHandler(handler)

# Set up fresh handlers for daemon
setup_webserver_daemon_logging()
```

**What gets logged where**:

| DEBUG_LEVEL | Daemon Log File                                      | What's Logged    |
| ----------- | ---------------------------------------------------- | ---------------- |
| 0 (default) | `outputs/webserver_daemon.log`                       | ERROR level only |
| 1           | `outputs/webserver_debug_daemon_YYYYMMDD_HHMMSS.log` | INFO and above   |
| 2           | `outputs/webserver_debug_daemon_YYYYMMDD_HHMMSS.log` | DEBUG and above  |

## Coding Pattern

### ✅ CORRECT: Use logger with conditional debug details

```python
from ..log import logger
from .debug import is_debug_enabled

# Always log important events
logger.info("HTTP server started on port %s", self.port)

# Conditional debug details
if is_debug_enabled(2):
    logger.debug("HTTP server created: %s", server_address)

# Performance metrics (debug only)
if is_debug_enabled(2):
    elapsed = time.time() - start_time
    logger.debug("File read took %.3fs", elapsed)
```

### ❌ WRONG: Don't set up logging in parent process

```python
# DON'T DO THIS - parent and daemon will share file handles
setup_webserver_daemon_logging()  # Only call in daemon!
```

## When to Use Each Log Level

### logger.error() / logger.warning()

- Always logged (all debug levels)
- Daemon writes to its log file
- Example: Server crashes, file not found, permission denied

### logger.info()

- Logged when DEBUG_LEVEL >= 1
- Server lifecycle events
- API endpoint calls
- Important state changes

### logger.debug()

- Logged when DEBUG_LEVEL >= 2
- Performance metrics
- Detailed request information
- Internal state for troubleshooting

## Log File Names

**Production (DEBUG_LEVEL=0)**:

- `outputs/webserver_daemon.log` - Errors only, no timestamp (persistent file)

**Debug Mode (DEBUG_LEVEL=1 or 2)**:

- `outputs/webserver_debug_daemon_20251023_184416.log` - Timestamped per daemon start

## Setup Flow

1. **Import package**: No logging set up yet

   ```python
   from lib.services.web_server import webserver_main
   ```

2. **Call webserver_main()**: Still no logging

3. **Fork daemon**: Parent returns, child continues

4. **In daemon**:
   - Close inherited handlers
   - Call `setup_webserver_daemon_logging()`
   - Fresh log file created

## Example: What Happens During Fork

```python
# Parent process (PID 1234)
logger.handlers = [FileHandler('autotest.log'), StreamHandler(stdout)]

os.fork()

# Parent (PID 1234) - continues normally
# - Still has handlers writing to autotest.log
# - Returns immediately

# Child daemon (PID 5678) - different process
# Step 1: Close inherited handlers
for handler in logger.handlers[:]:
    handler.close()
    logger.removeHandler(handler)
# logger.handlers = []  # Now empty!

# Step 2: Add daemon-specific handler
setup_webserver_daemon_logging()
# logger.handlers = [FileHandler('webserver_daemon.log')]

# Now daemon writes to its own file, parent unchanged
```

## Debug Output Examples

**With DEBUG_LEVEL=0** (`webserver_daemon.log`):

```
2025-10-23 18:50:23 - [ERROR] - Unable to start webserver: Address already in use
2025-10-23 18:51:15 - [ERROR] - Web server crashed: Connection reset by peer
```

**With DEBUG_LEVEL=1** (`webserver_debug_daemon_20251023_185000.log`):

```
2025-10-23 18:50:00 - [INFO] - Web Server Daemon Logging Initialized (Level 1)
2025-10-23 18:50:00 - [INFO] - HTTP server started on port 8080
2025-10-23 18:50:05 - [INFO] - API tail: /var/log/test.log - lines=1000
2025-10-23 18:50:10 - [INFO] - Loading file: /home/user/file.txt
```

**With DEBUG_LEVEL=2** (`webserver_debug_daemon_20251023_185000.log`):

```
2025-10-23 18:50:00 - [INFO] - setup_webserver_daemon_logging:83 - Web Server Daemon Logging Initialized (Level 2)
2025-10-23 18:50:00 - [DEBUG] - __init__:35 - WebServer initialized: ip=0.0.0.0, port=8080
2025-10-23 18:50:00 - [DEBUG] - _create_server:44 - HTTP server created: ('0.0.0.0', 8080)
2025-10-23 18:50:05 - [DEBUG] - read_file_tail:138 - read_file_tail: /var/log/test.log - 1000 lines, time=0.025s
```

## Key Benefits

1. **Fork-Safe**: No shared file handles between parent and daemon
2. **Simple**: Only one logger to use
3. **Isolated**: Daemon logs separate from parent
4. **Clean**: No duplicate messages or corruption
5. **Flexible**: Different log levels for different needs
