"""
Mock Device Simulators for Testing

Architecture:
- MockDevice: Base class with common device operations
- MockFortiGate: FortiGate-specific command simulation
- MockPC: PC/Linux-specific command simulation

Factory function `create_mock_device()` returns appropriate type based on device name.
"""

import logging
import re
from typing import Optional, Dict


class MockDevice:
    """Base mock device with common operations"""
    
    def __init__(self, name: str, config: Optional[Dict] = None):
        self.name = name
        self.config = config or {}
        self.connected = False
        self.command_history = []
        self.logger = logging.getLogger(__name__)
    
    def connect(self):
        """Simulate device connection"""
        self.logger.info(f"[{self.name}] Connecting...")
        self.connected = True
    
    def disconnect(self):
        """Simulate device disconnection"""
        self.connected = False
    
    def switch(self, retry=0):
        """Simulate device switch (no-op for mock devices)"""
        self.logger.debug(f"[{self.name}] Switching to device (mock)")
        # Mock devices don't need connection handling
        pass
    
    def send_command(self, cmd, pattern=None, timeout=None):
        """
        Send a command and return output (AutoLib v3 interface).
        
        Args:
            cmd: Command to send
            pattern: Optional pattern to wait for
            timeout: Optional timeout in seconds
        
        Returns:
            Tuple of (status, output, match_result, cli_output)
            For mocks, we return (True, output, None, output)
        """
        output = self.execute(cmd)
        return (True, output, None, output)
    
    def expect(self, pattern, timeout=5, need_clear=True):
        """
        Expect pattern in device output (AutoLib v3 interface).
        
        Args:
            pattern: Regular expression pattern to match
            timeout: Timeout in seconds
            need_clear: Whether to clear buffer first
        
        Returns:
            Tuple of (matched, output)
            Mock implementation searches last executed command output
        """
        import re
        
        # For mock devices, we check if pattern matches the last output
        # In a real device, this would check the device buffer
        output = self._last_output if hasattr(self, '_last_output') else ""
        
        # Try regex match
        try:
            matched = bool(re.search(pattern, output))
        except re.error:
            # If pattern is not valid regex, try literal match
            matched = pattern in output
        
        self.logger.debug(f"[{self.name}] Expect pattern '{pattern[:50]}...' → {'MATCHED' if matched else 'NOT MATCHED'}")
        return (matched, output)
    
    def get_buffer(self):
        """Get current device buffer (last command output)"""
        return getattr(self, '_last_output', "")
    
    def clear_buffer(self):
        """Clear device buffer"""
        self._last_output = ""
    
    def execute(self, command: str) -> str:
        """Execute command - to be overridden by subclasses"""
        self.logger.debug(f"[{self.name}] Execute: {command[:100]}...")
        self.command_history.append(command)
        output = self._execute_command(command)
        self._last_output = output  # Store for expect()
        return output

    def reset_config(self, cmd: str) -> str:
        """Reset device configuration (mock no-op for base device).

        Args:
            cmd: Reset command (e.g., "exe factoryreset").

        Returns:
            Mock response string.
        """
        self.logger.info(f"[{self.name}] Reset config (mock): {cmd}")
        return ""
    
    def _execute_command(self, command: str) -> str:
        """Actual command execution - override in subclasses"""
        return ""


class MockFortiGate(MockDevice):
    """FortiGate device simulator with FOS command support"""
    
    def __init__(self, name: str, config: Optional[Dict] = None):
        super().__init__(name, config)
        self.custom_signatures = {}
        self.backup_files = {}
        self.current_vdom = "root"

    def reset_config(self, cmd: str = "exe factoryreset") -> str:
        """Reset FortiGate configuration in mock mode.

        Args:
            cmd: Reset command to simulate.

        Returns:
            Mock response string.
        """
        self.logger.warning(f"[{self.name}] RESET CONFIG SIMULATED: {cmd}")
        self.custom_signatures = {}
        self.backup_files = {}
        self.current_vdom = "root"
        self.command_history = []
        self._last_output = ""
        return ""
    
    def _parse_config_block(self, command: str):
        """Parse multi-line config blocks for IPS signatures"""
        if 'config ips custom' not in command:
            return
        
        # Split into lines and process edit blocks
        lines = command.split('\n')
        current_sig_name = None
        current_sig_data = []
        in_edit_block = False
        
        for line in lines:
            line = line.strip()
            
            # Match edit "name"
            if line.startswith('edit '):
                # Extract name from edit "name" or edit name
                match = re.match(r'edit\s+"(.+)"', line)
                if not match:
                    match = re.match(r'edit\s+(.+)', line)
                if match:
                    current_sig_name = match.group(1)
                    in_edit_block = True
                    current_sig_data = []
            
            # Match set signature "..."
            elif in_edit_block and line.startswith('set signature '):
                # Extract everything after 'set signature '
                sig_start = line.find('set signature ') + len('set signature ')
                sig_line = line[sig_start:].strip()
                
                # Remove leading/trailing quotes if present
                if sig_line.startswith('"') and sig_line.endswith('"'):
                    sig_line = sig_line[1:-1]
                elif sig_line.startswith('"'):
                    # Handle case where quote doesn't end on same line
                    sig_line = sig_line[1:]
                    
                current_sig_data.append(sig_line)
            
            # Continue collecting signature data if we're in a signature line
            elif in_edit_block and current_sig_data and not line.startswith('next') and not line.startswith('end'):
                # This is a continuation of the signature
                if line.endswith('"'):
                    current_sig_data.append(line[:-1])  # Remove trailing quote
                else:
                    current_sig_data.append(line)
            
            # Match next - end of current edit block
            elif line == 'next':
                if current_sig_name and current_sig_data:
                    # Join all signature data
                    sig_value = ' '.join(current_sig_data)
                    self.custom_signatures[current_sig_name] = sig_value
                    self.logger.info(f"[{self.name}] Stored signature: {current_sig_name}")
                    self.logger.debug(f"[{self.name}] Signature data: {repr(sig_value)}")
                in_edit_block = False
                current_sig_name = None
                current_sig_data = []
    
    def _execute_command(self, command: str) -> str:
        """Simulate FortiGate command execution"""
        # Handle multi-line config blocks
        if '\n' in command:
            # Parse config blocks for IPS signatures
            self._parse_config_block(command)
            
            # Check for reboot in multi-line block
            if 'reboot' in command:
                self.logger.warning(f"[{self.name}] REBOOT SIMULATED (signatures persist)")
            return ""
        
        # Single-line commands
        command = command.strip()
        
        if command.startswith("comment"):
            return ""
        
        elif command == "config vdom":
            return ""
        
        elif command.startswith("edit vd1") or command.startswith('edit "vd1"'):
            self.current_vdom = "vd1"
            return ""
        
        elif command == "show ips custom":
            # Return stored signatures in FortiGate format
            if not self.custom_signatures:
                return "config ips custom\nend\n"
            
            output = "config ips custom\n"
            for sig_name, sig_data in self.custom_signatures.items():
                output += f'    edit "{sig_name}"\n'
                output += f'        set signature "{sig_data}"\n'
                output += "    next\n"
            output += "end\n"
            return output
        
        elif command == "purge":
            self.custom_signatures = {}
            return ""
        
        elif command == "end":
            return ""
        
        elif command.startswith("exe backup ipsuserdefsig") or command.startswith("exec backup"):
            # Extract filename (e.g., FGT_A:CUSTOMSIG1)
            parts = command.split()
            if len(parts) >= 4:
                filename = parts[3]
                # Store backup content (hash of current signatures)
                content = str(sorted(self.custom_signatures.items()))
                self.backup_files[filename] = content
                self.logger.info(f"[{self.name}] Backed up to {filename}")
            return ""
        
        elif command.startswith("get system status") or command.startswith("get sys status"):
            # Return FortiGate system status with platform type
            # Determine platform from config or use default
            platform = self.config.get('Platform', 'FGVM') if self.config else 'FGVM'
            model = self.config.get('Model', 'FGVM') if self.config else 'FGVM'
            version = self.config.get('VERSION', '7.0.0') if self.config else '7.0.0'
            
            # Map FGVM/generic names to actual platform model names for realistic output
            # This allows setvar regex to extract meaningful platform types
            platform_map = {
                'FGVM': 'FortiGate-VM64',
                'FGT': 'FortiGate-501E',
                'FortiGate': 'FortiGate-501E'
            }
            
            # Use mapped name if model is generic, otherwise use model as-is
            display_model = platform_map.get(model, model)
            if display_model == model and model in platform_map:
                display_model = platform_map[model]
            
            # Return status in format that matches real device output
            # Format: "Version: <Platform> v<Version> ..."
            return f"""Version: {display_model} v{version} build0193
Firmware Signature: certified
Serial-Number: {self.name}
System time: Mon Feb 25 15:30:00 2026
"""

        elif command in {"resetFirewall", "exec factoryreset", "exe factoryreset", "factoryreset"}:
            return self.reset_config(command)
        
        elif command.startswith("diagnose"):
            return f"Diagnostic output from {self.name}"
        
        elif command.startswith("sleep"):
            return ""
        
        elif command == "keep_running 0":
            return ""
        
        else:
            # Generic response
            return f"Command OK: {command}"


class MockPC(MockDevice):
    """PC/Linux device simulator"""
    
    def __init__(self, name: str, config: Optional[Dict] = None):
        super().__init__(name, config)
        self.files = {}  # Simulated filesystem {filename: content}
    
    def _execute_command(self, command: str) -> str:
        """Simulate Linux/PC command execution"""
        command = command.strip()
        
        if command.startswith("cmp "):
            # Compare two files
            parts = command.split()
            if len(parts) >= 3:
                file1 = parts[1].split('/')[-1]  # Get filename from path
                file2 = parts[2].split('/')[-1]
                
                # Simulate file comparison
                # In real scenario, check actual file content
                # For prototype, check if filenames suggest they should match
                if file1 in self.files and file2 in self.files:
                    if self.files[file1] == self.files[file2]:
                        return ""  # Files are identical (no output)
                    else:
                        return f"{file1} {file2} differ"
                # Default: assume files are identical if both exist
                return ""
            return ""
        
        elif command.startswith("rm "):
            # Remove file
            parts = command.split()
            if len(parts) >= 2:
                filename = parts[-1].split('/')[-1]
                if filename in self.files:
                    del self.files[filename]
                self.logger.info(f"[{self.name}] Deleted file: {filename}")
            return ""
        
        elif command.startswith("ls "):
            # List files
            return "\n".join(self.files.keys())
        
        elif command.startswith("cat "):
            # Display file content
            parts = command.split()
            if len(parts) >= 2:
                filename = parts[1].split('/')[-1]
                return self.files.get(filename, f"cat: {filename}: No such file or directory")
            return ""
        
        elif command.startswith("echo "):
            # Echo command
            return command[5:]
        
        elif command.startswith("pwd"):
            return "/root"
        
        elif command.startswith("cd "):
            return ""
        
        elif command == "keep_running 0":
            return ""
        
        else:
            # Generic shell response
            cmd_name = command.split()[0] if command.split() else command
            return f"bash: {cmd_name}: command not found"


def create_mock_device(name: str, config: Optional[Dict] = None) -> MockDevice:
    """
    Factory function to create appropriate mock device based on name.
    
    Device type detection:
    - FGT_*, FGTA*, FGTB*, etc. → MockFortiGate
    - PC_*, PC-* → MockPC
    - Default → MockFortiGate
    """
    logger = logging.getLogger(__name__)
    
    if name.startswith("FGT") or "FGT" in name.upper():
        return MockFortiGate(name, config)
    elif name.startswith("PC_") or name.startswith("PC-"):
        return MockPC(name, config)
    else:
        # Default to FortiGate for unknown types
        logger.warning(f"Unknown device type for {name}, defaulting to MockFortiGate")
        return MockFortiGate(name, config)


# Backward compatibility - keep MockDevice as alias to create_mock_device
# This allows existing code using MockDevice(name, config) to work
class MockDevice_DEPRECATED(MockDevice):
    """Deprecated: Use create_mock_device() factory function instead"""
    def __new__(cls, name: str, config: Optional[Dict] = None):
        return create_mock_device(name, config)
