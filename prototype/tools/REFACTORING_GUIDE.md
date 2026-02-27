# DSL Transpiler - Refactored Architecture

## Overview

The DSL transpiler has been refactored using **separation of concerns** principles to improve maintainability, testability, and code clarity.

## Module Structure

### 1. **dsl_parser.py** - DSL Parsing
**Responsibility:** Parse DSL test files into structured data

**Key Classes:**
- `DSLParser`: Main parser class

**Key Methods:**
- `parse_test_file()`: Parse DSL file → structured dict
- `extract_includes()`: Extract include directives
- `resolve_include_path()`: Resolve include paths

**Input:** DSL test file (raw text)  
**Output:** Structured dictionary with qaid, title, sections, includes

---

### 2. **test_generator.py** - Test Code Generation
**Responsibility:** Generate pytest test code from parsed DSL structure

**Key Classes:**
- `TestGenerator`: Generate pytest test files

**Key Methods:**
- `generate_test_header()`: Create test file header with imports
- `generate_test_function()`: Generate complete test function
- `convert_section()`: Convert DSL section to pytest code
- `_group_commands()`: Group commands into logical blocks
- `_convert_blocks()`: Convert command blocks to Python
- `sanitize_identifier()`: Ensure valid Python identifiers

**Input:** Parsed DSL structure  
**Output:** Python test code (string)

---

### 3. **conftest_generator.py** - Conftest Generation
**Responsibility:** Generate pytest conftest.py with fixtures and hooks

**Key Classes:**
- `ConftestGenerator`: Generate conftest.py content

**Key Methods:**
- `generate_header()`: Complete conftest.py generation
- `_generate_imports()`: Import statements
- `_generate_testbed_fixture()`: Testbed fixture with env config
- `_generate_pytest_hooks()`: All pytest hooks (collection, execution, tracking)
- `_generate_logger_fixture()`: Logger fixture for tests

**Input:** Optional environment config file  
**Output:** Complete conftest.py content (string)

**Pytest Hooks Included:**
- `pytest_addoption`: Command-line options
- `pytest_collection_modifyitems`: Test ordering and filtering
- `pytest_runtest_makereport`: Outcome tracking
- `pytest_sessionfinish`: Results export and summary

---

### 4. **dsl_transpiler_refactored.py** - Main Orchestrator
**Responsibility:** Coordinate the transpilation process

**Key Classes:**
- `DSLTranspiler`: Main orchestrator

**Key Workflow:**
1. Parse DSL test (via `DSLParser`)
2. Initialize conftest.py (via `ConftestGenerator`)
3. Convert include dependencies to helpers (via `IncludeConverter`)
4. Generate pytest test file (via `TestGenerator`)
5. Update conversion registry

**Dependencies:**
- Uses `DSLParser` for parsing
- Uses `TestGenerator` for test generation
- Uses `ConftestGenerator` for conftest generation
- Uses `IncludeConverter` for helper conversion
- Uses `ConversionRegistry` for tracking

---

## Dependency Graph

```
dsl_transpiler_refactored.py (Orchestrator)
    ├── dsl_parser.py (Parsing)
    ├── test_generator.py (Test Generation)
    ├── conftest_generator.py (Conftest Generation)
    ├── include_converter.py (Helper Conversion)
    └── conversion_registry.py (Tracking)
```

## Benefits of Refactoring

### 1. **Separation of Concerns**
- Each module has a single, well-defined responsibility
- Changes to parsing don't affect test generation
- Conftest generation is completely isolated

### 2. **Testability**
- Each module can be tested independently
- Mock dependencies easily in unit tests
- Clear input/output contracts

### 3. **Maintainability**
- Smaller, focused files are easier to understand
- Related code is grouped together
- Clear module boundaries

### 4. **Reusability**
- `TestGenerator` can be used independently
- `ConftestGenerator` can generate conftest for other tools
- `DSLParser` can be used for DSL analysis tools

### 5. **Extensibility**
- Easy to add new pytest hooks (just edit `conftest_generator.py`)
- Easy to add new DSL constructs (just edit `test_generator.py`)
- Easy to change parsing logic (just edit `dsl_parser.py`)

## Migration Guide

### Old Usage (Monolithic)
```python
from dsl_transpiler import DSLTranspiler
from conversion_registry import ConversionRegistry

registry = ConversionRegistry()
transpiler = DSLTranspiler(registry)
result = transpiler.transpile(test_file, output_dir, env_file)
```

### New Usage (Refactored)
```python
from dsl_transpiler_refactored import DSLTranspiler
from conversion_registry import ConversionRegistry

registry = ConversionRegistry()
transpiler = DSLTranspiler(registry)
result = transpiler.transpile(test_file, output_dir, env_file)
```

**Note:** The public API remains the same! Only internal structure changed.

## File Sizes Comparison

| Module | Lines | Purpose |
|--------|-------|---------|
| **Old:** dsl_transpiler.py | ~1330 | Everything |
| **New:** dsl_transpiler_refactored.py | ~285 | Orchestration only |
| **New:** dsl_parser.py | ~130 | Parsing only |
| **New:** test_generator.py | ~450 | Test generation |
| **New:** conftest_generator.py | ~360 | Conftest generation |
| **Total New** | ~1225 | Sum of all modules |

## Testing Strategy

### Unit Tests (Recommended)

```python
# Test parser independently
def test_dsl_parser():
    parser = DSLParser()
    result = parser.parse_test_file(Path('test.dsl'))
    assert result['qaid'] == expected_qaid

# Test test generator independently
def test_test_generator():
    gen = TestGenerator()
    code = gen.generate_test_function(parsed_data)
    assert 'def test_' in code

# Test conftest generator independently
def test_conftest_generator():
    gen = ConftestGenerator()
    conftest = gen.generate_header(env_file)
    assert 'def testbed():' in conftest
```

## Future Enhancements

1. **Add type hints** to all modules for better IDE support
2. **Add comprehensive docstrings** with examples
3. **Create unit tests** for each module
4. **Extract constants** to configuration files
5. **Add plugin system** for custom DSL extensions

## Questions?

See the individual module files for detailed implementation notes and docstrings.
