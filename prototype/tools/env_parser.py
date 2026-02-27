"""
Environment Configuration File Parser for AutoLib v3

Parses INI-style environment configuration files used by AutoLib v3 DSL tests.
Format: [SECTION] with KEY: VALUE pairs (colon separator, not equals).

Example:
    [GLOBAL]
    Platform: FGVM
    VERSION: trunk
    
    [PC_01]
    CONNECTION: ssh -t fosqa@10.6.30.11 sudo -s
    IP_ETH1: 10.1.100.11
    
    [FGT_A]
    Model: FGVM
    PASSWORD: admin
"""

import re
from pathlib import Path
from typing import Dict, Any, Optional


class EnvParser:
    """Parser for AutoLib v3 environment configuration files."""
    
    def __init__(self):
        self.config: Dict[str, Dict[str, str]] = {}
        self.current_section: Optional[str] = None
    
    def parse_file(self, filepath: str) -> Dict[str, Dict[str, str]]:
        """
        Parse environment configuration file.
        
        Args:
            filepath: Path to the environment configuration file
            
        Returns:
            Dictionary with structure: {section_name: {key: value}}
            
        Example:
            {
                'GLOBAL': {'Platform': 'FGVM', 'VERSION': 'trunk'},
                'PC_01': {'CONNECTION': 'ssh ...', 'IP_ETH1': '10.1.100.11'},
                'FGT_A': {'Model': 'FGVM', 'PASSWORD': 'admin'}
            }
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Environment file not found: {filepath}")
        
        self.config = {}
        self.current_section = None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                self._parse_line(line, line_num)
        
        return self.config
    
    def _parse_line(self, line: str, line_num: int) -> None:
        """Parse a single line from the configuration file."""
        # Remove trailing whitespace but preserve leading for multi-line detection
        line = line.rstrip()
        
        # Skip empty lines
        if not line or line.strip() == '':
            return
        
        # Skip comment lines (lines starting with #)
        if line.strip().startswith('#'):
            return
        
        # Check for section header: [SECTION_NAME]
        section_match = re.match(r'^\[([^\]]+)\]', line.strip())
        if section_match:
            self.current_section = section_match.group(1).strip()
            if self.current_section not in self.config:
                self.config[self.current_section] = {}
            return
        
        # Parse key-value pair: KEY: VALUE or KEY:VALUE
        if ':' in line and self.current_section:
            # Split on first colon only
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            
            # Store in current section
            self.config[self.current_section][key] = value
        
        # Ignore lines without section context or proper format
    
    def get_device_config(self, device_name: str) -> Dict[str, str]:
        """
        Get configuration for a specific device.
        
        Args:
            device_name: Name of the device (e.g., 'FGT_A', 'PC_01')
            
        Returns:
            Dictionary of device configuration
        """
        return self.config.get(device_name, {})
    
    def get_global_config(self) -> Dict[str, str]:
        """Get global configuration section."""
        return self.config.get('GLOBAL', {})
    
    def get_variable(self, device: str, variable: str) -> Optional[str]:
        """
        Get a specific variable value for a device.
        
        Args:
            device: Device name (e.g., 'FGT_A', 'PC_05')
            variable: Variable name (e.g., 'IP_ETH1', 'CUSTOMSIG1')
            
        Returns:
            Variable value or None if not found
            
        Example:
            parser.get_variable('PC_05', 'IP_ETH1')  # Returns '172.16.200.55'
            parser.get_variable('FGT_A', 'CUSTOMSIG1')  # Returns 'custom1on1801F'
        """
        device_config = self.get_device_config(device)
        return device_config.get(variable)
    
    def resolve_variable(self, var_string: str) -> Optional[str]:
        """
        Resolve a variable string in DEVICE:VARIABLE format.
        
        Args:
            var_string: Variable string like 'PC_05:IP_ETH1' or 'FGT_A:CUSTOMSIG1'
            
        Returns:
            Resolved value or None if not found
            
        Example:
            parser.resolve_variable('PC_05:IP_ETH1')  # Returns '172.16.200.55'
        """
        if ':' not in var_string:
            return None
        
        parts = var_string.split(':', 1)
        if len(parts) != 2:
            return None
        
        device, variable = parts
        return self.get_variable(device.strip(), variable.strip())
    
    def to_testbed_config(self) -> Dict[str, Dict[str, Any]]:
        """
        Convert parsed config to TestBed-compatible format.
        
        Returns:
            Dictionary suitable for TestBed(env_config=...)
            
        Example:
            {
                'FGT_A': {
                    'type': 'fortigate',
                    'hostname': 'FGT_A',
                    'connection': 'telnet 0.0.0.0 11023',
                    'username': 'admin',
                    'password': 'admin',
                    'model': 'FGVM',
                    # ... all other config variables
                },
                'PC_01': {
                    'type': 'pc',
                    'hostname': 'PC_01',
                    'connection': 'ssh -t fosqa@10.6.30.11 sudo -s',
                    'username': 'fosqa',
                    'password': 'Qa123456!',
                    # ... all other config variables
                }
            }
        """
        testbed_config = {}
        
        for section_name, section_config in self.config.items():
            # Skip GLOBAL and ORIOLE sections (not devices)
            if section_name in ['GLOBAL', 'ORIOLE']:
                continue
            
            # Determine device type from section name
            device_type = 'pc' if section_name.startswith('PC_') else 'fortigate'
            
            # Create device config with normalized keys
            device_config = {
                'type': device_type,
                'hostname': section_name,
            }
            
            # Add all configuration variables with lowercase keys
            for key, value in section_config.items():
                # Map common keys to standard names
                key_lower = key.lower()
                if key_lower == 'connection':
                    device_config['connection'] = value
                elif key_lower == 'username':
                    device_config['username'] = value
                elif key_lower == 'password':
                    device_config['password'] = value
                elif key_lower == 'model':
                    device_config['model'] = value
                else:
                    # Keep original key for all other variables
                    device_config[key] = value
            
            testbed_config[section_name] = device_config
        
        # Add global config as a special section
        if 'GLOBAL' in self.config:
            testbed_config['GLOBAL'] = self.config['GLOBAL']
        
        return testbed_config
    
    def get_all_sections(self) -> list:
        """Get list of all section names."""
        return list(self.config.keys())
    
    def get_all_devices(self) -> list:
        """Get list of all device sections (excluding GLOBAL, ORIOLE)."""
        return [s for s in self.config.keys() if s not in ['GLOBAL', 'ORIOLE']]


def parse_env_file(filepath: str) -> Dict[str, Dict[str, Any]]:
    """
    Convenience function to parse environment file.
    
    Args:
        filepath: Path to environment configuration file
        
    Returns:
        TestBed-compatible configuration dictionary
        
    Example:
        >>> config = parse_env_file('env.fortistack.ips.conf')
        >>> print(config['FGT_A']['password'])
        'admin'
    """
    parser = EnvParser()
    parser.parse_file(filepath)
    return parser.to_testbed_config()


# Example usage
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        env_file = sys.argv[1]
    else:
        env_file = '/home/fosqa/autolibv3/autolib_v3/testcase/ips/env.fortistack.ips.conf'
    
    print(f"Parsing environment file: {env_file}")
    print("=" * 80)
    
    parser = EnvParser()
    config = parser.parse_file(env_file)
    
    print(f"\nFound {len(config)} sections:")
    for section in config.keys():
        print(f"  - {section}")
    
    print("\n" + "=" * 80)
    print("GLOBAL Config:")
    print("-" * 80)
    global_config = parser.get_global_config()
    for key, value in global_config.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 80)
    print("FGT_A Config (first 10 items):")
    print("-" * 80)
    fgt_config = parser.get_device_config('FGT_A')
    for i, (key, value) in enumerate(list(fgt_config.items())[:10]):
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 80)
    print("PC_05 Config:")
    print("-" * 80)
    pc_config = parser.get_device_config('PC_05')
    for key, value in pc_config.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 80)
    print("Variable Resolution Examples:")
    print("-" * 80)
    examples = [
        'PC_05:IP_ETH1',
        'PC_05:PASSWORD',
        'FGT_A:CUSTOMSIG1',
        'FGT_A:CUSTOMSIG2',
        'FGT_A:Model',
    ]
    for var in examples:
        value = parser.resolve_variable(var)
        print(f"  {var} = {value}")
    
    print("\n" + "=" * 80)
    print("TestBed Config Format (FGT_A):")
    print("-" * 80)
    testbed_config = parser.to_testbed_config()
    fgt_testbed = testbed_config.get('FGT_A', {})
    for key, value in list(fgt_testbed.items())[:15]:
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 80)
    print(f"Total devices in testbed config: {len([k for k in testbed_config.keys() if k not in ['GLOBAL', 'ORIOLE']])}")
