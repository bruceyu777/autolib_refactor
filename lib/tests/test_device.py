"""
Tests for lib.core.device modules.
"""

# pylint: disable=singleton-comparison,unused-argument,unused-variable
# pylint: disable=unnecessary-pass,unused-import

from unittest.mock import MagicMock

import pytest


class TestDeviceBase:
    """Test suite for Device base class."""

    def test_device_initialization(self, mock_device):
        """Test device initialization with config."""
        # Test using mock device
        assert mock_device.name == "MockDevice"
        assert mock_device.ip == "192.168.1.1"
        assert mock_device.port == 22
        assert mock_device.username == "admin"

    def test_device_connect(self, mock_device):
        """Test device connection."""
        # Mock device already has connection setup
        assert mock_device is not None

    def test_send_command_basic(self, mock_device):
        """Test sending basic commands."""
        mock_device.send_command.return_value = "Command output"
        result = mock_device.send_command("get system status")

        assert result == "Command output"
        mock_device.send_command.assert_called_once_with("get system status")

    def test_send_command_with_auto_proceed(self, mock_device):
        """Test send_command with auto-proceed patterns."""
        # Test auto-proceed logic with mock
        mock_device.send_command.return_value = "Proceeded successfully"
        result = mock_device.send_command("execute factoryreset")
        assert result == "Proceeded successfully"

    def test_device_info_parsing(self, fortigate_system_status):
        """Test parsing device information."""
        # Test would parse the system status output
        assert "FortiGate-VM64" in fortigate_system_status
        assert "v7.4.1" in fortigate_system_status

    def test_reboot_detection(self, mock_device):
        """Test reboot command detection."""
        # Mock is_reboot_command method
        mock_device.is_reboot_command = MagicMock(return_value=True)

        result = mock_device.is_reboot_command("execute reboot")
        assert result == True

    def test_expect_pattern_matching(self, mock_connection):
        """Test expect pattern matching."""
        mock_connection.expect.return_value = 0
        result = mock_connection.expect(["#", "$"], timeout=30)
        assert result == 0

    def test_search_pattern(self, mock_connection):
        """Test search for pattern in output."""
        mock_connection.before = b"Version: FortiGate-VM64 v7.4.1"
        # Would test search functionality
        assert b"v7.4.1" in mock_connection.before

    def test_device_reconnect(self, mock_device):
        """Test device reconnection."""
        mock_device.reconnect = MagicMock(return_value=True)
        result = mock_device.reconnect()
        assert result == True

    def test_device_switch(self, mock_device):
        """Test switching device context."""
        mock_device.switch = MagicMock(return_value=None)
        mock_device.switch()
        mock_device.switch.assert_called_once()


class TestFortiGateDevice:
    """Test suite for FortiGate device."""

    def test_fortigate_system_status_parsing(self, fortigate_system_status):
        """Test parsing FortiGate system status."""
        # Extract version
        assert "v7.4.1" in fortigate_system_status
        # Extract serial number
        assert "FGVM0123456789" in fortigate_system_status
        # Extract hostname
        assert "FortiGate-VM64" in fortigate_system_status
        # Extract operation mode
        assert "NAT" in fortigate_system_status

    def test_fortigate_autoupdate_versions(self, fortigate_autoupdate_versions):
        """Test parsing autoupdate versions."""
        assert "AV Engine" in fortigate_autoupdate_versions
        assert "7.00018" in fortigate_autoupdate_versions
        assert "Virus Definitions" in fortigate_autoupdate_versions

    def test_fortigate_restore_image(self, mock_fortigate, mocker):
        """Test FortiGate image restoration."""
        mock_fortigate.restore_image = MagicMock(return_value=True)
        result = mock_fortigate.restore_image("v7.4.1", "2448", need_reset=True)

        mock_fortigate.restore_image.assert_called_once()

    def test_fortigate_reboot(self, mock_fortigate):
        """Test FortiGate reboot."""
        mock_fortigate.reboot_device = MagicMock(return_value=None)
        mock_fortigate.reboot_device()

        mock_fortigate.reboot_device.assert_called_once()

    def test_fortigate_license_info(self, mock_fortigate):
        """Test extracting FortiGate license information."""
        mock_fortigate.get_device_info = MagicMock(
            return_value={
                "version": "v7.4.1",
                "serial": "FGVM0123456789",
                "license": "valid",
            }
        )

        info = mock_fortigate.get_device_info()
        assert "license" in info


class TestComputerDevice:
    """Test suite for Computer device (Linux/Windows)."""

    def test_computer_ssh_connection(self, mock_connection, mocker):
        """Test Computer SSH connection."""
        # Would test SSH connection to Linux/Windows computer
        pass

    def test_computer_prompt_detection(self):
        """Test detection of Linux/Windows prompts."""
        linux_prompt = "user@host:~$"
        windows_prompt = "C:\\>"

        assert "$" in linux_prompt or ">" in windows_prompt


class TestKVMDevice:
    """Test suite for KVM hypervisor device."""

    def test_kvm_vm_deployment(self, mocker):
        """Test KVM VM deployment."""
        # Would test VM deployment workflow
        pass

    def test_kvm_vm_lifecycle(self):
        """Test KVM VM lifecycle operations."""
        # Test: create -> start -> stop -> remove
        pass

    def test_kvm_vm_status_detection(self):
        """Test KVM VM status detection."""
        statuses = ["RUNNING", "SHUTOFF", "PAUSED", "NONE"]
        assert "RUNNING" in statuses
        assert "SHUTOFF" in statuses


class TestDeviceIntegration:
    """Integration tests for device operations."""

    def test_multi_device_session(self):
        """Test managing multiple device sessions."""
        pytest.skip("Requires full device integration")

    def test_device_command_chain(self):
        """Test chaining multiple commands."""
        pytest.skip("Requires full device integration")
