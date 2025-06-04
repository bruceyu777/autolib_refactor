# Change Log

## v3r10build0006

### Added

- Support to uprade binary with branch and build. [04b7f64]
- Support for upgrading binary based on the local OS version. [7c1fda4]
- Docker support for running `autotest`. [eb13286]
- Telnet and Git installation in Dockerfile. [b20cc6c]
- Timeout mechanism for `regex.search` to prevent hangs from invalid patterns. [2883284]
- New `non_strict` flag to allow script execution even with syntax errors. [2a5e738]
- Custom version tag support and binary renaming from `AutoLib` to `autotest`. [e94289c]
- Float support in `sleep` command. [c0bcdd4]
- Fallback mechanism for webserver IP and port if unset. [3b25e93]
- Support for:
  - PC access using SSH keys,
  - Special license platforms,
  - Default password for FortiStack. [c0bcdd4]

### Changed

- Refactored `build_binary` script:
  - Supports uploading support files.
  - Designed for more flexible future enhancements. [7c1fda4]
- Updated build script to include Dockerfiles in the upload path. [56099e9]
- Shortened wait times and optimized buffer handling:
  - Shortened `clear_buffer` delay,
  - Read buffer before clearing,
  - Enlarged wait timer for slow VM bootup. [838ecfd] [f37c645]
- Improved `pre_login_handling` for faster logins. [eca45dd]
- Updated summary HTML format as per QA request. [3b25e93]
- Refactored image upload logic in `build_binary` script. [32143fa]
- Refactored some function for oriole client. [04b7f64]

### Fixed

- Prompt mismatch on SSH key login (`Last login: ...`). [eb1fb32]
- Pattern matching bug with CRLF endings in line match mode. [d3a878f]
- Pattern mismatch in conditional syntax logic. [3d6de82]
- SSH pattern mismatch issue on Windows. [0cc9b83]
- Include script decoding issue during device switching. [12d0e35]
- Incorrect debug log line numbers. [c0bcdd4]
- Terminal server issues:
  - Cisco terminal server `enable` command bug,
  - Digi terminal server debugging fixes,
  - PC login issues. [cf94d32] [c0bcdd4]
