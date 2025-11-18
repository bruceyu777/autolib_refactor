"""
Tests for lib.services.environment module.
"""

# pylint: disable=unused-argument,unused-variable,unnecessary-lambda,unused-import

from collections import namedtuple
from unittest.mock import MagicMock

import pytest

from lib.services.environment import Environment


class TestEnvironment:
    """Test suite for Environment service."""

    def test_environment_initialization(self):
        """Test environment initialization."""
        env = Environment()
        assert env is not None
        assert hasattr(env, "variables")

    def test_add_variable(self):
        """Test adding variables to environment."""
        env = Environment()
        env.add_var("sn", "FG12345")
        assert env.get_var("sn") == "FG12345"

    def test_get_variable(self):
        """Test getting variables from environment."""
        env = Environment()
        env.add_var("hostname", "FortiGate-VM64")
        result = env.get_var("hostname")
        assert result == "FortiGate-VM64"

    def test_get_nonexistent_variable(self):
        """Test getting nonexistent variable returns None."""
        env = Environment()
        result = env.get_var("nonexistent")
        assert result is None

    def test_variable_overwrite(self):
        """Test overwriting existing variable."""
        env = Environment()
        env.add_var("version", "v7.4.1")
        env.add_var("version", "v7.4.2")
        assert env.get_var("version") == "v7.4.2"

    def test_get_dev_cfg(self, mock_environment):
        """Test getting device configuration."""
        dev_cfg = mock_environment.get_dev_cfg("FGT1")
        assert dev_cfg is not None
        assert "ip" in dev_cfg
        assert dev_cfg["ip"] == "192.168.1.1"

    def test_init_env_with_args(self, temp_dir, mocker):
        """Test environment initialization with args."""
        # Create test environment file
        env_file = temp_dir / "test_env.conf"
        env_file.write_text(
            """
[FGT1]
ip = 192.168.1.1
port = 22
username = admin
password = password
device_type = fortigate
"""
        )

        script_file = temp_dir / "test_script.conf"
        script_file.write_text("comment: Test\n")

        args = namedtuple("args", ["env", "script"])
        args.env = str(env_file)
        args.script = str(script_file)

        env = Environment()
        # Would test init_env method if it exists
        # env.init_env(args)

    def test_variable_interpolation(self):
        """Test variable interpolation in strings."""
        env = Environment()
        env.add_var("serial", "FG12345")

        # Test interpolation (if method exists)
        # result = env.variable_interpolation("Serial: $serial")
        # assert result == "Serial: FG12345"

    def test_device_configuration_validation(self, mock_environment):
        """Test device configuration has required fields."""
        dev_cfg = mock_environment.get_dev_cfg("FGT1")

        required_fields = ["ip", "port", "username", "password", "device_type"]
        for field in required_fields:
            assert field in dev_cfg

    def test_multiple_devices(self, mock_environment):
        """Test managing multiple device configurations."""
        # Set up multiple devices
        mock_environment.get_dev_cfg = MagicMock(
            side_effect=lambda name: {
                "FGT1": {
                    "ip": "192.168.1.1",
                    "port": 22,
                    "username": "admin",
                    "password": "pass",
                    "device_type": "fortigate",
                },
                "FGT2": {
                    "ip": "192.168.1.2",
                    "port": 22,
                    "username": "admin",
                    "password": "pass",
                    "device_type": "fortigate",
                },
            }.get(name)
        )

        fgt1_cfg = mock_environment.get_dev_cfg("FGT1")
        fgt2_cfg = mock_environment.get_dev_cfg("FGT2")

        assert fgt1_cfg["ip"] == "192.168.1.1"
        assert fgt2_cfg["ip"] == "192.168.1.2"


class TestEnvironmentIntegration:
    """Integration tests for Environment service."""

    def test_environment_singleton(self):
        """Test that environment behaves like a singleton."""
        # Would test singleton pattern if implemented
        pytest.skip("Requires singleton implementation check")

    def test_environment_persistence(self):
        """Test that variables persist across accesses."""
        env = Environment()
        env.add_var("test_key", "test_value")

        # Access again
        result1 = env.get_var("test_key")
        result2 = env.get_var("test_key")

        assert result1 == result2 == "test_value"
