"""
Shared pytest fixtures for autolib test suite.
"""

# pylint: disable=redefined-outer-name  # Pytest fixtures intentionally shadow fixture names
# pylint: disable=protected-access  # Tests need to access protected members

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from lib.core.compiler.lexer import Token
from lib.core.compiler.vm_code import VMCode

# ==================== File & Directory Fixtures ====================


@pytest.fixture
def temp_dir():
    """Provide a temporary directory that's cleaned up after test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_script_file(temp_dir):
    """Create a temporary script file for testing."""
    script_file = temp_dir / "test_script.conf"
    script_file.write_text(
        """
comment: This is a test script
config system admin
    edit "admin"
        set password "test123"
    next
end
"""
    )
    yield script_file


@pytest.fixture
def temp_group_file(temp_dir):
    """Create a temporary group file for testing."""
    # Create individual script files
    script1 = temp_dir / "script1.conf"
    script1.write_text(
        "comment: Script 1\nconfig system global\n    set hostname FGT1\nend\n"
    )

    script2 = temp_dir / "script2.conf"
    script2.write_text(
        "comment: Script 2\nconfig system global\n    set alias FGT2\nend\n"
    )

    # Create group file
    group_file = temp_dir / "group.txt"
    group_file.write_text(
        f"""
<group>
<device> FGT1 <device>
<script> {script1} <script>
<script> {script2} <script>
<group>
"""
    )
    yield group_file, [script1, script2]


# ==================== Device Mocking Fixtures ====================


@pytest.fixture
def mock_device():
    """Mock a generic Device object."""
    device = MagicMock()
    device.name = "MockDevice"
    device.ip = "192.168.1.1"
    device.port = 22
    device.username = "admin"
    device.password = "password"
    device.device_type = "fortigate"
    device.is_connected.return_value = True
    device.send_command.return_value = "Command executed successfully"
    device.expect.return_value = 0
    device.search.return_value = True
    device.get_device_info.return_value = {
        "hostname": "FortiGate-VM64",
        "version": "v7.4.1",
        "serial": "FGVM0123456789",
    }
    return device


@pytest.fixture
def mock_fortigate(mock_device):
    """Mock a FortiGate device."""
    mock_device.device_type = "fortigate"
    mock_device.get_parsed_system_status.return_value = {
        "Version": "FortiGate-VM64 v7.4.1,build2448,230811",
        "Serial-Number": "FGVM0123456789",
        "Hostname": "FortiGate-VM64",
        "Operation Mode": "NAT",
    }
    return mock_device


@pytest.fixture
def mock_connection():
    """Mock a pexpect connection object."""
    conn = MagicMock()
    conn.before = b"Command output"
    conn.after = b"# "
    conn.expect.return_value = 0
    conn.send.return_value = None
    conn.sendline.return_value = None
    conn.isalive.return_value = True
    return conn


# ==================== Compiler Fixtures ====================


@pytest.fixture
def sample_tokens():
    """Sample token list for testing parser."""
    return [
        Token("comment", "This is a test", 1),
        Token("command", "config system admin", 2),
        Token("command", 'edit "admin"', 3),
        Token("command", 'set password "test123"', 4),
        Token("command", "next", 5),
        Token("command", "end", 6),
    ]


@pytest.fixture
def sample_vm_codes():
    """Sample VMCode objects for testing executor."""
    return [
        VMCode(1, "comment", ["This is a test"]),
        VMCode(2, "command", ["config system admin"]),
        VMCode(3, "command", ['edit "admin"']),
        VMCode(4, "command", ['set password "test123"']),
        VMCode(5, "command", ["next"]),
        VMCode(6, "command", ["end"]),
    ]


# ==================== Environment Fixtures ====================


@pytest.fixture
def mock_environment(mocker):
    """Mock Environment service."""
    env = MagicMock()
    env.variables = {}
    env.get_var = Mock(side_effect=env.variables.get)

    def add_var_impl(key, val):
        env.variables.update({key: val})

    env.add_var = Mock(side_effect=add_var_impl)
    env.get_dev_cfg = Mock(
        return_value={
            "ip": "192.168.1.1",
            "port": 22,
            "username": "admin",
            "password": "password",
            "device_type": "fortigate",
        }
    )

    # Patch the singleton
    mocker.patch("lib.services.environment.env", env)
    return env


@pytest.fixture
def mock_logger(mocker):
    """Mock Logger service."""
    logger_mock = MagicMock()
    logger_mock.in_debug_mode = False
    logger_mock.info = MagicMock()
    logger_mock.warning = MagicMock()
    logger_mock.debug = MagicMock()
    # Patch at the import location
    mocker.patch("lib.core.compiler.compiler.logger", logger_mock)
    return logger_mock


@pytest.fixture
def mock_summary(mocker):
    """Mock Summary service."""
    summary = MagicMock()
    summary.register_testcase.return_value = None
    summary.save_result.return_value = None
    # Patch at the module level, not the attribute
    mocker.patch("lib.services.summary", summary)
    return summary


# ==================== Executor Fixtures ====================


@pytest.fixture
def mock_executor():
    """Mock Executor with basic setup."""
    executor = MagicMock()
    executor.env = MagicMock()
    executor.logger = MagicMock()
    executor.summary = MagicMock()
    executor.current_device = None
    executor.variables = {}
    executor.pc = 0
    executor.if_stack = []
    executor._switch_device = MagicMock()
    executor._command = MagicMock()
    executor.jump_forward = MagicMock()
    executor.jump_backward = MagicMock()
    executor.execute = MagicMock()

    return executor


# ==================== Device Output Fixtures ====================


@pytest.fixture
def fortigate_system_status():
    """Sample FortiGate 'get system status' output."""
    return """Version: FortiGate-VM64 v7.4.1,build2448,230811 (interim)
Security Level: 1
Firmware Signature: certified
Virus-DB: 1.00000(2018-04-09 18:07)
IPS-DB: 6.00741(2015-12-01 02:30)
Serial-Number: FGVM0123456789
Hostname: FortiGate-VM64
Operation Mode: NAT
Current virtual domain: root
Max number of virtual domains: 10
Virtual domains status: 1 in NAT mode, 0 in TP mode
Virtual domain configuration: enable
FIPS-CC mode: disable
Current HA mode: standalone
System time: Mon Nov 01 10:00:00 2025
"""


@pytest.fixture
def fortigate_autoupdate_versions():
    """Sample FortiGate 'diag autoupdate versions' output."""
    return """AV Engine
---------
Version: 7.00018 signed
Contract Expiry Date: Tue Mar 14 2026

Virus Definitions
---------
Version: 1.00000 signed
Contract Expiry Date: Tue Mar 14 2026

IPS Attack Engine
---------
Version: 7.00510
Contract Expiry Date: Tue Mar 14 2026
"""


# ==================== Web Server Fixtures ====================


@pytest.fixture
def mock_http_request():
    """Mock HTTP request object."""
    request = MagicMock()
    request.path = "/"
    request.headers = {"Host": "localhost:8000"}
    request.client_address = ("127.0.0.1", 12345)
    return request


@pytest.fixture
def sample_log_file(temp_dir):
    """Create a sample log file for web server testing."""
    log_file = temp_dir / "test.log"
    log_content = "\n".join([f"Log line {i}" for i in range(1, 101)])
    log_file.write_text(log_content)
    return log_file


# ==================== API Discovery Fixtures ====================


@pytest.fixture
def mock_api_module(temp_dir):
    """Create a mock API module file."""
    api_file = temp_dir / "test_api.py"
    api_file.write_text(
        '''
"""Test API module."""

def test_function(param1, param2):
    """A test API function."""
    return param1 + param2

def _private_function():
    """This should not be discovered."""
    pass

class TestClass:
    """This should not be discovered as API."""
    pass
'''
    )
    return api_file


# ==================== Process Mocking Fixtures ====================


@pytest.fixture
def mock_subprocess(mocker):
    """Mock subprocess operations."""
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "Command output"
    mock_proc.stderr = ""

    mock_run = mocker.patch("subprocess.run", return_value=mock_proc)
    mock_popen = mocker.patch("subprocess.Popen", return_value=mock_proc)

    return {"run": mock_run, "popen": mock_popen, "process": mock_proc}


@pytest.fixture
def mock_os_fork(mocker):
    """Mock os.fork for daemon process testing."""
    # Return 0 to simulate child process
    return mocker.patch("os.fork", return_value=0)


# ==================== File System Mocking ====================


@pytest.fixture
def mock_file_operations(mocker):
    """Mock common file operations."""
    mocks = {
        "open": mocker.patch("builtins.open", mocker.mock_open(read_data="test data")),
        "exists": mocker.patch("os.path.exists", return_value=True),
        "isfile": mocker.patch("os.path.isfile", return_value=True),
        "isdir": mocker.patch("os.path.isdir", return_value=False),
    }
    return mocks


# ==================== Network Mocking ====================


@pytest.fixture
def mock_socket(mocker):
    """Mock socket operations."""
    mock_sock = MagicMock()
    mock_sock.connect.return_value = None
    mock_sock.send.return_value = 100
    mock_sock.recv.return_value = b"Response"
    mock_sock.close.return_value = None

    mocker.patch("socket.socket", return_value=mock_sock)
    return mock_sock


# ==================== Schema Fixtures ====================


@pytest.fixture
def mock_schema(mocker):
    """Mock ScriptSyntax schema."""
    schema = MagicMock()
    schema.get_token_syntax_definition.return_value = {
        "operation": "command",
        "patterns": [r"^config\s+(.+)$"],
    }
    schema.is_valid_command.return_value = True

    mocker.patch("lib.core.compiler.syntax.script_syntax", schema)
    return schema


# ==================== Code Execution Fixtures ====================


@pytest.fixture
def sample_python_code():
    """Sample Python code for testing."""
    return "x = 10\ny = 20\nreturn x + y"


@pytest.fixture
def sample_bash_code():
    """Sample Bash code for testing."""
    return "echo 'Hello World'"


@pytest.fixture
def code_execution_context(mock_device):
    """Context dictionary for code execution."""
    return {
        "last_output": "Sample device output",
        "device": mock_device,
        "devices": {"DEV1": mock_device},
        "variables": {"var1": "value1", "var2": "value2"},
        "config": {},
        "get_variable": lambda x: "value1",
        "set_variable": lambda x, y: None,
        "workspace": "/workspace",
        "logger": MagicMock(),
    }


@pytest.fixture
def temp_code_file(temp_dir):
    """Create a temporary code file for testing.

    Usage:
        filepath = temp_code_file("script.py", "print('Hello')")
    """

    def _create_file(filename, content):
        filepath = temp_dir / filename
        filepath.write_text(content)
        return filepath

    return _create_file


@pytest.fixture
def temp_python_file(temp_dir):
    """Create a temporary Python file with sample code."""
    python_file = temp_dir / "sample_script.py"
    python_file.write_text(
        """
# Sample Python script
def process_data(data):
    '''Process input data.'''
    return data.upper()

# Default execution
result = process_data('hello')
result
"""
    )
    return python_file


@pytest.fixture
def temp_bash_file(temp_dir):
    """Create a temporary Bash file with sample code."""
    bash_file = temp_dir / "sample_script.sh"
    bash_file.write_text(
        """#!/bin/bash
# Sample Bash script
echo "Executing bash script"
echo "Current directory: $(pwd)"
"""
    )
    return bash_file
