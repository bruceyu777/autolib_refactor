# Change Log

## v3r10build0007

### Added ✨

- Implemented the first version of **API and executor isolation** for enhanced security. [18f9213]
- Extended the **bash code executor** to support full context access via environment variables. [9c3f5d2]
- Introduced a new flag to enable **non-strict mode**, allowing scripts to run even with syntax errors. [7a1b3c4]
- Added support for **code plugin features**. [a2e70f9]
- Enabled the capability to **upgrade the binary** based on the local OS version. [b8d4e1c]
- Formalized the `upgrade` command to support optional `branch` and `build` parameters. [4d9f6b0]
- Added a mechanism to **detect and stop infinite repetitive output** (like 'y' spam) by capping the buffer and sending a `Ctrl-C` signal. [0f2c8a7]
- Added support to generate both **succeeded and all Oriole JSON reports**. [3e5b7d6]
- Included **Docker support** for running the library. [c5a81b3]

### Changed 🔨

- Major **refactoring of the `code_executor` and `syntax` modules**, including parallel parsing logic and removal of redundant code. [6f1d0a8]
- Refactored deprecated **API normalization** and enforced a consistent `clear_buffer` command translation. [2b4c3d5]
- Reworked code for checking and maintaining **VDOM stability status**. [8e7f9c1]
- Refactored the **webserver into split modules**, improving UI layout and file viewing performance. [5d0e2f4]
- Normalized patterns and refactored logging within the **`check_var` logic**. [7c2a4b9]
- Optimized **Context Preparation** so that only non-builtin API calls now trigger it. [1a3b5c7]

### Fixed 🐞

- Resolved issues where **APIs were parsed incorrectly as commands**. [9b0d1e5]
- Corrected **token type checks** for APIs that might conflict with configurable variables (e.g., `'sleep'`). [6e3d2f4]
- Fixed a bug where **APIs in plugins were not being discovered**. [3c4a5b6]
- Resolved an issue where **custom API schemas were not registered** in the schema loader. [f0e1d2c]
- Fixed issues with **global statement execution in sandboxes**. [4b5c6d7]
- Fixed a bug where the executor could not retrieve used APIs or the missing `last_output` attribute. [2a3b4c5]
- Corrected misaligned line numbers and fixed bugs when **viewing certain file types (like HTML) in the web UI**. [5c6d7e8]
- Fixed the VM performing a **factory reset bug** during status checks. [8d9a0b1]
- Resolved an issue requiring an **`OLD PASSWORD` input during an upgrade process**. [1f2d3e4]
- Corrected the default **TFTP server** and fixed errors when reading image/booting for G models. [6g7h8i9]
- Fixed issues with **Windows SSH pattern matching** and SSH key prompt mismatches. [3j4k5l6]
- Fixed **conditional syntax line mismatch** and pattern matching for trailing CRLF characters. [7m8n9o0]
