# Variable Resolution with Decorator Pattern

## Overview

Variable resolution (replacing `DEVICE:VARIABLE` patterns with actual values from environment config) is now implemented using a **decorator pattern** that automatically resolves variables in **all string parameters** across all FluentDevice methods.

## Implementation

### The Decorator

```python
def resolve_command_vars(func):
    """
    Decorator to automatically resolve DEVICE:VARIABLE patterns in command strings.
    
    Resolves variables in all string arguments before method execution.
    Requires the instance to have a 'testbed' attribute with resolve_variables() method.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if hasattr(self, 'testbed') and self.testbed:
            # Resolve variables in positional string arguments
            resolved_args = [
                self.testbed.resolve_variables(arg) if isinstance(arg, str) else arg 
                for arg in args
            ]
            
            # Resolve variables in keyword string arguments
            resolved_kwargs = {
                key: self.testbed.resolve_variables(value) if isinstance(value, str) else value
                for key, value in kwargs.items()
            }
            
            return func(self, *resolved_args, **resolved_kwargs)
        else:
            return func(self, *args, **kwargs)
    
    return wrapper
```

### Usage in FluentDevice

Simply apply the decorator to any method that accepts string parameters:

```python
class FluentDevice:
    @resolve_command_vars
    def execute(self, command: str):
        """Execute command (variables auto-resolved)"""
        # command already has variables resolved by decorator
        self.logger.info(f"Executing: {command}")
        self._last_output = self.device.execute(command)
        return OutputAssertion(self._last_output, self.results, self)
    
    @resolve_command_vars
    def config(self, config_block: str):
        """Execute configuration block (variables auto-resolved)"""
        # config_block already has variables resolved by decorator
        self.logger.info(f"Configuring:\n{config_block}")
        self.device.execute(config_block)
        return self
    
    @resolve_command_vars
    def raw_execute(self, command: str) -> str:
        """Execute command without fluent API wrapper (variables auto-resolved)"""
        # command already has variables resolved by decorator
        return self.device.execute(command)
```

## Benefits

### ✅ Automatic & Universal
- **All string parameters** are automatically resolved
- Works for positional and keyword arguments
- No need to manually call `resolve_variables()` in each method

### ✅ Clean Code
- No repetitive resolution code in each method
- Single source of truth for resolution logic
- Easy to apply to new methods

### ✅ Consistent Behavior
- Same resolution logic across all methods
- Case-insensitive variable lookup
- Proper fallback if variable not found

### ✅ DRY Principle
- Don't Repeat Yourself - decorator handles it once
- Easy to maintain and update resolution logic
- Reduced chance of bugs from forgotten resolution calls

## Examples

### Example 1: execute() Method

```python
# In test code (variables in string):
fgt.execute("exe backup ftp FGT_A:CUSTOMSIG1 PC_05:IP_ETH1 root PC_05:PASSWORD")

# Decorator automatically resolves before execution:
# "exe backup ftp custom1on1801F 172.16.200.55 root Qa123456!"
```

### Example 2: config() Method

```python
# In test code (variables in config block):
fgt.config("""
    config ips custom
    edit "FGT_A:CUSTOMSIG1"
    set file "PC_05:SCRIPT/FGT_A:CUSTOMSIG2"
    next
    end
""")

# Decorator automatically resolves all variables:
# edit "custom1on1801F"
# set file "/home/tester/attack_scripts/custom2on1801F"
```

### Example 3: Multiple Methods

```python
# All these methods get automatic variable resolution:
fgt.execute("command with FGT_A:Model")              # ✅ Resolved
fgt.config("config with PC_05:IP_ETH1")               # ✅ Resolved
fgt.raw_execute("raw command with PC_05:PASSWORD")   # ✅ Resolved
```

## Technical Details

### Resolution Order

For each `DEVICE:VARIABLE` pattern, the decorator tries:

1. **Exact match**: `device_config.get(variable)`
2. **Lowercase**: `device_config.get(variable.lower())`
3. **Uppercase**: `device_config.get(variable.upper())`
4. **Keep original**: If not found, keep `DEVICE:VARIABLE` unchanged

### Pattern Matching

**Regex Pattern**: `r'([A-Z][A-Z0-9_]*):([A-Za-z][A-Za-z0-9_]*)'`

**Matches**:
- `FGT_A:CUSTOMSIG1` ✅
- `PC_05:IP_ETH1` ✅
- `PC_05:PASSWORD` ✅
- `FGT_A:Model` ✅

**Does Not Match**:
- `lowercase:variable` ❌ (device must start with uppercase)
- `DEVICE:123` ❌ (variable must start with letter)

### Performance

- **Minimal overhead**: Regex substitution is very fast
- **Lazy evaluation**: Only resolves if testbed exists
- **No caching needed**: Environment config is in-memory dict lookup

## Migration from Manual Resolution

### Before (Manual Resolution)

```python
def execute(self, command: str):
    # Manual resolution in each method
    if self.testbed:
        command = self.testbed.resolve_variables(command)
    
    self.logger.info(f"Executing: {command}")
    self._last_output = self.device.execute(command)
    return OutputAssertion(self._last_output, self.results, self)

def config(self, config_block: str):
    # Oops! Forgot to add resolution here - BUG!
    self.logger.info(f"Configuring:\n{config_block}")
    self.device.execute(config_block)
    return self
```

### After (Decorator Pattern)

```python
@resolve_command_vars
def execute(self, command: str):
    # Variables already resolved by decorator
    self.logger.info(f"Executing: {command}")
    self._last_output = self.device.execute(command)
    return OutputAssertion(self._last_output, self.results, self)

@resolve_command_vars
def config(self, config_block: str):
    # Variables already resolved by decorator - no bugs!
    self.logger.info(f"Configuring:\n{config_block}")
    self.device.execute(config_block)
    return self
```

## Testing

### Test File: `test_decorator_resolution.py`

Tests variable resolution across all methods:

```bash
python3 test_decorator_resolution.py
```

**Output**:
```
✅ All Decorator Tests PASSED

Summary:
- execute() method: ✅ Variables resolved
- config() method: ✅ Variables resolved
- raw_execute() method: ✅ Variables resolved
- Multiple variables: ✅ All resolved
- Complex config blocks: ✅ All resolved
```

### pytest Integration Test

```bash
cd output && pytest test__205812.py -vs
```

**Result**: ✅ PASS (7/7 assertions)

## Future Extensions

### Easy to Add New Methods

```python
@resolve_command_vars
def new_method(self, command: str, path: str):
    # Both command AND path get automatic variable resolution
    # No extra code needed!
    ...
```

### Optional Selective Resolution

If needed, could extend decorator to specify which parameters to resolve:

```python
@resolve_command_vars(params=['command'])  # Only resolve 'command' param
def method(self, command: str, literal_string: str):
    # command: resolved
    # literal_string: NOT resolved (kept as-is)
    ...
```

## Summary

The **decorator pattern** provides:
- ✅ **Automatic** variable resolution across all methods
- ✅ **Universal** application to all string parameters
- ✅ **Clean** code without repetition
- ✅ **Consistent** behavior everywhere
- ✅ **DRY** - single place to update resolution logic
- ✅ **Bug-resistant** - can't forget to add resolution

All methods in `FluentDevice` that accept string parameters now automatically resolve `DEVICE:VARIABLE` patterns before execution, ensuring consistency and reducing maintenance burden.
