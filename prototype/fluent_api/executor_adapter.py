"""
Executor Adapter for pytest Integration

This module provides a bridge between pytest tests using FluentAPI and
AutoLib v3's existing Executor infrastructure, enabling 100% code reuse.

Design:
    pytest → FluentAPI → PytestExecutor → Executor → API Registry → API Functions
                                                    → Device Layer
                                                    → Services/Utilities

Key Components:
    - PytestScript: Minimal Script implementation for pytest (no VM codes)
    - PytestExecutor: Thin wrapper around AutoLib v3 Executor
    - Device factory: Creates real AutoLib v3 device instances

Benefits:
    - Reuses all AutoLib v3 battle-tested code
    - Access to 50+ executor APIs
    - Production-ready result management (ScriptResultManager)
    - Access to device layer, services, utilities
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add AutoLib v3 to path (so we can import lib.core.*, lib.services.*, etc.)
autolib_root = Path(__file__).parent.parent.parent
if str(autolib_root) not in sys.path:
    sys.path.insert(0, str(autolib_root))

from lib.core.executor import Executor
from lib.core.compiler.vm_code import VMCode
from lib.core.device import FortiGate, Pc, Computer
from lib.services import env, logger


class PytestScript:
    """
    Minimal Script implementation for pytest tests.
    
    Unlike DSL scripts that compile to VM codes, pytest tests directly call
    FluentAPI methods. This class provides the minimum Script interface
    required by Executor.
    """
    
    def __init__(self, test_name: str = "pytest_test", source_file: str = None):
        """
        Initialize pytest script.
        
        Args:
            test_name: Name of the pytest test (used for reporting)
            source_file: Optional path to source file (for reference)
        """
        self.source_file = source_file or f"{test_name}.py"
        self.test_name = test_name
        
        # Empty VM codes - pytest doesn't use VM execution
        self.vm_codes = []
        
        # Empty source lines - pytest source is the .py file
        self.lines = []
        
        logger.debug(f"Created PytestScript for test: {test_name}")
    
    @property
    def id(self):
        """Script ID for reporting"""
        return self.test_name
    
    def get_script_line(self, line_number: int) -> str:
        """Get source line (not used in pytest, but required by interface)"""
        # Handle None or invalid line numbers
        if line_number is None or line_number < 1:
            return f"# {self.test_name} (pytest test)"
        if line_number <= len(self.lines):
            return self.lines[line_number - 1]
        return f"# {self.test_name} line {line_number}"
    
    def update_code_to_execute(self, program_counter: int):
        """Update code to execute (not used in pytest)"""
        # Return dummy VMCode - pytest doesn't use VM execution
        return program_counter, VMCode("noop", ())
    
    def get_program_counter_limit(self) -> int:
        """Get VM code limit (always 0 for pytest)"""
        return 0
    
    def get_compiled_code_line(self, line_number: int):
        """Get compiled VM code line (not used in pytest)"""
        return VMCode("noop", ())
    
    def get_all_involved_devices(self):
        """Get devices involved in script"""
        # Devices are managed by pytest fixtures
        return set()
    
    def __str__(self):
        return f"PytestScript({self.test_name})"


class PytestExecutor:
    """
    Executor adapter for pytest tests.
    
    Wraps AutoLib v3's Executor to work with pytest's test structure.
    Provides simplified interface for FluentAPI while leveraging all
    existing executor functionality.
    
    Usage:
        executor = PytestExecutor(devices, test_name="test_205812")
        executor.switch_device("FGT_A")
        executor.execute_api("_command", "show system status")
        executor.execute_api("expect", "-e", "FortiGate", "-for", "205812")
    """
    
    def __init__(self, devices: Dict[str, Any], test_name: str = "pytest_test", 
                 need_report: bool = True):
        """
        Initialize pytest executor.
        
        Args:
            devices: Dict of device_name -> device_instance
            test_name: Name of pytest test (for reporting)
            need_report: Whether to generate test reports
        """
        # Create minimal Script object for pytest
        self.script = PytestScript(test_name)
        
        # Initialize env service (required by expect API)
        # Create minimal FosConfigParser with GLOBAL section
        import configparser
        from lib.services.env_parser import FosConfigParser
        parser = FosConfigParser()
        # Add minimal GLOBAL section to avoid "GLOBAL section not found" error
        parser.add_section("GLOBAL")
        parser.set("GLOBAL", "RETRY_EXPECT", "no")  # Disable retry for pytest
        env.user_env = parser
        
        # Create AutoLib v3 Executor
        self.executor = Executor(
            script=self.script,
            devices=devices,
            need_report=need_report
        )
        
        logger.info(f"Created PytestExecutor for test: {test_name}")
    
    def switch_device(self, device_name: str):
        """
        Switch to a different device for subsequent commands.
        
        Args:
            device_name: Name of device to switch to
            
        Returns:
            Device instance (for FluentDevice wrapping)
        """
        self.executor._switch_device([device_name])
        logger.debug(f"Switched to device: {device_name}")
        return self.executor.cur_device
    
    def execute_api(self, api_name: str, *params):
        """
        Execute an API or internal executor method.
        
        Args:
            api_name: Name of API/method to execute
            *params: API/method parameters
            
        Returns:
            API/method result
            
        Example:
            executor.execute_api("_command", "show system status")
            executor.execute_api("expect", "-e", "FortiGate", "-for", "205812")
        
        Note:
            - Internal methods (starting with _) are called directly on executor
            - Public APIs are routed through api_handler
        """
        # Internal executor methods (e.g., _command, _switch_device)
        if api_name.startswith('_'):
            method = getattr(self.executor, api_name, None)
            if method:
                return method(params)
            else:
                raise AttributeError(f"Executor has no internal method '{api_name}'")
        
        # Public APIs (e.g., expect, report) - route through API handler
        return self.executor.api_handler.execute_api(api_name, params)
    
    def get_result_manager(self):
        """
        Get result manager for assertion tracking.
        
        Returns:
            ScriptResultManager instance
        """
        return self.executor.result_manager
    
    def get_current_device(self):
        """
        Get current device.
        
        Returns:
            Current device instance or None
        """
        return self.executor.cur_device
    
    def variable_replacement(self, parameters: tuple) -> tuple:
        """
        Replace variables using executor's variable interpolation.
        
        Args:
            parameters: Tuple of parameters with potential variables
            
        Returns:
            Tuple with variables resolved
        """
        return self.executor.variable_replacement(parameters)
    
    def clear_devices_buffer(self):
        """Clear buffers for all devices"""
        self.executor.clear_devices_buffer()
    
    def report_script_result(self):
        """Generate final test report"""
        self.executor.report_script_result()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        # Clean up if needed
        pass
    
    def __repr__(self):
        return f"PytestExecutor(test={self.script.test_name}, device={self.executor.cur_device})"


def create_device_from_config(device_name: str, config: Dict[str, Any]):
    """
    Create AutoLib v3 device from configuration.
    
    Args:
        device_name: Name of device (e.g., 'FGT_A', 'PC_05')
        config: Device configuration dict from env file
        
    Returns:
        Device instance (FortiGate, Pc, or Computer)
        
    Example config:
        {
            'CONNECTION': 'telnet 0.0.0.0 11023',
            'USERNAME': 'admin',
            'PASSWORD': 'admin',
            'Model': 'FGVM'
        }
    """
    # Determine device type from name
    name_upper = device_name.upper()
    
    try:
        if 'FGT' in name_upper or name_upper.startswith('FG'):
            logger.debug(f"Creating FortiGate device: {device_name}")
            device = FortiGate(device_name)
        
        elif name_upper.startswith('PC_') or name_upper.startswith('PC-'):
            logger.debug(f"Creating PC device: {device_name}")
            device = Pc(device_name)
        
        elif 'COMPUTER' in name_upper or 'COMP' in name_upper:
            logger.debug(f"Creating Computer device: {device_name}")
            device = Computer(device_name)
        
        else:
            # Default to FortiGate for unknown types
            logger.warning(f"Unknown device type for {device_name}, defaulting to FortiGate")
            device = FortiGate(device_name)
        
        # Store device config in environment (for variable interpolation)
        if config:
            # AutoLib v3 uses env service for device configuration
            for key, value in config.items():
                env.set_var(f"{device_name}:{key}", value)
        
        return device
    
    except Exception as e:
        logger.error(f"Failed to create device {device_name}: {e}")
        raise


def create_devices_from_env(env_config: Dict[str, Dict[str, Any]], 
                            use_mock: bool = False) -> Dict[str, Any]:
    """
    Create all devices from environment configuration.
    
    Args:
        env_config: Environment configuration dict
        use_mock: If True, use mock devices (for testing)
        
    Returns:
        Dict of device_name -> device_instance
        
    Example:
        devices = create_devices_from_env({
            'FGT_A': {'CONNECTION': 'telnet ...', 'USERNAME': 'admin'},
            'PC_05': {'CONNECTION': 'ssh ...', 'PASSWORD': 'Qa123456!'}
        })
    """
    if use_mock:
        # For prototype testing, import mock device factory
        logger.info("Creating MOCK devices for testing")
        sys.path.insert(0, str(Path(__file__).parent))
        from mock_device import create_mock_device
        
        return {
            name: create_mock_device(name, config)
            for name, config in env_config.items()
        }
    
    else:
        # Create real AutoLib v3 devices
        logger.info("Creating REAL AutoLib v3 devices")
        devices = {}
        
        for name, config in env_config.items():
            try:
                device = create_device_from_config(name, config)
                devices[name] = device
                logger.info(f"Created device: {name} ({type(device).__name__})")
            except Exception as e:
                logger.error(f"Failed to create device {name}: {e}")
                # Continue with other devices
        
        return devices
