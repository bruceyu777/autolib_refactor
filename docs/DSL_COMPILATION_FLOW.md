# DSL Compilation Flow: From Text to API Call

This document explains how AutoLib v3 transforms DSL text commands into Python API calls with parameter objects.

## Quick Example

**DSL Command:**
```
setvar -e "Serial-Number: (FGVM.*)" -to sn
```

**Becomes API Call:**
```python
setvar(executor, params)
# where params.rule = "Serial-Number: (FGVM.*)"
#   and params.name = "sn"
```

---

## The 5-Stage Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│  1. DSL TEXT                                                     │
│     setvar -e "Serial-Number: (FGVM.*)" -to sn                  │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. LEXER (Tokenization)                                         │
│     Tokens: [                                                    │
│       {type: "identifier", str: "setvar", line: 5},             │
│       {type: "identifier", str: "-e", line: 5},                 │
│       {type: "string", str: "Serial-Number: (FGVM.*)", line: 5},│
│       {type: "identifier", str: "-to", line: 5},                │
│       {type: "identifier", str: "sn", line: 5}                  │
│     ]                                                            │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. PARSER (Syntax Validation + Options Extraction)             │
│     • Looks up "setvar" in cli_syntax.json                      │
│     • Finds parse_mode: "options"                               │
│     • Calls _parse_options() to extract parameter values        │
│     • Creates VMCode: ("setvar", tuple_params)                  │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. SCHEMA MAPPING (cli_syntax.json)                            │
│     {                                                            │
│       "setvar": {                                                │
│         "parse_mode": "options",                                 │
│         "parameters": {                                          │
│           "-e": {                                                │
│             "alias": "rule",        ← Maps -e to rule           │
│             "position": 0,                                       │
│             "required": true                                     │
│           },                                                     │
│           "-to": {                                               │
│             "alias": "name",        ← Maps -to to name          │
│             "position": 1,                                       │
│             "required": true                                     │
│           }                                                      │
│         }                                                        │
│       }                                                          │
│     }                                                            │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. EXECUTION (ApiParams Wrapper)                               │
│     • execute_api("setvar", tuple_params)                       │
│     • Creates: params = ApiParams(tuple_params, schema)         │
│     • params._normalize() maps tuple → dict:                    │
│         {"rule": "Serial-Number: (FGVM.*)", "name": "sn"}      │
│     • Calls: setvar(executor, params)                           │
│     • API accesses: params.rule, params.name                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Detailed Breakdown

### Stage 1: DSL Text

The test script contains the raw text command:

```python
# In first_case.txt:
setvar -e "Serial-Number: (FGVM.*)" -to sn
```

### Stage 2: Lexer - Tokenization

**File:** `lib/core/compiler/lexer.py`

The lexer scans the text and creates tokens:

```python
def parse_line(self, line):
    # Breaks down the line into tokens
    tokens = [
        Token(type="identifier", str="setvar", line_number=5),
        Token(type="identifier", str="-e", line_number=5),
        Token(type="string", str="Serial-Number: (FGVM.*)", line_number=5),
        Token(type="identifier", str="-to", line_number=5),
        Token(type="identifier", str="sn", line_number=5),
    ]
```

### Stage 3: Parser - Options Extraction

**File:** `lib/core/compiler/parser.py`

The parser's `_parse_options()` method processes commands with `-option` syntax:

```python
def _parse_options(self, matched_rule):
    options_default, option_rule = matched_rule
    options = options_default.copy()  # Start with defaults
    command_token = self._cur_token    # "setvar"
    self._advance()
    
    # Loop through all -option value pairs
    while token.str.startswith("-"):
        option = token.str  # "-e" or "-to"
        tokens = self._extract(option_rule)  # Get ["-e", "value"]
        value = tokens[1]
        
        options[option] = value.str  # Store "-e": "Serial-Number: (FGVM.*)"
    
    # Create VMCode with parameter tuple
    self._add_vm_code(
        line_number=5,
        command="setvar",
        params=[options[k] for k in options]  # Convert to tuple
    )
```

**Result:** VMCode tuple created with ordered parameters based on schema positions.

### Stage 4: Schema Definition

**File:** `lib/core/compiler/static/cli_syntax.json`

The schema defines how CLI options map to parameter names:

```json
{
  "setvar": {
    "description": "Extract value from pattern match and set variable",
    "category": "variable",
    "parse_mode": "options",
    "parameters": {
      "-e": {
        "alias": "rule",          // -e maps to params.rule
        "type": "string",
        "position": 0,            // First parameter in tuple
        "required": true,
        "description": "Regex pattern with capture group"
      },
      "-to": {
        "alias": "name",          // -to maps to params.name
        "type": "string",
        "position": 1,            // Second parameter in tuple
        "required": true,
        "description": "Variable name to set"
      }
    }
  }
}
```

**Key Concepts:**
- **`alias`**: The Python parameter name (what appears as `params.rule`)
- **`position`**: Order in the tuple (0-indexed)
- **`parse_mode: "options"`**: Tells parser to use `_parse_options()`

### Stage 5: Execution with ApiParams

**File:** `lib/core/executor/api_manager.py` and `api_params.py`

When the VMCode executes, it calls `execute_api()`:

```python
# In api_manager.py
def execute_api(self, api_endpoint: str, parameters: Tuple):
    # parameters = ("Serial-Number: (FGVM.*)", "sn")
    
    # Load schema for this API
    schema = get_schema("setvar")  # From cli_syntax.json
    
    # Wrap tuple in ApiParams object
    params = ApiParams(parameters, schema)
    
    # Validate parameters
    params.validate()
    
    # Call the actual API function
    func = _API_REGISTRY["setvar"]  # The setvar function
    return func(executor, params)


# In api_params.py
class ApiParams:
    def __init__(self, data: Tuple, schema):
        self._raw = data  # ("Serial-Number: (FGVM.*)", "sn")
        self._schema = schema
        self._data = self._normalize(data, schema)
    
    def _normalize(self, data: Tuple, schema):
        """Convert tuple to dict using schema."""
        result = {}
        param_order = schema.get_param_order()  # ["rule", "name"]
        
        for i, param_name in enumerate(param_order):
            if i < len(data):
                result[param_name] = data[i]
        
        # result = {"rule": "Serial-Number: (FGVM.*)", "name": "sn"}
        return result
    
    def __getattr__(self, name: str):
        """Allow params.rule and params.name access."""
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"Parameter '{name}' not found")
```

**Final API Call:**

```python
# In lib/core/executor/api/variable.py
def setvar(executor, params):
    rule = params.rule   # "Serial-Number: (FGVM.*)"
    name = params.name   # "sn"
    
    rule = _normalize_regexp(params.rule)
    match, _ = executor.cur_device.expect(rule, need_clear=False)
    if match:
        value = match.group(1)  # Extract FGVMULTM25002684
        env.add_var(name, value)  # Add $sn = "FGVMULTM25002684"
```

---

## How Params Work

### Three Access Methods

The `ApiParams` class provides three ways to access parameters:

#### 1. **Attribute Access (Modern - Recommended)**
```python
def setvar(executor, params):
    rule = params.rule  # Direct attribute access
    name = params.name
```

#### 2. **Dictionary Access**
```python
def setvar(executor, params):
    rule = params["rule"]      # By alias name
    rule = params["-e"]        # By CLI option
    name = params.get("name")  # With default
```

#### 3. **Tuple Unpacking (Legacy)**
```python
def setvar(executor, params):
    (rule, name) = params  # Old style - still works
```

### Why Use ApiParams?

1. **Self-Documenting**: `params.rule` is clearer than `params[0]`
2. **Flexible**: Supports both old and new code styles
3. **Validated**: Schema validation catches errors early
4. **Type-Safe**: Can specify types in schema

---

## Common DSL Patterns

### 1. Options-Based APIs (like setvar)

**Syntax:** `command -option1 value1 -option2 value2`

```python
# DSL
setvar -e "pattern" -to varname

# Schema
"parse_mode": "options"
"parameters": {
  "-e": {"alias": "rule", "position": 0},
  "-to": {"alias": "name", "position": 1}
}

# API
def setvar(executor, params):
    rule = params.rule
    name = params.name
```

### 2. Positional APIs

**Syntax:** `command arg1 arg2 arg3`

```python
# DSL
expect "Login:" 10

# Schema
"parse_mode": "positional"
"parameters": ["pattern", "timeout"]

# API
def expect(executor, params):
    pattern = params.pattern  # Or params[0]
    timeout = params.timeout  # Or params[1]
```

### 3. Mixed APIs (Options with Defaults)

**Syntax:** `command -required value [-optional value]`

```python
# DSL
check_var -name hostname -pattern "FGT-.*" -for 801831

# Schema
"parameters": {
  "-name": {"alias": "name", "required": true},
  "-pattern": {"alias": "pattern", "required": false},
  "-for": {"alias": "qaid", "required": true}
}

# API
def check_var(executor, params):
    name = params.name
    pattern = params.get("pattern")  # May be None
    qaid = params.qaid
```

---

## Adding New DSL Commands

To add a new DSL command, you need to:

### 1. Define the API Function

Create in `lib/core/executor/api/<category>.py`:

```python
def my_command(executor, params):
    """My new command."""
    arg1 = params.arg1
    arg2 = params.get("arg2", "default")
    # Implementation...
```

### 2. Define the Schema

Add to `lib/core/compiler/static/cli_syntax.json`:

```json
{
  "my_command": {
    "description": "My new command",
    "category": "mycategory",
    "parse_mode": "options",
    "parameters": {
      "-arg1": {
        "alias": "arg1",
        "type": "string",
        "position": 0,
        "required": true,
        "description": "First argument"
      },
      "-arg2": {
        "alias": "arg2",
        "type": "string",
        "position": 1,
        "required": false,
        "default": "default",
        "description": "Optional second argument"
      }
    }
  }
}
```

### 3. Use in DSL

```python
# In test script
my_command -arg1 "value1" -arg2 "value2"
```

**That's it!** The framework automatically:
- Discovers the API function
- Loads the schema
- Parses the DSL
- Creates the params object
- Calls your function

---

## Debugging Tips

### 1. Check Parameter Names

If you get `AttributeError: Parameter 'xxx' not found`:

1. Check the schema's `alias` field matches your code
2. Verify the CLI option is defined in schema
3. Check if parameter is required or optional

### 2. View VMCode

Enable debug logging to see compiled VMCode:

```bash
python autotest.py -c test.txt -e env.conf -d
```

Look for:
```
VMCode: ("setvar", ("Serial-Number: (FGVM.*)", "sn"))
```

### 3. Inspect Params Object

Add debug logging in your API:

```python
def my_api(executor, params):
    logger.debug("Params dict: %s", params._data)
    logger.debug("Params raw: %s", params._raw)
```

---

## Summary

**The Flow:**
1. **DSL Text** → `setvar -e "pattern" -to sn`
2. **Lexer** → Tokens
3. **Parser** → Extracts options into tuple
4. **Schema** → Maps CLI options to parameter names
5. **ApiParams** → Wraps tuple, provides named access
6. **API** → Receives `params` with `.rule` and `.name`

**Key Files:**
- **Schema:** `lib/core/compiler/static/cli_syntax.json`
- **Parser:** `lib/core/compiler/parser.py`
- **Params:** `lib/core/executor/api_params.py`
- **Executor:** `lib/core/executor/api_manager.py`
- **Your API:** `lib/core/executor/api/<category>.py`

**The Magic:**
The `alias` field in the schema is what creates `params.rule` from `-e`:
```json
"-e": {"alias": "rule"}  // DSL: -e  →  Python: params.rule
```
---

## Related Documentation

- **[Compiler Deep Dive](COMPILER_DEEP_DIVE.md)**: Deep dive into lexer/parser internals, control flow compilation, and line number tracking mechanisms
- **[Executor Deep Dive](EXECUTOR_DEEP_DIVE.md)**: How VM codes are executed with program counter and if_stack
- **[Variable Usage Guide](VARIABLE_USAGE_AND_TROUBLESHOOTING.md)**: Understanding variable interpolation
- **[Include Directive](INCLUDE_DIRECTIVE.md)**: Script modularization with includes
- **[DSL to Execution Example](DSL_TO_EXECUTION_EXAMPLE.md)**: Complete walkthrough with real test case

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-18  
**Framework**: AutoLib v3 V3R10B0007