# DSL to Pytest Conversion - Quick Reference

## Conversion Workflow

### Step 1: Clean Start (Recommended)
```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype/output
make clean-conversion
```

**This removes:**
- `.conversion_registry.json` - Helper conversion tracking
- `conftest.py` - Pytest fixtures
- `testcases/helpers/` - All helper modules
- `.pytest-order.txt` - Test execution order

**Preserves:** Test files in `testcases/test_*.py`

### Step 2: Convert Group File
```bash
make convert-grp GRP=grp.ips.crit
```

**Input:**
- Group file: `/home/fosqa/autolibv3/autolib_v3/testcase/ips/grp.ips.crit`
- Env file: Specified in group file or passed via `-e` flag

**Output:**
- Test files: `testcases/test_*.py`
- Helper modules: `testcases/helpers/helper_*.py`
- Conversion registry: `.conversion_registry.json`
- Test order: `.pytest-order.txt`
- Fixtures: `conftest.py`

### Step 3: Run Tests
```bash
make test-grp GRP=grp.ips.crit
```

**Result:**
- Tests run in order from `.pytest-order.txt`
- Reports generated in `reports/`

---

## Common Scenarios

### Scenario 1: First Time Conversion
```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype/output
make clean-conversion convert-grp GRP=grp.ips.crit
make test-grp GRP=grp.ips.crit
```

### Scenario 2: Reconvert After Include Change
```bash
# DSL include file was modified
make clean-conversion
make convert-grp GRP=grp.ips.crit
```

### Scenario 3: Import Error Troubleshooting
```bash
# ImportError: cannot import name 'helper_X'
make clean-conversion
make convert-grp GRP=grp.ips.crit
make test-grp GRP=grp.ips.crit
```

### Scenario 4: Switch Group Files
```bash
# Currently using grp.ips.crit, switch to grp.ips_nat.full
make clean-conversion
make convert-grp GRP=grp.ips_nat.full
make test-grp GRP=grp.ips_nat.full
```

### Scenario 5: Complete Fresh Start
```bash
# Remove everything and start over
make clean-all
make convert-grp GRP=grp.ips.crit
make test-grp GRP=grp.ips.crit
```

---

## Cleanup Commands Comparison

| Command | Registry | conftest.py | helpers/ | Tests | Reports | Cache |
|---------|----------|-------------|----------|-------|---------|-------|
| `clean-conversion` | ✓ | ✓ | ✓ | - | - | - |
| `clean-all` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `clean-reports` | - | - | - | - | ✓ | ✓ |
| `clean` | - | - | - | - | - | ✓ |

**Legend:**
- ✓ = Removed
- \- = Preserved

---

## File Dependency Chain

```
Group File (grp.ips.crit)
    ↓
[Transpiler Reads]
    ↓
DSL Test Files + Include Files
    ↓
[Conversion Process]
    ↓
.conversion_registry.json ← Tracks which includes converted
    ↓
testcases/helpers/helper_*.py ← One module per include
    ↓
testcases/test_*.py ← Tests import helpers
    ↓
conftest.py ← Provides pytest fixtures
    ↓
.pytest-order.txt ← Defines test execution order
    ↓
[Test Execution]
    ↓
reports/ ← Test results
```

---

## Why Clean Conversion?

### The Problem
Conversion registry (`.conversion_registry.json`) caches which DSL includes have been converted to helpers. If:
- Include file content changes
- Helper generation logic improves
- Different group file uses same include names

...you may get stale helpers or import errors.

### The Solution
`make clean-conversion` removes all cached conversion state, forcing:
- Fresh helper regeneration
- Updated conftest.py
- New conversion registry
- Correct test execution order

### When NOT to Clean
If you're just:
- Re-running tests (no conversion needed)
- Debugging a specific test failure
- Viewing reports

Then `make clean-conversion` is unnecessary.

---

## Example: Full Workflow

```bash
# Navigate to output directory
cd /home/fosqa/autolibv3/autolib_v3/prototype/output

# Check what's available
make help

# Clean start
make clean-conversion

# Convert DSL to pytest
make convert-grp GRP=grp.ips.crit

# Check conversion results
make show-grp-order
make list-tests

# Run single test for verification
make test QAID=205812

# Run full suite
make test-grp GRP=grp.ips.crit

# View results
make report

# Analyze failures (if any)
make test-failed
```

---

## Troubleshooting Checklist

- [ ] Used `make clean-conversion` before converting?
- [ ] Group file path correct in convert command?
- [ ] `.conversion_registry.json` present after conversion?
- [ ] `testcases/helpers/` directory populated?
- [ ] `.pytest-order.txt` contains test order?
- [ ] `conftest.py` has fixture definition?
- [ ] Test files import from `helpers.helper_X`?
- [ ] Virtual environment activated?

---

## Documentation Files

1. **CONVERSION_GUIDE.md** - Comprehensive guide (read this first)
2. **README.md** - Quick start and overview
3. **QUICK_REFERENCE.md** - This file (command cheat sheet)

---

**Created:** February 25, 2026
**Last Updated:** February 25, 2026
