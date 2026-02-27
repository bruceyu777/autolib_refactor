"""
Mock device for prototype testing
Simulates FortiGate/PC behavior without real connections
"""

import logging
import re


class MockDevice:
    """Mock device for testing transpiler output"""
    
    def __init__(self, name: str, config: dict = None):
        self.name = name
        self.config = config or {}
        self.connected = False
        self.logger = logging.getLogger(__name__)
        self.command_history = []
        
        # Simulated state
        self.current_vdom = "root"
        self.custom_signatures = {}
        self.backup_files = {}  # Filename -> content
    
    def connect(self):
        """Simulate connection"""
        self.logger.info(f"[{self.name}] Connecting...")
        self.connected = True
    
    def disconnect(self):
        """Simulate disconnection"""
        self.logger.info(f"[{self.name}] Disconnecting...")
        self.connected = False
    
    def _parse_config_block(self, command: str):
        """Parse multi-line config block and extract signatures"""
        if "config ips custom" not in command:
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
    
    def execute(self, command: str) -> str:
        """Simulate command execution"""
        self.logger.debug(f"[{self.name}] Execute: {command[:100]}...")
        self.command_history.append(command)
        
        # Handle multi-line config blocks
        if '\n' in command:
            # Multi-line command - parse it
            if "config ips custom" in command:
                self._parse_config_block(command)
                return "# IPS custom signatures configured"
            
            elif "config global" in command and "exec reboot" in command:
                self.logger.warning(f"[{self.name}] REBOOT SIMULATED (signatures persist)")
                return "# Device rebooting..."
            
            elif "config vdom" in command:
                self.current_vdom = "vd1"
                return "# VDOM configuration"
        
        # Single-line commands
        command = command.strip()
        
        if command.startswith("comment"):
            return ""
        
        elif command == "config vdom":
            return ""
        
        elif command.startswith("edit vd1") or command.startswith("edit \"vd1\""):
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
        
        elif command.startswith("cmp "):
            # Compare two files
            parts = command.split()
            if len(parts) >= 3:
                file1 = parts[1].split('/')[-1]  # Get filename from path
                file2 = parts[2].split('/')[-1]
                
                # Check if files exist and compare
                content1 = self.backup_files.get(file1, "")
                content2 = self.backup_files.get(file2, "")
                
                if content1 == content2:
                    # Files identical - no output
                    return ""
                else:
                    # Files differ
                    return f"{parts[1]} {parts[2]} differ"
            return ""
        
        elif command.startswith("rm -f"):
            # Remove file
            parts = command.split()
            if len(parts) >= 3:
                filename = parts[2].split('/')[-1]
                if filename in self.backup_files:
                    del self.backup_files[filename]
                    self.logger.info(f"[{self.name}] Removed {filename}")
            return ""
        
        elif command.startswith("sleep"):
            return ""
        
        elif command.startswith("keep_running"):
            return ""
        
        elif command.startswith("report"):
            qaid = command.split()[1]
            self.logger.info(f"[{self.name}] REPORT QAID {qaid}")
            return f"# QAID {qaid} reported"
        
        elif command.startswith("config global"):
            return ""
        
        elif command.startswith("exec reboot") or command.startswith("reboot"):
            self.logger.warning(f"[{self.name}] REBOOT SIMULATED")
            return ""
        
        elif not command or command.startswith("#"):
            return ""
        
        else:
            # Unknown command
            return f"# Command executed: {command}"
    
    def get_history(self):
        """Get command history for debugging"""
        return self.command_history

