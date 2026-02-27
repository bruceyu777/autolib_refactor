# DSL to Pytest Transpiler - Unified Structure

## Directory Structure

```
prototype/
├── output/
│   ├── conftest.py                 # Shared pytest fixtures for all tests
│   ├── .conversion_registry.json   # Tracks converted includes
│   └── testcases/                  # All generated test files
│       ├── test__205812.py
│       ├── test__205924.py
│       └── ...
├── fluent_api/                     # Fluent API implementation
├── tools/
│   └── dsl_transpiler.py          # Unified transpiler
└── sample_includes/               # Sample include files

```

## Unified Transpilation Process

The transpiler now handles **both normal DSL tests and control-flow DSL tests** with a single, unified conversion process.

### Features Supported

#### Normal DSL Features
- Device sections ([FGT_A], [PC_02], etc.)
- Command execution
- Pattern matching (expect)
- Include files → pytest fixtures
- Environment variables

#### Control Flow Features  
- `<if>` / `<else>` / `<fi>` blocks
- `<while>` / `<done>` loops
- Variable management (intset, strset, intchange)
- Nested control structures
- DEVICE:VARIABLE conditions

### Usage

Convert any DSL test (with or without control flow):

```bash
# From prototype directory
python3 tools/dsl_transpiler.py ../testcase/ips/topology1/205812.txt --output-dir output
python3 tools/dsl_transpiler.py ../testcase/ips/topology1/205924.txt --output-dir output
```

Output:
- Test file → `output/testcases/test__<qaid>.py`
- Shared conftest → `output/conftest.py`
- Registry → `output/.conversion_registry.json`

### Running Tests

```bash
cd output
source ../../venv/bin/activate

# Run all tests
pytest testcases/ -v

# Run specific test
pytest testcases/test__205812.py -vs
pytest testcases/test__205924.py -vs
```

### Import Path Resolution

All generated tests use the same import structure:
```python
# Add fluent API to path (go up to prototype directory)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'fluent_api'))
```

This works because:
- Tests are in: `prototype/output/testcases/test__*.py`
- Fluent API is in: `prototype/fluent_api/`
- Path goes: `testcases/ → output/ → prototype/ → fluent_api/`

### Shared Conftest

The `output/conftest.py` file contains:
- `testbed` fixture (with mock device support)
- All converted include fixtures (e.g., `setup_govdom1`, `cleanup_outvdom`)
- Environment configuration (from env files)

All tests in `testcases/` automatically use these shared fixtures.

