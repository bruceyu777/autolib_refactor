# DSL to pytest Migration - Complete Process Guide

## Overview

This guide walks through the complete DSL → pytest migration process, showing how to:
1. View the original DSL test
2. Generate vmcode from DSL (AutoLib v3 compiler)
3. Convert DSL to pytest (new transpiler)
4. Compare all three formats

## File Locations

### Source Files (Original DSL)
```
/home/fosqa/autolibv3/autolib_v3/testcase/ips/topology1/
├── 205812.txt                    # Original DSL test
├── env.fortistack.ips.conf       # Environment configuration
└── includes/
    ├── govdom1.txt               # VDOM entry include
    └── outvdom.txt               # VDOM exit include
```

### Prototype Files (Migration Tools)
```
/home/fosqa/autolibv3/autolib_v3/prototype/
├── fluent_api/                   # Python fluent API
│   ├── fluent.py                 # FluentFortiGate, TestBed, ResultManager
│   └── mock_device.py            # Mock device for testing
│
├── sample_includes/              # Sample include files for prototype
│   ├── govdom1.txt               # VDOM entry
│   └── outvdom.txt               # VDOM exit
│
├── tools/                        # Transpiler tools
│   ├── conversion_registry.py   # Track include→fixture conversions
│   ├── include_converter.py     # Convert includes to fixtures
│   └── dsl_transpiler.py         # Main DSL→pytest transpiler
│
├── output/                       # Generated pytest files
│   ├── conftest.py               # Auto-generated fixtures
│   ├── test_205812.py            # Auto-generated pytest test
│   └── .conversion_registry.json # Conversion tracking database
│
├── run_transpiler.py             # Quick runner script
├── PROTOTYPE_SUMMARY.md          # Prototype documentation
└── MIGRATION_PROCESS_GUIDE.md    # This file
```

---

## Step-by-Step Migration Process

### Step 1: View Original DSL Test

**Command**:
```bash
cd /home/fosqa/autolibv3/autolib_v3
cat testcase/ips/topology1/205812.txt
```

**What to look for**:
- Device sections: `[FGT_A]`, `[PC_05]`
- Include directives: `include testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt`
- Commands: `config ips custom`, `show ips custom`
- Assertions: `expect -e "pattern" -for 205812`

**Example snippet**:
```plaintext
[FGT_A]
    comment REGR_IPS_02_01:Busy: create custom signatures
    include testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt
    config ips custom
        edit "match small"
            set signature "F-SBID(...)"
        next
    end
    show ips custom
    expect -e "match small" -for 205812 -t 5
```

---

### Step 2: Generate vmcode (AutoLib v3 Compiler)

**Purpose**: See the intermediate bytecode that AutoLib v3 generates

**Command**:
```bash
cd /home/fosqa/autolibv3/autolib_v3

# Compile DSL to vmcode
python3 autotest.py --file testcase/ips/topology1/205812.txt --compile-only
```

**Expected output location**:
```
outputs/205812/vmcode.txt          # Generated VM bytecode
outputs/205812/test_info.json     # Test metadata
```

**View the vmcode**:
```bash
# View compiled vmcode
cat outputs/205812/vmcode.txt

# Or with line numbers
cat -n outputs/205812/vmcode.txt | less
```

**What vmcode looks like** (example):
```
LOAD_DEVICE FGT_A
EXECUTE "comment REGR_IPS_02_01:Busy: create custom signatures"
LOAD_INCLUDE govdom1.txt
EXECUTE "config ips custom"
EXECUTE "edit \"match small\""
EXECUTE "set signature \"F-SBID(...)\""
EXECUTE "next"
EXECUTE "end"
EXECUTE "show ips custom"
EXPECT "match small" QAID=205812 TIMEOUT=5
POP_DEVICE
```

**Alternative - Use autotest.py with verbose mode**:
```bash
# See full compilation process
python3 autotest.py --file testcase/ips/topology1/205812.txt --verbose --compile-only
```

---

### Step 3: Convert DSL to pytest (New Transpiler)

**Command**:
```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype

# Run the transpiler
python3 run_transpiler.py
```

**What happens**:
```
🚀 DSL to pytest Transpiler - Prototype Demo
======================================================================

TRANSPILING: 205812.txt
============================================================

[1/5] Parsing DSL test...
  ✓ QAID: 205812
  ✓ Title: IPS Regression Test Case 2.1
  ✓ Sections: 4
  ✓ Includes: 3

[2/5] Initializing conftest.py...
  ✓ Created: conftest.py

[3/5] Converting include dependencies...
→ Converting dependency: govdom1.txt
  ✓ Converted fixture: govdom1.txt → setup_govdom1
→ Converting dependency: outvdom.txt
  ✓ Converted fixture: outvdom.txt → cleanup_outvdom
  ✓ Fixtures generated: ['setup_govdom1', 'cleanup_outvdom']

[4/5] Updating registry...
  ✓ Registry saved

[5/5] Generating test file...
  ✓ Created: test_205812.py

============================================================
TRANSPILATION COMPLETE
============================================================
Test file: output/test_205812.py
Fixtures: setup_govdom1, cleanup_outvdom
============================================================
```

**Generated files**:
```
output/
├── conftest.py               # Fixtures from includes
├── test_205812.py            # Converted pytest test
└── .conversion_registry.json # Tracking database
```

---

### Step 4: View Generated pytest Files

#### 4.1: View test_205812.py

**Command**:
```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype/output
cat test_205812.py
```

**Or with syntax highlighting**:
```bash
pygmentize -l python test_205812.py
# Or
bat test_205812.py  # If bat is installed
```

**What you'll see**:
```python
def test_205812(testbed, setup_govdom1, cleanup_outvdom):
    """IPS Regression Test Case 2.1"""
    
    with testbed.device('FGT_A') as fgt_a:
        fgt_a.execute("comment REGR_IPS_02_01:Busy: create custom signatures")
        fgt_a.execute("""
    config ips custom
    edit "match small"
    set signature "F-SBID(...)"
    next
    end
        """)
        fgt_a.execute("show ips custom")
        fgt_a.execute("").expect("match small", qaid="205812")
```

#### 4.2: View conftest.py (Fixtures)

**Command**:
```bash
cat conftest.py
```

**What you'll see**:
```python
@pytest.fixture
def testbed():
    """TestBed fixture with device connections"""
    testbed = TestBed()
    testbed.register_device('FGT_A', MockDevice('FGT_A'))
    testbed.register_device('PC_05', MockDevice('PC_05'))
    return testbed

@pytest.fixture
def setup_govdom1(testbed):
    """Auto-generated from: govdom1.txt"""
    fgt = testbed.get_device('FGT_A')
    fgt.execute('config vdom')
    fgt.execute('edit vd1')
    return fgt

@pytest.fixture
def cleanup_outvdom(testbed):
    """Auto-generated from: outvdom.txt"""
    yield testbed
    fgt = testbed.get_device('FGT_A')
    fgt.execute('end')
```

#### 4.3: View Conversion Registry

**Command**:
```bash
cat .conversion_registry.json | python3 -m json.tool
```

**What you'll see**:
```json
{
  "version": "1.0",
  "conversions": {
    "testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt": {
      "type": "fixture",
      "fixture_name": "setup_govdom1",
      "fixture_file": "conftest.py",
      "hash": "51f3ccadd5df25e1",
      "used_by": ["test_205812"]
    },
    "testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt": {
      "type": "fixture",
      "fixture_name": "cleanup_outvdom",
      "fixture_file": "conftest.py",
      "hash": "b652554d0918b608",
      "used_by": ["test_205812"]
    }
  }
}
```

---

### Step 5: View Fluent API Implementation

**Check the Python fluent API that powers the generated tests**:

```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype

# View fluent API
cat fluent_api/fluent.py

# View mock device
cat fluent_api/mock_device.py
```

**Key classes**:
- `FluentFortiGate` - Method chaining for commands
- `OutputAssertion` - Expect pattern matching
- `TestBed` - Device management and context switching
- `ResultManager` - QAID tracking and reporting
- `MockDevice` - Simulate device behavior for testing

---

## Comparison: DSL vs vmcode vs pytest

### Original DSL (205812.txt)
```plaintext
[FGT_A]
    include testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt
    config ips custom
        edit "match small"
            set signature "F-SBID(...)"
        next
    end
    show ips custom
    expect -e "match small" -for 205812 -t 5
```

### Generated vmcode (outputs/205812/vmcode.txt)
```
LOAD_DEVICE FGT_A
LOAD_INCLUDE govdom1.txt
EXECUTE "config ips custom"
EXECUTE "edit \"match small\""
EXECUTE "set signature \"F-SBID(...)\""
EXECUTE "next"
EXECUTE "end"
EXECUTE "show ips custom"
EXPECT "match small" QAID=205812 TIMEOUT=5
POP_DEVICE
```

### Generated pytest (test_205812.py)
```python
def test_205812(testbed, setup_govdom1, cleanup_outvdom):
    with testbed.device('FGT_A') as fgt_a:
        fgt_a.execute("""
    config ips custom
    edit "match small"
    set signature "F-SBID(...)"
    next
    end
        """)
        fgt_a.execute("show ips custom")
        fgt_a.execute("").expect("match small", qaid="205812")
```

**Key Differences**:

| Aspect | DSL | vmcode | pytest |
|--------|-----|---------|--------|
| **Format** | Text DSL | Bytecode instructions | Python code |
| **Includes** | `include ...` directive | `LOAD_INCLUDE` instruction | Fixture injection |
| **Device switching** | `[DEVICE]` section | `LOAD_DEVICE`/`POP_DEVICE` | Context manager |
| **Commands** | Plain text | `EXECUTE "..."` | `.execute("...")` |
| **Assertions** | `expect -e "..."` | `EXPECT "..." QAID=...` | `.expect("...", qaid="...")` |
| **Readability** | High | Low (bytecode) | Very High |
| **Debuggability** | Medium | Hard | Easy (Python debugger) |
| **IDE support** | None | None | Full (autocomplete, linting) |

---

## Quick Reference Commands

### View Original DSL
```bash
# View test file
cat /home/fosqa/autolibv3/autolib_v3/testcase/ips/topology1/205812.txt

# View environment
cat /home/fosqa/autolibv3/autolib_v3/testcase/ips/env.fortistack.ips.conf

# Search for more tests
find /home/fosqa/autolibv3/autolib_v3/testcase -name "*.txt" -type f | head -20
```

### Generate vmcode
```bash
cd /home/fosqa/autolibv3/autolib_v3

# Compile single test
python3 autotest.py --file testcase/ips/topology1/205812.txt --compile-only

# View generated vmcode
cat outputs/205812/vmcode.txt
ls -lh outputs/205812/
```

### Run Transpiler
```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype

# Generate pytest from DSL
python3 run_transpiler.py

# View generated files
ls -lh output/
cat output/test_205812.py
cat output/conftest.py
```

### View Transpiler Tools
```bash
# Registry tracker
cat prototype/tools/conversion_registry.py

# Include converter
cat prototype/tools/include_converter.py

# Main transpiler
cat prototype/tools/dsl_transpiler.py
```

### Test Generated pytest
```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype/output

# Run with pytest
pytest -v test_205812.py

# Run with verbose output
pytest -v -s test_205812.py

# Run with pytest debugging
pytest -v -s --pdb test_205812.py
```

---

## File Tree Summary

### Complete Prototype Structure
```
/home/fosqa/autolibv3/autolib_v3/
│
├── testcase/ips/topology1/          # Original DSL tests
│   ├── 205812.txt                   # ← START HERE (original DSL)
│   └── env.fortistack.ips.conf      # Environment config
│
├── outputs/205812/                  # AutoLib v3 compiler outputs
│   ├── vmcode.txt                   # ← Generated vmcode (Step 2)
│   └── test_info.json               # Test metadata
│
└── prototype/                       # Migration prototype
    │
    ├── fluent_api/                  # Python fluent API
    │   ├── fluent.py                # ← Core API (200+ lines)
    │   └── mock_device.py           # ← Mock simulator (130+ lines)
    │
    ├── tools/                       # Transpiler tools
    │   ├── conversion_registry.py   # ← Registry tracker (180 lines)
    │   ├── include_converter.py     # ← Include→fixture (200 lines)
    │   └── dsl_transpiler.py        # ← Main transpiler (400+ lines)
    │
    ├── sample_includes/             # Sample includes for prototype
    │   ├── govdom1.txt              # VDOM entry
    │   └── outvdom.txt              # VDOM exit
    │
    ├── output/                      # Generated pytest files
    │   ├── conftest.py              # ← Generated fixtures (71 lines)
    │   ├── test_205812.py           # ← Generated test (81 lines)
    │   └── .conversion_registry.json # Tracking database (952 bytes)
    │
    ├── run_transpiler.py            # ← Quick runner
    ├── PROTOTYPE_SUMMARY.md         # Prototype documentation
    └── MIGRATION_PROCESS_GUIDE.md   # This guide
```

---

## Typical Workflow

### For Test Developer
```bash
# 1. View original test
cat testcase/ips/topology1/205812.txt

# 2. Run transpiler
cd prototype && python3 run_transpiler.py

# 3. Review generated pytest
cd output
cat test_205812.py
cat conftest.py

# 4. Run the test
pytest -v test_205812.py

# 5. Debug if needed
pytest -v -s --pdb test_205812.py
```

### For Migration Engineer
```bash
# 1. Understand current compilation
python3 autotest.py --file testcase/ips/topology1/205812.txt --compile-only
cat outputs/205812/vmcode.txt

# 2. Compare with pytest conversion
cd prototype
python3 run_transpiler.py
cat output/test_205812.py

# 3. Check conversion registry
cat output/.conversion_registry.json | python3 -m json.tool

# 4. Validate transpiler logic
cd tools
python3 -c "
from dsl_transpiler import DSLTranspiler
from conversion_registry import ConversionRegistry

registry = ConversionRegistry()
transpiler = DSLTranspiler(registry)
registry.print_stats()
"
```

---

## Debugging Tips

### Check File Locations
```bash
# Find all test files
find /home/fosqa/autolibv3/autolib_v3/testcase -name "*.txt" | wc -l

# Find include files
find /home/fosqa/autolibv3/autolib_v3/testcase -name "*gov*.txt"

# Check generated files
ls -lh prototype/output/
```

### View Transpiler Logs
```bash
# Run with full output
cd prototype
python3 run_transpiler.py 2>&1 | tee transpiler.log

# View specific sections
grep "Converting dependency" transpiler.log
grep "✓ Created" transpiler.log
```

### Validate Generated Code
```bash
# Check Python syntax
cd prototype/output
python3 -m py_compile test_205812.py
python3 -m py_compile conftest.py

# Check with pylint
pylint test_205812.py
pylint conftest.py

# Check with mypy
mypy test_205812.py
```

---

## Next Steps

1. **Explore more test cases**: Convert additional tests from `testcase/ips/topology1/`
2. **Compare vmcode**: Study vmcode patterns for complex scenarios
3. **Extend transpiler**: Add support for loops, conditionals, variables
4. **Batch conversion**: Convert entire test suites
5. **Integration**: Hook into CI/CD pipeline

---

## Questions & Troubleshooting

### Q: Where is the vmcode generated?
**A**: `outputs/<QAID>/vmcode.txt` after running `autotest.py --compile-only`

### Q: How do I see what fixtures are available?
**A**: Check `output/conftest.py` and `output/.conversion_registry.json`

### Q: Can I convert multiple tests at once?
**A**: Currently manual, but you can modify `run_transpiler.py` to loop through test files

### Q: How do I debug conversion issues?
**A**: 
```bash
cd prototype/tools
python3 dsl_transpiler.py /path/to/test.txt --output-dir ../output
```

### Q: Where are the include files?
**A**: In `testcase/` directory tree. Use `find testcase -name "govdom*.txt"` to locate

---

## Summary

This migration process demonstrates:
- ✅ **DSL → vmcode** (AutoLib v3 compiler)
- ✅ **DSL → pytest** (New transpiler)
- ✅ **Include → Fixture** (Automatic conversion)
- ✅ **Registry tracking** (Reuse and dependency management)
- ✅ **Readable output** (Python code vs bytecode)

All files are accessible and documented for review and extension.
