"""
Fluent API for Device Testing (Prototype)
Provides method chaining and readable test syntax
Supports both mock devices (for testing) and real devices (AutoLib v3)
"""

import logging
import os
from typing import Optional, Any
from contextlib import contextmanager
from functools import wraps


def resolve_command_vars(func):
    """
    Decorator to automatically resolve DEVICE:VARIABLE patterns in command strings.
    
    Resolves variables in all string arguments before method execution.
    Requires the instance to have a 'testbed' attribute with resolve_variables() method.
    
    Usage:
        @resolve_command_vars
        def execute(self, command: str):
            # command already has variables resolved
            ...
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # Only resolve if testbed is available
        if hasattr(self, 'testbed') and self.testbed:
            # Resolve variables in positional string arguments
            resolved_args = []
            for arg in args:
                if isinstance(arg, str):
                    resolved_args.append(self.testbed.resolve_variables(arg))
                else:
                    resolved_args.append(arg)
            
            # Resolve variables in keyword string arguments
            resolved_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, str):
                    resolved_kwargs[key] = self.testbed.resolve_variables(value)
                else:
                    resolved_kwargs[key] = value
            
            return func(self, *resolved_args, **resolved_kwargs)
        else:
            # No testbed, call without resolution
            return func(self, *args, **kwargs)
    
    return wrapper


class OutputAssertion:
    """Fluent assertions for command output"""
    
    def __init__(self, output: str, result_manager, device):
        self.output = output
        self.results = result_manager
        self.device = device
    
    def expect(self, pattern: str, qaid: Optional[str] = None, 
               timeout: int = 5, should_fail: bool = False):
        """Assert pattern in output"""
        found = pattern in self.output
        
        if should_fail:
            success = not found
            msg = f"Pattern '{pattern}' should NOT be in output"
        else:
            success = found
            msg = f"Pattern '{pattern}' should be in output"
        
        if qaid:
            self.results.add_qaid(qaid, success, self.output, msg)
        
        if not success:
            raise AssertionError(f"{msg}\nOutput:\n{self.output}")
        
        return self.device  # Return device for chaining


class FluentDevice:
    """Fluent API wrapper for device operations (FortiGate, PC, etc.)"""
    
    def __init__(self, device, result_manager, testbed=None):
        self.device = device
        self.results = result_manager
        self.testbed = testbed
        self._last_output = ""
        self.logger = logging.getLogger(__name__)
    
    @resolve_command_vars
    def execute(self, command: str):
        """Execute command and store output (variables auto-resolved)"""
        self.logger.info(f"Executing: {command}")
        
        # Handle both mock and real device interfaces
        if hasattr(self.device, 'execute'):
            # Mock device interface
            self._last_output = self.device.execute(command)
        elif hasattr(self.device, 'send_line_get_output'):
            # Real AutoLib v3 device interface
            self._last_output = self.device.send_line_get_output(command)
        else:
            # Fallback
            self.logger.warning(f"Unknown device interface for {self.device}")
            self._last_output = ""
            
        return OutputAssertion(self._last_output, self.results, self)
    
    @resolve_command_vars
    def config(self, config_block: str):
        """Execute configuration block (variables auto-resolved)"""
        self.logger.info(f"Configuring:\n{config_block}")
        self.device.execute(config_block)
        return self
    
    def comment(self, text: str):
        """Add comment (for logging/traceability)"""
        self.logger.info(f"# {text}")
        return self
    
    def clear_buffer(self):
        """Clear output buffer"""
        self._last_output = ""
        return self
    
    def sleep(self, seconds: int):
        """Sleep for specified seconds"""
        import time
        self.logger.info(f"Sleeping for {seconds}s...")
        time.sleep(seconds)
        return self
    
    def report(self, qaid: str):
        """Report test completion"""
        self.results.report(qaid)
        return self
    
    def keep_running(self, state: int):
        """Keep running state (compatibility)"""
        # Placeholder for AutoLib v3 compatibility
        return self
    
    # Direct access to device for raw operations
    @resolve_command_vars
    def raw_execute(self, command: str) -> str:
        """Execute command without fluent API wrapper (variables auto-resolved)"""
        return self.device.execute(command)


class ResultManager:
    """Manage QAID results for pytest"""
    
    def __init__(self):
        self.results = {}
        self.qaids = []
    
    def add_qaid(self, qaid: str, success: bool, output: str, message: str = ""):
        """Record QAID result"""
        if qaid not in self.results:
            self.results[qaid] = []
        
        self.results[qaid].append({
            'success': success,
            'output': output,
            'message': message
        })
        
        if qaid not in self.qaids:
            self.qaids.append(qaid)
    
    def report(self, qaid: str):
        """Finalize and report QAID"""
        if qaid in self.results:
            all_passed = all(r['success'] for r in self.results[qaid])
            status = "PASS" if all_passed else "FAIL"
            print(f"\n{'='*60}")
            print(f"QAID {qaid}: {status}")
            print(f"{'='*60}")
            
            for i, result in enumerate(self.results[qaid], 1):
                print(f"  Step {i}: {'✓' if result['success'] else '✗'} {result['message']}")
            
            if not all_passed:
                raise AssertionError(f"QAID {qaid} failed")
    
    def get_qaid_results(self, qaid: str):
        """Get results for specific QAID"""
        return self.results.get(qaid, [])


def create_device(name: str, config: dict = None, use_mock: bool = False):
    """
    Factory to create either mock or real device based on configuration.
    
    Args:
        name: Device name (e.g., FGT_A, PC_05)
        config: Device configuration dict
        use_mock: If True, use mock device. If False (default), use real AutoLib v3 device
    
    Returns:
        Device instance (mock or real)
    """
    if use_mock:
        # Use mock device for testing/prototyping
        from mock_device import create_mock_device
        return create_mock_device(name, config)
    else:
        # Use real AutoLib v3 device
        import sys
        from pathlib import Path
        
        # Add AutoLib v3 lib to path if not already there
        autolib_lib = Path(__file__).parent.parent.parent / 'lib'
        if str(autolib_lib) not in sys.path:
            sys.path.insert(0, str(autolib_lib))
        
        try:
            from core.device import FortiGate, Pc, Computer
            
            # Determine device type from name
            name_upper = name.upper()
            if 'FGT' in name_upper or name.startswith('FG'):
                return FortiGate(name)
            elif name.startswith('PC_') or name.startswith('PC-'):
                return Pc(name)
            elif 'COMPUTER' in name_upper:
                return Computer(name)
            else:
                # Default to FortiGate
                logger = logging.getLogger(__name__)
                logger.warning(f"Unknown device type for {name}, defaulting to FortiGate")
                return FortiGate(name)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create real device {name}: {e}")
            logger.info("Falling back to mock device")
            from mock_device import create_mock_device
            return create_mock_device(name, config)


# Backward compatibility alias
FluentFortiGate = FluentDevice


class TestBed:
    """
    Test environment with device context management.
    
    Supports both mock devices (for prototyping/testing) and real devices.
    Default: Uses real AutoLib v3 devices.
    """
    
    def __init__(self, env_config: dict = None, use_mock: bool = None):
        """
        Initialize TestBed.
        
        Args:
            env_config: Environment configuration dict
            use_mock: If True, use mock devices. If False, use real devices.
                     If None (default), checks env var USE_MOCK_DEVICES, defaults to False (real)
        """
        self.env = env_config or {}
        self.devices = {}
        self.result_manager = ResultManager()
        self.results = self.result_manager  # Alias for compatibility
        self.logger = logging.getLogger(__name__)
        
        # Determine whether to use mock devices
        if use_mock is None:
            # Check environment variable
            use_mock_env = os.getenv('USE_MOCK_DEVICES', 'false').lower()
            self.use_mock = use_mock_env in ('true', '1', 'yes')
        else:
            self.use_mock = use_mock
        
        if self.use_mock:
            self.logger.info("TestBed configured to use MOCK devices")
        else:
            self.logger.info("TestBed configured to use REAL AutoLib v3 devices")
    
    @contextmanager
    def device(self, name: str):
        """Context manager for device operations (with fluent API)"""
        if name not in self.devices:
            # Create device from environment config
            device_conf = self.env.get(name, {})
            
            # Use factory to create appropriate device (mock or real)
            dev = create_device(name, device_conf, use_mock=self.use_mock)
            
            # Connect to device (both mock and real have connect())
            if hasattr(dev, 'connect'):
                dev.connect()
            
            self.devices[name] = dev
        
        device = self.devices[name]
        fluent = FluentDevice(device, self.result_manager, testbed=self)
        
        self.logger.info(f"Switching to device: {name}")
        
        yield fluent
        
        # Cleanup if needed (handled by fixtures)
    
    def get_device(self, name: str):
        """Get device without context manager (for fixtures)"""
        if name not in self.devices:
            device_conf = self.env.get(name, {})
            dev = create_device(name, device_conf, use_mock=self.use_mock)
            
            if hasattr(dev, 'connect'):
                dev.connect()
            
            self.devices[name] = dev
        
        return FluentDevice(self.devices[name], self.result_manager, testbed=self)
    
    def resolve_variables(self, command: str) -> str:
        """
        Resolve DEVICE:VARIABLE patterns in command string.
        
        Example:
            "exe backup ftp FGT_A:CUSTOMSIG1 PC_05:IP_ETH1 PC_05:PASSWORD"
            → "exe backup ftp custom1on1801F 172.16.200.55 Qa123456!"
        
        Args:
            command: Command string with potential DEVICE:VARIABLE patterns
            
        Returns:
            Command with variables resolved to actual values
        """
        import re
        
        # Pattern: DEVICE_NAME:VARIABLE_NAME
        # Device: uppercase letters/numbers/underscores (PC_05, FGT_A)
        # Variable: alphanumeric with underscores (CUSTOMSIG1, IP_ETH1, Model, PASSWORD)
        pattern = r'([A-Z][A-Z0-9_]*):([A-Za-z][A-Za-z0-9_]*)'
        
        def replace_var(match):
            device = match.group(1)
            variable = match.group(2)
            
            # Look up device in env config
            device_config = self.env.get(device, {})
            
            # Try case-insensitive lookup (try original case first, then lowercase)
            value = device_config.get(variable)
            
            if value is None:
                # Try lowercase (for normalized keys like password, username, model)
                value = device_config.get(variable.lower())
            
            if value is None:
                # Try uppercase (for env vars like IP_ETH1, CUSTOMSIG1)
                value = device_config.get(variable.upper())
            
            if value is not None:
                self.logger.debug(f"Resolved {device}:{variable} → {value}")
                return value
            else:
                # Variable not found, keep original
                self.logger.warning(f"Variable not found: {device}:{variable}")
                return match.group(0)
        
        resolved = re.sub(pattern, replace_var, command)
        return resolved
    
    def cleanup(self):
        """Clean up all device connections"""
        for device in self.devices.values():
            device.disconnect()
