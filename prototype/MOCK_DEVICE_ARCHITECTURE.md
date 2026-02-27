# Mock Device Architecture - Design Document

## Overview

The mock device architecture follows **separation of concerns** with a base class and specialized implementations for different device types.

## Class Hierarchy

```
MockDevice (Base)
├── MockFortiGate (FortiOS simulation)
└── MockPC (Linux/PC simulation)
```

## Design Principles

### 1. **Base Class: MockDevice**

Contains common device operations:
- Connection management (`connect()`, `disconnect()`)
- Command history tracking
- Logging infrastructure
- Basic `execute()` interface

### 2. **Specialized Classes**

Each device type implements:
- Device-specific command handlers
- State management appropriate to the device
- Output formatting that matches real device behavior

## Class Details

### MockDevice (Base)

```python
class MockDevice:
    """Base mock device with common operations"""
    
    def __init__(self, name: str, config: Optional[Dict] = None)
    def connect(self)
    def disconnect(self)
    def execute(self, command: str) -> str  # To be overridden
```

**Purpose**: Provide common interface and minimal functionality

**State**:
- `name`: Device identifier
- `config`: Device configuration dict
- `connected`: Connection status
- `command_history`: List of executed commands
- `logger`: Logging instance

### MockFortiGate

```python
class MockFortiGate(MockDevice):
    """FortiGate device simulator with FOS command support"""
```

**Additional State**:
- `custom_signatures`: IPS signature storage `{name: signature_data}`
- `backup_files`: File backup storage `{filename: content}`
- `current_vdom`: Current VDOM context

**Supported Commands**:
- `config ips custom` - Multi-line IPS signature configuration
- `show ips custom` - Display stored signatures
- `exe backup ipsuserdefsig` - Backup signatures to file
- `config vdom` - VDOM context switching
- `edit vd1` - Enter VDOM
- `get system status` - System information
- `diagnose` - Diagnostic commands
- `sleep` - Sleep/wait
- `purge` - Clear signatures
- `reboot` - Simulated reboot (in config blocks)

**Special Features**:
- Multi-line config block parsing
- IPS signature extraction with regex
- State persistence across reboot
- FortiOS-style output formatting

### MockPC

```python
class MockPC(MockDevice):
    """PC/Linux device simulator"""
```

**Additional State**:
- `files`: Simulated filesystem `{filename: content}`

**Supported Commands**:
- `cmp file1 file2` - File comparison
- `rm [-f] file` - File deletion
- `ls [dir]` - List files
- `cat file` - Display file content
- `echo text` - Echo text
- `pwd` - Print working directory
- `cd dir` - Change directory

**Special Features**:
- Simulated filesystem for file operations
- Linux-style command output
- Error messages for unknown commands

## Factory Pattern

### create_mock_device()

```python
def create_mock_device(name: str, config: Optional[Dict] = None) -> MockDevice
```

**Detection Logic**:
1. If name starts with `FGT` or contains `FGT` → `MockFortiGate`
2. If name starts with `PC_` or `PC-` → `MockPC`
3. Default → `MockFortiGate` (with warning)

**Examples**:
- `FGT_A` → `MockFortiGate`
- `FGT_PRIMARY` → `MockFortiGate`
- `FGTA` → `MockFortiGate`
- `PC_05` → `MockPC`
- `PC-Linux-01` → `MockPC`

## Integration with Fluent API

### fluent.py

```python
from mock_device import create_mock_device

# In TestBed.device():
dev = create_mock_device(name, device_conf)
dev.connect()
```

The factory automatically selects the correct device type based on the device name.

## Usage Examples

### FortiGate Operations

```python
fgt = create_mock_device("FGT_A")
fgt.connect()

# Configure IPS signatures
fgt.execute('''
config ips custom
edit "my_signature"
set signature "F-SBID(--name test)"
next
end
''')

# Show signatures
output = fgt.execute("show ips custom")
# Returns FortiOS-formatted config output
```

### PC Operations

```python
pc = create_mock_device("PC_05")
pc.connect()

# Simulate file operations
pc.files["backup1.txt"] = "content A"
pc.files["backup2.txt"] = "content A"

# Compare files
result = pc.execute("cmp /root/backup1.txt /root/backup2.txt")
# Returns "" if identical, "differ" if different

# Delete file
pc.execute("rm -f /root/backup1.txt")
```

## Extending the Architecture

### Adding New Device Types

1. **Create new class**:
```python
class MockSwitch(MockDevice):
    """Switch device simulator"""
    
    def __init__(self, name: str, config: Optional[Dict] = None):
        super().__init__(name, config)
        self.vlans = {}  # Switch-specific state
    
    def execute(self, command: str) -> str:
        # Switch-specific command handling
        if command.startswith("show vlan"):
            return self._format_vlans()
        return super().execute(command)
```

2. **Update factory**:
```python
def create_mock_device(name: str, config: Optional[Dict] = None) -> MockDevice:
    if name.startswith("SW_"):
        return MockSwitch(name, config)
    elif name.startswith("FGT"):
        return MockFortiGate(name, config)
    # ... etc
```

### Adding New Commands

#### For FortiGate:

Add handler in `MockFortiGate.execute()`:

```python
def execute(self, command: str) -> str:
    # ... existing code ...
    
    elif command.startswith("get system interface"):
        return self._format_interfaces()
    
    elif command == "show full-configuration firewall policy":
        return self._show_policies()
```

#### For PC:

Add handler in `MockPC.execute()`:

```python
def execute(self, command: str) -> str:
    # ... existing code ...
    
    elif command.startswith("wget "):
        url = command.split()[1]
        self.files["index.html"] = f"Downloaded from {url}"
        return ""
```

## Benefits of This Architecture

### 1. **Separation of Concerns**
- Each device type has its own implementation
- No cross-contamination of FortiGate and PC logic
- Easy to understand and maintain

### 2. **Extensibility**
- Add new device types without modifying existing code
- Extend existing devices with new commands
- Override base methods as needed

### 3. **Type Safety**
- Factory returns appropriate type
- IDE autocomplete works correctly
- Type hints for better development experience

### 4. **Testability**
- Mock each device type independently
- Test device-specific functionality in isolation
- Easy to add unit tests for new features

### 5. **Maintainability**
- One file, multiple classes, clear hierarchy
- Each class has focused responsibility
- Easy to locate and fix bugs

## File Structure

```
fluent_api/
├── mock_device.py          # All mock device classes + factory
├── fluent.py               # Fluent API using create_mock_device()
├── mock_device_old.py      # Backup of original (can be removed)
└── ...
```

## Testing

### Factory Test

```bash
cd prototype
python3 test_mock_factory.py
```

Verifies:
- ✓ Correct device type creation based on name
- ✓ FortiGate-specific functionality (IPS signatures)
- ✓ PC-specific functionality (file operations)

### Integration Test

```bash
cd prototype/output
pytest test__205812.py -v
```

Verifies:
- ✓ Multi-device test (FGT_A + PC_05)
- ✓ FortiGate operations work correctly
- ✓ PC operations work correctly
- ✓ Cross-device interactions (backup to PC, compare files)

## Migration Notes

### From Old Architecture

**Before**:
```python
from mock_device import MockDevice
dev = MockDevice(name, config)  # Single class for all devices
```

**After**:
```python
from mock_device import create_mock_device
dev = create_mock_device(name, config)  # Factory selects type
```

### Backward Compatibility

The old `MockDevice(name, config)` syntax still works via the deprecated wrapper, but using `create_mock_device()` is recommended.

## Future Enhancements

- [ ] Add MockSwitch for switch simulation
- [ ] Add MockAP for access point simulation
- [ ] Real device support (SSH/Telnet backends)
- [ ] State serialization (save/restore device state)
- [ ] Command recording/playback
- [ ] Performance metrics (command execution time)
- [ ] Plugin architecture for custom command handlers

## Summary

The refactored architecture provides:
- ✅ Clear separation between FortiGate and PC simulation
- ✅ Easy extensibility for new device types
- ✅ Better code organization and maintainability
- ✅ Type-safe factory pattern
- ✅ Fully backward compatible
- ✅ All existing tests pass without modification
