# Autolib v3 - FortiOS Automation Testing Framework

A comprehensive automation testing framework for FortiOS devices with a custom Domain-Specific Language (DSL) for test script authoring.

**Documentation**: https://releaseqa-portal.corp.fortinet.com/static/docs/training/autolib_v3_docs/

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Testing Guidelines](#testing-guidelines)
- [Code Structure](#code-structure)
- [Contributing](#contributing)
- [Common Tasks](#common-tasks)

---

## Overview

Autolib v3 is a Python-based test automation framework designed for FortiOS device testing. It provides:

- **Custom DSL**: Domain-specific language for writing test scripts
- **Device Abstraction**: Support for FortiGate, FortiSwitch, FortiAP, and KVM devices
- **Script Compiler**: Lexer, parser, and compiler for DSL scripts
- **Test Executor**: Runtime engine for executing compiled test scripts
- **Scheduler**: Task and job management for test orchestration
- **Web Interface**: HTTP server for viewing test results
- **Plugin System**: Extensible API system for custom operations

### Key Features

- Multi-device support with automatic session management
- Variable interpolation and expression evaluation
- Control flow constructs (if/else, loops)
- Image restoration and VM deployment workflows
- Real-time test result viewing via web interface
- Comprehensive device information collection

---

## Architecture

```
autolib_v3/
├── lib/
│   ├── core/
│   │   ├── compiler/      # DSL compiler (lexer, parser, VM code generation)
│   │   ├── device/        # Device abstraction layer
│   │   ├── executor/      # Script execution engine and APIs
│   │   └── scheduler/     # Task and job scheduling
│   ├── services/          # Core services (logging, environment, web server)
│   ├── tests/             # Unit and integration tests
│   └── utilities/         # Helper functions and exceptions
├── plugins/
│   ├── apis/              # User-defined custom APIs
│   └── lib/               # Custom library extensions
├── testcase/              # Test script examples
├── outputs/               # Test execution results
└── autotest.py            # Main entry point
```

### Component Overview

1. **Compiler (`lib/core/compiler/`)**: Converts DSL scripts into executable VM code
2. **Device Layer (`lib/core/device/`)**: Abstracts device connections and operations
3. **Executor (`lib/core/executor/`)**: Executes compiled scripts with runtime APIs
4. **Scheduler (`lib/core/scheduler/`)**: Manages test jobs and task execution
5. **Services (`lib/services/`)**: Provides logging, configuration, and web server

---

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Linux/Unix environment (Ubuntu 18.04+ recommended)
- SSH access to target devices (for actual device testing)

### Installation

1. **Clone the repository**:

   ```bash
   git clone https://release.qa.gitlab.fortinet.com/fortios/autolib_v3.git
   cd autolib_v3
   ```

2. **Install dependencies**:

   ```bash
   pip3 install -r requirements.txt
   ```

3. **Verify installation**:
   ```bash
   python3 autotest.py --help
   ```

### Quick Start

Run a sample test script:

```bash
python3 autotest.py -e testcase/v760/antivirus/env.fortistack.antivirus.conf -g testcase/v760/antivirus/grp.antivirus_all.full
```

---

## Development Workflow

### Branch Strategy

- `main`: Production-ready code
- `develop`: Integration branch for features
- `feature/*`: Feature development branches
- `bugfix/*`: Bug fix branches
- `refactor/*`: Code refactoring branches

### Development Process

1. **Create a feature branch**:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the code style guidelines

3. **Write/update tests** (see [Testing Guidelines](#testing-guidelines))

4. **Run tests locally**:

   ```bash
   pytest lib/tests/ -v
   ```

5. **Check code quality**:

   ```bash
   # Run linter
   pylint lib/

   # Check formatting (optional)
   black --check lib/
   ```

6. **Commit your changes**:

   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

7. **Push and create merge request**:
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Convention

Follow conventional commit format:

- `feat:` New feature
- `fix:` Bug fix
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `docs:` Documentation changes
- `chore:` Maintenance tasks

Example:

```
feat: add support for FortiManager devices

- Implement FMG device class
- Add FMG-specific commands
- Update compiler to recognize FMG sections
```

---

## Testing Guidelines

### ⚠️ IMPORTANT: Always Run Tests

**Before committing any changes, you MUST run the test suite to ensure your changes don't break existing functionality.**

### Running Tests

#### Run all tests:

```bash
pytest lib/tests/
```

#### Run tests with coverage:

```bash
pytest lib/tests/ --cov=lib --cov-report=html --cov-report=term
```

#### Run specific test file:

```bash
pytest lib/tests/test_compiler.py -v
```

#### Run specific test:

```bash
pytest lib/tests/test_compiler.py::TestCompiler::test_compile_file_basic -v
```

#### Run tests matching pattern:

```bash
pytest lib/tests/ -k "test_device" -v
```

### Test Coverage

View the HTML coverage report:

```bash
xdg-open htmlcov/index.html  # Linux
open htmlcov/index.html       # macOS
```

**Current coverage target: 35%+**

### Writing Tests

#### Test Structure

Tests are organized by module:

- `test_compiler.py` - Compiler, lexer, parser tests
- `test_device.py` - Device abstraction tests
- `test_executor.py` - Execution engine tests
- `test_api_manager.py` - API discovery and execution
- `test_scheduler.py` - Task scheduling tests
- `test_web_server.py` - Web server tests

#### Test Example

```python
"""
Tests for new feature module.
"""
import pytest
from unittest.mock import MagicMock, patch

class TestNewFeature:
    """Test suite for NewFeature class."""

    def test_feature_initialization(self, mocker):
        """Test feature initializes correctly."""
        # Arrange
        mock_dependency = mocker.patch('module.Dependency')

        # Act
        feature = NewFeature()

        # Assert
        assert feature is not None
        mock_dependency.assert_called_once()

    def test_feature_with_fixture(self, temp_dir):
        """Test feature with temporary directory."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("content")

        # Test your feature
        assert test_file.exists()
```

#### Common Fixtures

Available in `lib/tests/conftest.py`:

- `temp_dir` - Temporary directory (auto-cleaned)
- `temp_script_file` - Temporary test script
- `sample_vm_codes` - Sample VM code objects
- `mock_device` - Mock device object
- `mock_fortigate` - Mock FortiGate device
- `mock_logger` - Mock logger
- `mock_environment` - Mock environment

#### Integration Tests

Mark integration tests that require full environment:

```python
@pytest.mark.skip(reason="Requires full environment setup")
def test_full_integration():
    """Integration test requiring real devices."""
    pass
```

### Test Requirements

Before your merge request is approved:

1. ✅ **All tests must pass** - No failing tests allowed
2. ✅ **New features must have tests** - Minimum 80% coverage for new code
3. ✅ **Bug fixes must have regression tests** - Prevent the bug from reoccurring
4. ✅ **Maintain overall coverage** - Don't decrease project coverage
5. ✅ **No skipped tests without reason** - Document why tests are skipped

---

## Code Structure

### Core Modules

#### `lib/core/compiler/`

Compiles DSL scripts into executable VM code.

**Key files**:

- `compiler.py` - Main compiler singleton
- `lexer.py` - Tokenizes script files
- `parser.py` - Builds VM code from tokens
- `syntax.py` - DSL syntax definitions
- `vm_code.py` - VM instruction representation

#### `lib/core/device/`

Device abstraction layer for all supported devices.

**Key files**:

- `device.py` - Base device abstract class
- `fortigate.py` - FortiGate implementation
- `fortiswitch.py` - FortiSwitch implementation
- `fortiap.py` - FortiAP implementation
- `kvm.py` - KVM hypervisor management
- `computer.py` - Generic SSH computer/server

#### `lib/core/executor/`

Executes compiled scripts with runtime support.

**Key files**:

- `executor.py` - Main execution engine
- `api_manager.py` - API discovery and registration
- `api/` - Built-in API implementations
  - `control_flow.py` - if/else, loops
  - `device.py` - Device operations
  - `command.py` - Command execution
  - `variable.py` - Variable management

#### `lib/core/scheduler/`

Manages test execution workflow.

**Key files**:

- `task.py` - Single script execution
- `job.py` - Complete test job orchestration
- `group_task.py` - Multiple script execution

#### `lib/services/`

Core services and utilities.

**Key files**:

- `environment.py` - Test environment configuration
- `log.py` - Logging setup and management
- `web_server/` - HTTP server for results viewing
- `output.py` - Output file management

### Plugin System

#### Creating Custom APIs

1. Create a Python file in `plugins/apis/`:

   ```python
   # plugins/apis/my_custom_api.py

   def my_custom_operation(executor, params):
       """
       Custom operation description.

       Parameters:
           param1: First parameter description
           param2: Second parameter description
       """
       param1 = params.get(0)
       param2 = params.get(1, default_value)

       # Your implementation
       result = do_something(param1, param2)

       return result
   ```

2. Use in test scripts:
   ```
   # test_script.conf
   [FGT1]
   my_custom_operation param1_value param2_value
   ```

APIs are automatically discovered and registered at runtime.

---

## Contributing

### Code Style

- Follow PEP 8 guidelines
- Line length: 120 characters max
- Use type hints where appropriate
- Document all public functions and classes

### Documentation

- Update docstrings for any modified functions
- Add comments for complex logic
- Update this README for significant changes
- Add examples for new features

### Code Review Checklist

Before submitting a merge request:

- [ ] All tests pass locally
- [ ] New tests added for new features
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No debug print statements left in code
- [ ] Commit messages follow convention
- [ ] No merge conflicts with target branch

### Pull Request Process

1. Ensure all tests pass and coverage is maintained
2. Update documentation as needed
3. Fill out the MR template completely
4. Request review from team members
5. Address review feedback promptly
6. Squash commits if requested
7. Wait for CI/CD pipeline to pass

---

## Common Tasks

### Running a Test Script

```bash
# Basic script execution
python3 autotest.py -s path/to/script.conf -e env.yaml

# With debug logging
python3 autotest.py -s script.conf -e env.yaml --debug

# List available APIs
python3 autotest.py --list-apis

# Start web server for results
python3 autotest.py --webserver --port 8080
```

### Debugging

#### Enable debug logging:

```bash
python3 autotest.py -s script.conf -e env.yaml --debug
```

#### View compiled VM code:

```bash
python3 -c "
from lib.core.compiler import Compiler
c = Compiler()
c.run('script.conf')
for code in c.retrieve_vm_codes('script.conf'):
    print(code)
"
```

#### Check device connection:

```python
from lib.core.device import FortiGate

device = FortiGate('FGT1')
device.connect()
result = device.send_command('get system status')
print(result)
```

### Building Binary

Create standalone executable:

```bash
./build_binary.sh
```

Output: `autotest` (standalone binary)

### Docker Usage

```bash
# Build Docker image
docker build -f AutolibDockerfile -t autolib:latest .

# Run tests in container
docker run -v $(pwd)/testcase:/testcase autolib:latest \
  -s /testcase/sample.conf -e /testcase/env.yaml
```

---

## Troubleshooting

### Common Issues

**Import errors after changes**:

```bash
# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

**Tests failing unexpectedly**:

```bash
# Run tests with verbose output
pytest lib/tests/ -vv --tb=short

# Run single failing test
pytest lib/tests/test_module.py::test_function -vv
```

**Coverage report not generating**:

```bash
# Install coverage plugin
pip3 install pytest-cov

# Generate report
pytest lib/tests/ --cov=lib --cov-report=html
```

---

## Additional Resources

- **Documentation Portal**: https://releaseqa-portal.corp.fortinet.com/static/docs/training/autolib_v3_docs/
- **GitLab Repository**: https://release.qa.gitlab.fortinet.com/fortios/autolib_v3
- **Issue Tracker**: Use GitLab Issues for bug reports and feature requests

---

## Version

Current version: See `version` file

## License

Proprietary - Fortinet Internal Use Only

---

## Support

For questions and support:

- Create an issue in GitLab
- Contact the automation team
- Check the internal documentation portal

---

## Acknowledgments

Developed and maintained by the FortiOS QA Automation Team.
