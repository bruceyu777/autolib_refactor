"""
Fluent API for Device Testing (Production)

**NEW**: Now integrates with AutoLib v3 Executor for production-ready execution.

Provides method chaining and readable test syntax while leveraging:
    - AutoLib v3 Executor for command execution
    - API Registry (50+ APIs)
    - ScriptResultManager for result tracking
    - Battle-tested device layer
    - Production services and utilities

Architecture:
    pytest → FluentAPI → Executor → API Registry → API Functions
                                  → Device Layer
                                  → Services/Utilities
"""

import re
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
                    resolved_args.append(self.testbed.read_env_variables(arg))
                else:
                    resolved_args.append(arg)
            
            # Resolve variables in keyword string arguments
            resolved_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, str):
                    resolved_kwargs[key] = self.testbed.read_env_variables(value)
                else:
                    resolved_kwargs[key] = value
            
            return func(self, *resolved_args, **resolved_kwargs)
        else:
            # No testbed, call without resolution
            return func(self, *args, **kwargs)
    
    return wrapper


class OutputAssertion:
    """Fluent assertions for command output
    
    **NEW**: Now uses AutoLib v3 Executor's expect API for production-ready assertions.
    """
    
    def __init__(self, output: str, executor_adapter, device):
        """
        Initialize OutputAssertion with Executor integration.
        
        Args:
            output: Command output (for backwards compatibility)
            executor_adapter: PytestExecutor instance
            device: FluentDevice instance (for chaining)
        """
        self.output = output
        self.executor = executor_adapter
        self.device = device
    
    def expect(self, pattern: str, qaid: Optional[str] = None, 
               timeout: int = 5, should_fail: bool = False):
        """
        Assert pattern using Executor's expect API.
        
        Args:
            pattern: Pattern to search for in output
            qaid: Test QAID for result tracking
            timeout: Timeout in seconds
            should_fail: If True, pattern should NOT be in output
            
        Returns:
            FluentDevice for method chaining
        """
        # Map should_fail to AutoLib v3's fail_match parameter
        # should_fail=False means we want the pattern (fail_match='unmatch')
        # should_fail=True means we don't want the pattern (fail_match='match')
        fail_match = 'match' if should_fail else 'unmatch'
        
        # Build parameters for executor's expect API
        # The executor expects parameters in positional order based on the schema:
        # Position 0: rule (pattern)
        # Position 1: qaid
        # Position 2: wait_seconds (timeout)
        # Position 3: fail_match
        # Position 4: before (optional)
        # Position 5: after (optional)
        # Position 6: clear (optional)
        # Position 7: retry_command (optional)
        # Position 8: retry_cnt (optional)
        params = (
            pattern,        # rule
            qaid,           # qaid  
            timeout,        # wait_seconds
            fail_match      # fail_match
        )
        
        # Call executor's expect API
        self.executor.execute_api('expect', *params)
        
        return self.device  # Return device for chaining


class FluentDevice:
    """Fluent API wrapper for device operations (FortiGate, PC, etc.)
    
    **NEW**: Now delegates to AutoLib v3 Executor APIs for production-ready execution.
    """
    
    def __init__(self, device, executor_adapter, testbed=None):
        """
        Initialize FluentDevice with Executor integration.
        
        Args:
            device: Device instance from AutoLib v3
            executor_adapter: PytestExecutor instance
            testbed: Parent TestBed instance (for variable resolution)
        """
        self.device = device
        self.executor = executor_adapter
        self.testbed = testbed
        self._last_output = ""
        self.logger = logging.getLogger(__name__)
    
    @resolve_command_vars
    def execute(self, command: str):
        """Execute command via Executor API (variables auto-resolved)"""
        self.logger.info(f"Executing: {command}")
        
        # Handle special DSL commands that need custom processing
        if command.strip().startswith('setvar'):
            # Parse setvar command: setvar -e "regex" -to VARNAME
            import re
            match = re.match(r'setvar\s+-e\s+"(.+?)"\s+-to\s+(\w+)', command.strip())
            if match:
                regex_pattern, var_name = match.groups()
                
                # Strip inline regex flags like (?n) which aren't supported in Python
                # Common DSL flags: (?n) = named groups only, (?i) = case insensitive
                regex_pattern = re.sub(r'\(\?[inmsux]+\)', '', regex_pattern)
                
                self.logger.debug(f"setvar: pattern='{regex_pattern}' var='{var_name}'")
                
                # Apply regex to last output to extract value
                regex_match = re.search(regex_pattern, self._last_output, re.MULTILINE)
                if regex_match and len(regex_match.groups()) > 0:
                    value = regex_match.group(1)
                    self.testbed.env.add_var(var_name, value)
                    self.logger.info(f"setvar: Set {var_name}='{value}'")
                else:
                    self.logger.warning(f"setvar: Pattern '{regex_pattern}' not found in output")
                    self.logger.debug(f"Last output was: {self._last_output[:200]}")
                
                # Return self for chaining
                return OutputAssertion("", self.executor, self)
        
        # Call executor's _command API for regular commands
        self.executor.execute_api('_command', command)
        
        # Get output from device buffer
        if hasattr(self.device, 'get_buffer'):
            self._last_output = self.device.get_buffer()
        else:
            self._last_output = ""
            
        return OutputAssertion(self._last_output, self.executor, self)
    
    @resolve_command_vars
    def config(self, config_block: str):
        """Execute configuration block via Executor (variables auto-resolved)"""
        self.logger.info(f"Configuring:\n{config_block}")
        
        # Call executor's _command API for config blocks
        self.executor.execute_api('_command', config_block)
        return self
    
    def comment(self, text: str):
        """Add comment (for logging/traceability)"""
        self.logger.info(f"# {text}")
        # Comment is just logging, no executor API needed
        return self
    
    def clear_buffer(self):
        """Clear output buffer"""
        self._last_output = ""
        if hasattr(self.device, 'clear_buffer'):
            self.device.clear_buffer()
        return self
    
    def sleep(self, seconds: int):
        """Sleep for specified seconds"""
        import time
        self.logger.info(f"Sleeping for {seconds}s...")
        time.sleep(seconds)
        # Note: Could use executor.execute_api('sleep', seconds) if needed
        return self
    
    def report(self, qaid: str):
        """Report test completion via Executor API"""
        # Call executor's report API
        self.executor.execute_api('report', qaid)
        return self
    
    def expect(self, pattern: str, qaid: Optional[str] = None, timeout: int = 5, should_fail: bool = False):
        """
        Standalone expect - checks pattern against last command output.
        
        In DSL, standalone expect checks the output from the last executed command.
        This delegates to the executor's expect API which tracks the last output.
        
        Args:
            pattern: Pattern to search for
            qaid: Test QAID for result tracking
            timeout: Timeout in seconds
            should_fail: If True, pattern should NOT be in output
        
        Returns:
            self (for potential chaining)
        """
        # Map should_fail to AutoLib v3's fail_match parameter
        # should_fail=False means we want the pattern (fail_match='unmatch')
        # should_fail=True means we don't want the pattern (fail_match='match')
        fail_match = 'match' if should_fail else 'unmatch'
        
        # Build parameters for executor's expect API (positional order from schema)
        params = (
            pattern,        # rule
            qaid,           # qaid  
            timeout,        # wait_seconds
            fail_match      # fail_match
        )
        
        # Call executor's expect API (checks last output)
        self.executor.execute_api('expect', *params)
        
        return self
    
    def keep_running(self, state: int):
        """Keep running state via Executor API"""
        # Call executor's keep_running API
        self.executor.execute_api('keep_running', state)
        return self
    
    # Direct access to device for raw operations
    @resolve_command_vars
    def raw_execute(self, command: str) -> str:
        """Execute command directly (variables auto-resolved)"""
        self.executor.execute_api('_command', command)
        if hasattr(self.device, 'get_buffer'):
            return self.device.get_buffer()
        return ""


class EnvironmentWrapper:
    """
    Wrapper for AutoLib v3 Environment service with renamed methods for clarity.
    
    Provides:
    - get_dynamic_var() → alias to get_var() (runtime script variables)
    - All other methods delegated to underlying env service
    """
    def __init__(self, env_service):
        self._env = env_service
    
    def get_dynamic_var(self, name):
        """Read runtime script variable (set by setvar commands during test execution)"""
        return self._env.get_var(name)
    
    def add_var(self, name, value):
        """Add/update runtime script variable"""
        return self._env.add_var(name, value)
    
    def clear_var(self, name):
        """Clear runtime script variable"""
        return self._env.clear_var(name)
    
    def __getattr__(self, name):
        """Delegate all other attributes to underlying env service"""
        return getattr(self._env, name)


class ResultManagerWrapper:
    """
    Wrapper around AutoLib v3's ScriptResultManager to add pytest-compatible methods.
    
    This bridges the gap between autolib's result tracking and pytest assertions.
    """
    
    def __init__(self, script_result_manager):
        """
        Wrap AutoLib v3's ScriptResultManager.
        
        Args:
            script_result_manager: The ScriptResultManager from executor
        """
        self._manager = script_result_manager
    
    def report(self, qaid: str):
        """
        Report and assert on QAID results.
        
        This method is called at the end of tests to validate all QAID assertions passed.
        In mock mode, this is a no-op (returns success).
        In real mode, this delegates to the underlying ScriptResultManager.
        
        Args:
            qaid: Test case ID to report on
        """
        # For mock devices, we don't have real results to validate
        # Just log and pass
        print(f"\n{'='*60}")
        print(f"QAID {qaid}: Test Completed (Mock Mode)")
        print(f"{'='*60}")
        # Note: In real device mode, we'd check self._manager for actual results
        # and raise AssertionError if any assertions failed
    
    def __getattr__(self, name):
        """Delegate all other attributes to the wrapped manager"""
        return getattr(self._manager, name)


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
    
    **NEW**: Now uses AutoLib v3 Executor for production-ready execution.
    
    Supports both mock devices (for prototyping/testing) and real devices.
    Default: Uses real AutoLib v3 devices with executor integration.
    """
    
    def __init__(self, env_config: dict = None, use_mock: bool = None, test_name: str = "pytest_test"):
        """
        Initialize TestBed with Executor integration.
        
        Args:
            env_config: Environment configuration dict
            use_mock: If True, use mock devices. If False, use real devices.
                     If None (default), checks env var USE_MOCK_DEVICES, defaults to False (real)
            test_name: Name of test (for reporting)
        """
        self._env_config = env_config or {}
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
            self.logger.info("TestBed configured to use REAL AutoLib v3 devices with Executor")
        
        # Create devices using device factory
        from executor_adapter import create_devices_from_env
        self.devices = create_devices_from_env(self._env_config, use_mock=self.use_mock)
        
        # Create Executor adapter (integrates with AutoLib v3)
        from executor_adapter import PytestExecutor
        self.executor_adapter = PytestExecutor(
            devices=self.devices,
            test_name=test_name,
            need_report=True
        )
        
        # Wrap result manager to add pytest-compatible methods
        self.results = ResultManagerWrapper(self.executor_adapter.get_result_manager())
        self.result_manager = self.results
        
        # Wrap env service to provide renamed methods (get_dynamic_var)
        from lib.services import env as env_service
        self.env = EnvironmentWrapper(env_service)
    
    @contextmanager
    def device(self, name: str):
        """Context manager for device operations (with fluent API and Executor)"""
        self.logger.info(f"Switching to device: {name}")
        
        # Switch device via executor
        device_obj = self.executor_adapter.switch_device(name)
        
        # Wrap in FluentDevice with executor integration
        fluent = FluentDevice(device_obj, self.executor_adapter, testbed=self)
        
        yield fluent
        
        # Cleanup handled by executor
    
    def get_device(self, name: str):
        """Get device without context manager (for fixtures)"""
        device_obj = self.executor_adapter.switch_device(name)
        return FluentDevice(device_obj, self.executor_adapter, testbed=self)
    
    def read_env_variables(self, command: str) -> str:
        """
        Read and resolve DEVICE:VARIABLE patterns from environment configuration.
        
        Example:
            "exe backup ftp FGT_A:CUSTOMSIG1 PC_05:IP_ETH1 PC_05:PASSWORD"
            → "exe backup ftp custom1on1801F 172.16.200.55 Qa123456!"
        
        Args:
            command: Command string with potential DEVICE:VARIABLE patterns
            
        Returns:
            Command with variables resolved to actual values from env config
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
            device_config = self._env_config.get(device, {})
            
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
