# Compilation Workflow

## Overview

This document provides a detailed illustration of the compilation workflow for processing FortiOS automation scripts (`.fos` files) into executable VM code.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Compilation Pipeline](#compilation-pipeline)
3. [Phase 1: Lexical Analysis](#phase-1-lexical-analysis)
4. [Phase 2: Syntax Parsing](#phase-2-syntax-parsing)
5. [Phase 3: Code Generation](#phase-3-code-generation)
6. [Execution Flow](#execution-flow)
7. [Example Walkthrough](#example-walkthrough)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     COMPILATION ARCHITECTURE                     │
└─────────────────────────────────────────────────────────────────┘

Input: Script File (.fos)
   │
   ↓
┌──────────────────────┐
│   Schema Loader      │  ← cli_syntax.json (loaded once)
│   (syntax.py)        │     • 33 APIs
│                      │     • 48 Valid Commands
│   • Loads schema     │     • 12 Keywords
│   • Compiles regex   │     • Deprecated patterns
│   • Caches patterns  │
└──────────┬───────────┘
           │
           ↓
┌──────────────────────┐
│   Phase 1: LEXER     │  ← Tokenization (lexer.py)
│   (lexer.py)         │
│                      │     Input:  Raw text lines
│   • Line matching    │     Output: Token stream
│   • Token extraction │
│   • Deprecation      │     Time: 70% of compilation
│   • Section tracking │
└──────────┬───────────┘
           │
           ↓ Token Stream
           │
┌──────────────────────┐
│   Phase 2: PARSER    │  ← Syntax Analysis (parser.py)
│   (parser.py)        │
│                      │     Input:  Token stream
│   • Syntax validation│     Output: VM code list
│   • Structure analysis│
│   • Control flow     │     Time: 27% of compilation
│   • VM code emission │
└──────────┬───────────┘
           │
           ↓ VM Code List
           │
┌──────────────────────┐
│  Phase 3: VM CODES   │  ← Intermediate Representation
│  (vm_code.py)        │
│                      │     Input:  VM codes
│   • Operation codes  │     Output: Executable instructions
│   • Parameters       │
│   • Line numbers     │     Time: < 1% of compilation
│   • Schema binding   │
└──────────┬───────────┘
           │
           ↓
Output: VM Code List + Metadata
   │
   ├─→ VM Codes: List[VMCode]
   ├─→ Devices: Set[str] (sections discovered)
   └─→ Called Files: Set[tuple] (includes)
```

---

## Compilation Pipeline

### High-Level Flow

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   .fos      │─────→│   Lexer     │─────→│   Parser    │
│   File      │      │  (Tokens)   │      │ (VM Codes)  │
└─────────────┘      └─────────────┘      └─────────────┘
                             │                    │
                             ↓                    ↓
                      [Token Stream]      [VMCode List]
                       • type             • operation
                       • str              • parameters
                       • line_number      • line_number
```

### Entry Point

```python
# Main compilation entry point
from lib.core.compiler.lexer import Lexer
from lib.core.compiler.parser import Parser

# Step 1: Tokenize
lexer = Lexer("script.fos")
tokens, lines = lexer.parse()

# Step 2: Parse
parser = Parser("script.fos", tokens, lines)
vm_codes, devices, called_files = parser.run()

# Step 3: Execute (via executor)
# See lib/core/executor/ for execution phase
```

---

## Phase 1: Lexical Analysis

### Purpose

Convert raw text into a stream of tokens that represent syntactic elements.

### Input/Output

**Input**: Raw script file

```
[FGT1]
<setvar ip "192.168.1.1">
<expect -e "login:" -for QA001 -t 10>
config system global
    set hostname test-fgt
end
```

**Output**: Token stream

```python
[
    Token(type="section", str="FGT1", line_number=1),
    Token(type="api", str="setvar", line_number=2),
    Token(type="identifier", str="ip", line_number=2),
    Token(type="string", str="192.168.1.1", line_number=2),
    Token(type="api", str="expect", line_number=3),
    Token(type="identifier", str="-e", line_number=3),
    Token(type="string", str="login:", line_number=3),
    # ... more tokens
]
```

### Process Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        LEXER PROCESS FLOW                        │
└─────────────────────────────────────────────────────────────────┘

1. READ FILE
   ↓
   read() → Detect encoding (chardet) → Decode content
   ↓
   Split into lines

2. FOR EACH LINE:
   ↓
   update_deprecated_command(line)
   ↓
   ┌─────────────────────────────────────┐
   │ OPTIMIZATION: Fast Path             │
   │ Check prefix → 95% early exit       │
   │ Only regex match if prefix matches  │
   └─────────────────────────────────────┘
   ↓
   parse_line(line)
   ↓
   ┌────────────────────────────────────────────────────────┐
   │ LINE PATTERN MATCHING                                  │
   │                                                         │
   │ Match against line_pattern (compiled regex):           │
   │   • commented_section: #\s*\[[A-Z_0-9]+\]             │
   │   • commented_line:    #.*                             │
   │   • section:           \[(?P<section_name>[A-Z_0-9]+)\]│
   │   • statement:         \<\s*(?P<content>if|loop|...)  │
   │   • comment:           [Cc]omment[s]*\s*:*\s*(.*)     │
   │   • include:           include\s+(?P<file_name>.+)    │
   │   • api:               (generated from schema)         │
   │   • command:           .+  (fallback)                  │
   └────────────────────────────────────────────────────────┘
   ↓
   Matched line type → groupdict
   ↓
   _process_matched_line_types()
   ↓
   ┌────────────────────────────────────────────┐
   │ DISPATCH TO LINE TYPE HANDLER              │
   │                                            │
   │ section()     → add_token("section", ...)  │
   │ api()         → _parse_with_leftover(...)  │
   │ command()     → add_token("command", ...)  │
   │ statement()   → tokenize keywords          │
   │ comment()     → add_token("comment", ...)  │
   │ include()     → add_token("include", ...)  │
   └────────────────────────────────────────────┘
   ↓
   FOR API/STATEMENT LINES: tokenize(remaining_content)
   ↓
   ┌────────────────────────────────────────────┐
   │ TOKEN PATTERN MATCHING                     │
   │                                            │
   │ Match against token_pattern:               │
   │   • variable:       \$(?P<name>[^\s]+)    │
   │   • symbol:         ==|[-()[\]{}<>+*\/=]  │
   │   • number:         (?P<content>\d+)      │
   │   • operator:       eq|ne|lt               │
   │   • string:         "(?:\"|[^"\\]|\\.)*?" │
   │   • identifier:     .+?                    │
   └────────────────────────────────────────────┘
   ↓
   add_token(type, data) → Token object created

3. RETURN
   ↓
   (tokens, lines)
```

### Key Components

#### 1. Line Pattern Matching

```python
# Generated from schema at initialization
line_pattern = re.compile(
    r"(?P<commented_section>#\s*\[[A-Z_0-9]+\])|"
    r"(?P<commented_line>#.*)|"
    r"(?P<section>\[(?P<section_name>[A-Z_0-9]+)\])|"
    r"(?P<statement>\<\s*(?P<statement_content>(if|loop|...).*)>)|"
    r"(?P<comment>[Cc]omment[s]*\s*:*\s*(?P<comment_content>.*))|"
    r"(?P<include>include\s+(?P<file_name>.+))|"
    r"(?P<api>setvar\s+.+|expect\s+.+|...)|"  # Generated from APIs
    r"(?P<command>.+)"  # Fallback
)
```

#### 2. Token Extraction

```python
# Example: API line
"<expect -e \"login:\" -for QA001 -t 10>"

# Step 1: Match line pattern → type="api", str="expect -e \"login:\" -for QA001 -t 10"
# Step 2: _parse_with_leftover()
#   → first token: "expect" (api)
#   → leftover: "-e \"login:\" -for QA001 -t 10"
# Step 3: tokenize(leftover)
#   → Token(identifier, "-e")
#   → Token(string, "login:")
#   → Token(identifier, "-for")
#   → Token(identifier, "QA001")
#   → Token(identifier, "-t")
#   → Token(number, "10")
```

#### 3. Deprecated Command Handling (OPTIMIZED)

```python
# Fast path (95% of lines)
if not any(cmd.startswith(prefix) for prefix in self._deprecated_prefixes):
    return cmd  # Early exit - no regex matching

# Slow path (only if prefix matches)
for pattern, replacement in self._deprecated_patterns:
    updated_cmd = pattern.sub(replacement, cmd)
    if updated_cmd != cmd:
        log_warning(...)
        return updated_cmd
```

### Performance Characteristics

- **Time**: 70% of total compilation time
- **Bottlenecks**: Regex matching (optimized with caching and early exit)
- **Speed**: ~0.1ms per script (10-20 lines)
- **Memory**: ~48 bytes per token

---

## Phase 2: Syntax Parsing

### Purpose

Validate token stream against grammar rules and generate executable VM code.

### Input/Output

**Input**: Token stream

```python
[
    Token(type="section", str="FGT1", line_number=1),
    Token(type="api", str="expect", line_number=2),
    Token(type="identifier", str="-e", line_number=2),
    Token(type="string", str="login:", line_number=2),
    # ...
]
```

**Output**: VM code list

```python
[
    VMCode(line_number=1, operation="switch_device", parameters=("FGT1",)),
    VMCode(line_number=2, operation="expect", parameters=("login:", "QA001", "10")),
    # ...
]
```

### Process Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                       PARSER PROCESS FLOW                        │
└─────────────────────────────────────────────────────────────────┘

1. INITIALIZATION
   ↓
   Parser(file_name, tokens, lines)
   ↓
   cursor = 0  (token position)
   vm_codes = []
   devices = set()
   called_files = set()

2. MAIN LOOP: while cur_token is not None
   ↓
   _script()  ← Main dispatch method
   ↓
   ┌─────────────────────────────────────────────────────────┐
   │ IDENTIFY TOKEN CATEGORY                                 │
   │                                                          │
   │ if token.type in ["api", "keyword"]:                    │
   │     → Top-level category (needs syntax lookup)          │
   │     → get_token_syntax_definition(token)                │
   │     ↓                                                    │
   │     Returns: (operation, matched_rule)                  │
   │       • operation: "parse", "parse_options",            │
   │                    "control_block"                       │
   │       • matched_rule: Expected token pattern            │
   │     ↓                                                    │
   │     Dispatch: _parse() or _parse_options()              │
   │               or _control_block()                        │
   │ else:                                                    │
   │     → Simple type (section, command, comment, include)  │
   │     → Direct handler: _section(), _command(), etc.      │
   └─────────────────────────────────────────────────────────┘
   ↓
   advance cursor

3. SYNTAX DEFINITION LOOKUP
   ↓
   get_token_syntax_definition(token)
   ↓
   ┌──────────────────────────────────────────────────────────┐
   │ SCHEMA-DRIVEN SYNTAX EXTRACTION                          │
   │                                                           │
   │ if token.type == "api":                                  │
   │     api_schema = schema["apis"][token.str]               │
   │     parse_mode = api_schema["parse_mode"]                │
   │     ↓                                                     │
   │     if parse_mode == "options":                          │
   │         Build options_dict from parameters               │
   │         Return ("parse_options", [options_dict, rules])  │
   │     ↓                                                     │
   │     if parse_mode == "positional":                       │
   │         Build param_rules from parameters                │
   │         Return ("parse", [param_rules])                  │
   │                                                           │
   │ elif token.type == "keyword":                            │
   │     keyword_def = schema["keywords"][token.str]          │
   │     ↓                                                     │
   │     if keyword_def["type"] == "control_block":           │
   │         Return ("control_block", keyword_def["flow"])    │
   │     ↓                                                     │
   │     if keyword_def["type"] == "parse":                   │
   │         Return ("parse", keyword_def["rules"])           │
   └──────────────────────────────────────────────────────────┘

4. PARSE OPERATIONS
   ↓
   ┌──────────────────────────────────────────────────────────┐
   │ A. _parse(expected_tokens)                               │
   │    Used for: Positional APIs, keywords                   │
   │    ↓                                                      │
   │    Extract tokens according to expected pattern          │
   │    expected_tokens = [                                   │
   │        [["identifier"], None],  # First param            │
   │        [["number"], None]       # Second param           │
   │    ]                                                      │
   │    ↓                                                      │
   │    _extract(expected_tokens)                             │
   │    ↓                                                      │
   │    FOR EACH expected_token:                              │
   │        _parse_token(expected_type, expected_str)         │
   │        ↓                                                  │
   │        Validate: token.type matches expected_type        │
   │        Validate: same line number (no cross-line parse)  │
   │        ↓                                                  │
   │        Collect token                                     │
   │    ↓                                                      │
   │    _add_vm_code(operation, [params])                     │
   │                                                           │
   │ B. _parse_options(matched_rule)                          │
   │    Used for: Option-based APIs (expect, sendline, etc.)  │
   │    ↓                                                      │
   │    options_default = {"-e": None, "-for": None, ...}    │
   │    ↓                                                      │
   │    WHILE token.str.startswith("-"):                      │
   │        option = token.str  # e.g., "-e"                  │
   │        Extract: [option_flag, value]                     │
   │        ↓                                                  │
   │        options[option] = value                           │
   │    ↓                                                      │
   │    _add_vm_code(operation, [options.values()])           │
   │                                                           │
   │ C. _control_block(exp_stats)                             │
   │    Used for: if/else/loop/until control structures       │
   │    ↓                                                      │
   │    exp_stats = ["expression", "script", ["elseif",       │
   │                 "else", "fi"]]                            │
   │    ↓                                                      │
   │    FOR EACH exp_stat:                                    │
   │        if exp_stat == "expression":                      │
   │            _expression() → collect tokens                │
   │        elif exp_stat == "script":                        │
   │            WHILE not end_of_block:                       │
   │                _script() (recursive)                     │
   │        else: # Nested control (elseif, else, fi)         │
   │            _control_block(next_exp_stats) (recursive)    │
   └──────────────────────────────────────────────────────────┘

5. VM CODE EMISSION
   ↓
   _add_vm_code(line_number, operation, parameters)
   ↓
   VMCode(line_number, operation, parameters)
   ↓
   Append to vm_codes list

6. RETURN
   ↓
   (vm_codes, devices, called_files)
```

### Parsing Examples

#### Example 1: Positional API

```python
# Input tokens
[Token(api, "setvar"), Token(identifier, "ip"), Token(string, "192.168.1.1")]

# Syntax definition (from schema)
{
    "setvar": {
        "parse_mode": "positional",
        "parameters": [
            {"name": "var_name", "type": "string", "position": 0},
            {"name": "value", "type": "string", "position": 1}
        ]
    }
}

# Parser action
get_token_syntax_definition(Token(api, "setvar"))
  → ("parse", [[["identifier"], None], [["string"], None]])

_parse([[["identifier"], None], [["string"], None]])
  → Extract: Token(identifier, "ip"), Token(string, "192.168.1.1")
  → _add_vm_code(2, "setvar", ["ip", "192.168.1.1"])

# Output
VMCode(line_number=2, operation="setvar", parameters=("ip", "192.168.1.1"))
```

#### Example 2: Options API

```python
# Input tokens
[Token(api, "expect"), Token(identifier, "-e"), Token(string, "login:"),
 Token(identifier, "-for"), Token(identifier, "QA001"),
 Token(identifier, "-t"), Token(number, "10")]

# Syntax definition (from schema)
{
    "expect": {
        "parse_mode": "options",
        "parameters": {
            "-e": {"alias": "rule", "default": None},
            "-for": {"alias": "qaid", "default": None},
            "-t": {"alias": "wait_seconds", "default": 5}
        }
    }
}

# Parser action
get_token_syntax_definition(Token(api, "expect"))
  → ("parse_options", [{"-e": None, "-for": None, "-t": 5}, rules])

_parse_options([{"-e": None, "-for": None, "-t": 5}, rules])
  → Extract: -e → "login:", -for → "QA001", -t → "10"
  → options = {"-e": "login:", "-for": "QA001", "-t": "10"}
  → _add_vm_code(3, "expect", ["login:", "QA001", "10"])

# Output
VMCode(line_number=3, operation="expect", parameters=("login:", "QA001", "10"))
```

#### Example 3: Control Block (if/else/fi)

```python
# Input tokens
[Token(keyword, "if"), Token(variable, "status"), Token(operator, "=="),
 Token(number, "0"), Token(api, "report"), Token(identifier, "-qaid"),
 Token(identifier, "PASS"), Token(keyword, "else"), Token(api, "report"),
 Token(identifier, "-qaid"), Token(identifier, "FAIL"), Token(keyword, "fi")]

# Syntax definition (from schema)
{
    "if": {
        "type": "control_block",
        "flow": ["expression", "script", ["elseif", "else", "fi"]]
    }
}

# Parser action
_control_block(["expression", "script", ["elseif", "else", "fi"]])
  ↓
  _if() → VMCode(5, "if_not_goto", ())  # Jump target filled later
  ↓
  "expression": _expression() → ["status", "==", "0"]
    → Add to VMCode parameters: (..., "status", "==", "0")
  ↓
  "script": WHILE not keyword in ["elseif", "else", "fi"]:
    → _script() (parse "report" API)
    → VMCode(6, "report", ["PASS"])
  ↓
  "else": _else(prev_vm_code)
    → prev_vm_code.add_parameter(7)  # if jumps to line 7
    → VMCode(7, "else", ())
  ↓
  "script": WHILE not keyword "fi":
    → _script() (parse "report" API)
    → VMCode(8, "report", ["FAIL"])
  ↓
  "fi": _fi(prev_vm_code)
    → prev_vm_code.add_parameter(9)  # else jumps to line 9
    → VMCode(9, "endif", ())

# Output
[
    VMCode(5, "if_not_goto", ("status", "==", "0", 7)),  # If false, goto line 7
    VMCode(6, "report", ("PASS",)),
    VMCode(7, "else", (9,)),  # Jump to line 9 after if-block
    VMCode(8, "report", ("FAIL",)),
    VMCode(9, "endif", ())
]
```

### Performance Characteristics

- **Time**: 27% of total compilation time
- **Bottlenecks**: Token extraction, validation
- **Speed**: ~0.04ms per script
- **Memory**: ~96 bytes per VM code

---

## Phase 3: Code Generation

### Purpose

Create intermediate representation (VM codes) that can be executed by the runtime.

### VMCode Structure

```python
class VMCode:
    """
    Intermediate representation of a script operation.

    Attributes:
        line_number (int): Source line number (for debugging)
        operation (str): Operation name (API name or control flow op)
        parameters (tuple): Operation parameters (positional or extracted from options)
        _schema (APISchema): Optional schema reference for validation
    """

    def __init__(self, line_number, operation, parameters, schema=None):
        self.line_number = line_number
        self.operation = operation
        self.parameters = parameters
        self._schema = schema
```

### VM Code Types

```
┌────────────────────────────────────────────────────────────────┐
│                        VM CODE TYPES                            │
└────────────────────────────────────────────────────────────────┘

1. DEVICE OPERATIONS
   • switch_device(device_name)
     Example: VMCode(1, "switch_device", ("FGT1",))
     Purpose: Switch execution context to device section

2. API OPERATIONS
   • API_NAME(param1, param2, ...)
     Example: VMCode(5, "expect", ("login:", "QA001", 10))
     Purpose: Execute API with parameters
     Note: Parameters extracted from options or positional args

3. CONTROL FLOW
   • if_not_goto(condition..., jump_target)
     Example: VMCode(10, "if_not_goto", ("$x", "==", "0", 15))
     Purpose: Conditional jump (if condition false, goto line 15)

   • elseif(jump_target)
     Example: VMCode(12, "elseif", (18,))
     Purpose: Else-if branch

   • else(jump_target)
     Example: VMCode(15, "else", (20,))
     Purpose: Else branch

   • endif()
     Example: VMCode(20, "endif", ())
     Purpose: End of if block

   • loop()
     Example: VMCode(25, "loop", ())
     Purpose: Start of loop

   • until(loop_start_line)
     Example: VMCode(30, "until", (25,))
     Purpose: Loop back to line 25 if condition true

4. COMMANDS
   • command(command_string)
     Example: VMCode(8, "command", ("config system global",))
     Purpose: Execute FortiOS CLI command

5. METADATA
   • comment(comment_text)
     Example: VMCode(3, "comment", ("This is a test",))
     Purpose: Documentation (no execution)

   • include(file_name)
     Example: VMCode(7, "include", ("common_setup.fos",))
     Purpose: Include another script file
```

### Schema Binding

```python
# VMCode can be bound to schema for parameter validation
vm_code = VMCode(5, "expect", ("login:", "QA001", 10))

# Get schema
schema = vm_code.get_schema()  # Returns APISchema for "expect"

# Convert to ApiParams for modern API access
params = vm_code.as_params()  # Returns ApiParams instance

# Access parameters with schema validation
params.rule         # "login:" (validated as string)
params.qaid         # "QA001" (validated as string)
params.wait_seconds # 10 (validated and cast to int)
```

---

## Execution Flow

### From Compilation to Execution

```
┌─────────────────────────────────────────────────────────────────┐
│                  COMPILATION → EXECUTION FLOW                    │
└─────────────────────────────────────────────────────────────────┘

1. COMPILE SCRIPT
   ↓
   lexer = Lexer("script.fos")
   tokens, lines = lexer.parse()
   ↓
   parser = Parser("script.fos", tokens, lines)
   vm_codes, devices, called_files = parser.run()
   ↓
   [VMCode list ready for execution]

2. EXECUTION SETUP (lib/core/executor/)
   ↓
   executor = ScriptExecutor()
   executor.load_vm_codes(vm_codes)
   ↓
   executor.set_devices(devices)

3. EXECUTION LOOP
   ↓
   FOR EACH vm_code in vm_codes:
       ↓
       operation = vm_code.operation
       parameters = vm_code.parameters
       ↓
       ┌──────────────────────────────────────────────┐
       │ DISPATCH TO API HANDLER                      │
       │                                              │
       │ if operation == "switch_device":             │
       │     executor.switch_device(parameters[0])    │
       │                                              │
       │ elif operation in API_REGISTRY:              │
       │     api_func = API_REGISTRY[operation]       │
       │     params = vm_code.as_params()             │
       │     api_func(executor, params)               │
       │     ↓                                         │
       │     # API has schema-validated access        │
       │     # params.rule, params.qaid, etc.         │
       │                                              │
       │ elif operation == "command":                 │
       │     executor.send_command(parameters[0])     │
       │                                              │
       │ elif operation == "if_not_goto":             │
       │     condition = parameters[:-1]              │
       │     jump_target = parameters[-1]             │
       │     if not evaluate(condition):              │
       │         executor.goto(jump_target)           │
       │                                              │
       │ elif operation == "loop":                    │
       │     executor.mark_loop_start()               │
       │                                              │
       │ elif operation == "until":                   │
       │     loop_start = parameters[0]               │
       │     if evaluate_condition():                 │
       │         executor.goto(loop_start)            │
       └──────────────────────────────────────────────┘

4. API EXECUTION
   ↓
   def expect(executor, params):
       rule = params.rule          # From schema: "-e" option
       qaid = params.qaid          # From schema: "-for" option
       timeout = params.wait_seconds  # From schema: "-t" option (int)
       ↓
       # Execute pexpect logic
       executor.device.expect(rule, timeout=timeout)
       ↓
       # Report result
       if qaid:
           executor.report(qaid, "pass")
```

---

## Example Walkthrough

### Complete Example: Login Script

#### Input Script (`login.fos`)

```
[FGT1]
<setvar username "admin">
<setvar password "fortinet">
<expect -e "login:" -for QA001 -t 30>
<sendline -line $username -for QA002>
<expect -e "Password:" -for QA003 -t 10>
<sendline -line $password -for QA004>
<expect -e "#" -for QA005 -t 10>
<if $? == 0>
    <report -qaid QA100 -result pass>
<else>
    <report -qaid QA100 -result fail>
<fi>
config system global
    set hostname test-device
end
```

#### Step 1: Lexer Output (Tokens)

```python
[
    # Line 1
    Token(type="section", str="FGT1", line_number=1),

    # Line 2
    Token(type="api", str="setvar", line_number=2),
    Token(type="identifier", str="username", line_number=2),
    Token(type="string", str="admin", line_number=2),

    # Line 3
    Token(type="api", str="setvar", line_number=3),
    Token(type="identifier", str="password", line_number=3),
    Token(type="string", str="fortinet", line_number=3),

    # Line 4
    Token(type="api", str="expect", line_number=4),
    Token(type="identifier", str="-e", line_number=4),
    Token(type="string", str="login:", line_number=4),
    Token(type="identifier", str="-for", line_number=4),
    Token(type="identifier", str="QA001", line_number=4),
    Token(type="identifier", str="-t", line_number=4),
    Token(type="number", str="30", line_number=4),

    # Line 5
    Token(type="api", str="sendline", line_number=5),
    Token(type="identifier", str="-line", line_number=5),
    Token(type="variable", str="username", line_number=5),
    Token(type="identifier", str="-for", line_number=5),
    Token(type="identifier", str="QA002", line_number=5),

    # ... more tokens for lines 6-16
]
```

#### Step 2: Parser Output (VM Codes)

```python
[
    # Line 1: Section
    VMCode(line_number=1, operation="switch_device", parameters=("FGT1",)),

    # Line 2: setvar (positional API)
    VMCode(line_number=2, operation="setvar", parameters=("username", "admin")),

    # Line 3: setvar (positional API)
    VMCode(line_number=3, operation="setvar", parameters=("password", "fortinet")),

    # Line 4: expect (options API)
    VMCode(line_number=4, operation="expect", parameters=("login:", "QA001", 30)),

    # Line 5: sendline (options API)
    VMCode(line_number=5, operation="sendline", parameters=("$username", "QA002")),

    # Line 6: expect
    VMCode(line_number=6, operation="expect", parameters=("Password:", "QA003", 10)),

    # Line 7: sendline
    VMCode(line_number=7, operation="sendline", parameters=("$password", "QA004")),

    # Line 8: expect
    VMCode(line_number=8, operation="expect", parameters=("#", "QA005", 10)),

    # Line 9: if block start
    VMCode(line_number=9, operation="if_not_goto", parameters=("$?", "==", "0", 11)),

    # Line 10: report (inside if)
    VMCode(line_number=10, operation="report", parameters=("QA100", "pass")),

    # Line 11: else
    VMCode(line_number=11, operation="else", parameters=(13,)),

    # Line 12: report (inside else)
    VMCode(line_number=12, operation="report", parameters=("QA100", "fail")),

    # Line 13: endif
    VMCode(line_number=13, operation="endif", parameters=()),

    # Line 14-16: FortiOS commands
    VMCode(line_number=14, operation="command", parameters=("config system global",)),
    VMCode(line_number=15, operation="command", parameters=("set hostname test-device",)),
    VMCode(line_number=16, operation="command", parameters=("end",)),
]
```

#### Step 3: Execution Trace

```
Time  Line  Operation         Parameters                    Action
─────────────────────────────────────────────────────────────────────
0ms   1     switch_device     ("FGT1",)                    → Connect to FGT1
1ms   2     setvar            ("username", "admin")        → Set $username
2ms   3     setvar            ("password", "fortinet")     → Set $password
3ms   4     expect            ("login:", "QA001", 30)      → Wait for "login:"
500ms                                                       → Matched! QA001:PASS
501ms 5     sendline          ("admin", "QA002")           → Send "admin"
                                                            → (variable expanded)
550ms                                                       → Sent! QA002:PASS
551ms 6     expect            ("Password:", "QA003", 10)   → Wait for "Password:"
700ms                                                       → Matched! QA003:PASS
701ms 7     sendline          ("fortinet", "QA004")        → Send "fortinet"
                                                            → (variable expanded)
750ms                                                       → Sent! QA004:PASS
751ms 8     expect            ("#", "QA005", 10)           → Wait for "#"
850ms                                                       → Matched! QA005:PASS
                                                            → Set $? = 0
851ms 9     if_not_goto       ("$?", "==", "0", 11)        → Evaluate $? == 0
                                                            → TRUE, continue
852ms 10    report            ("QA100", "pass")            → QA100:PASS reported
853ms 11    else              (13,)                        → Jump to line 13
854ms 13    endif             ()                           → End if block
855ms 14    command           ("config system global",)    → Send to device
900ms 15    command           ("set hostname...",)          → Send to device
950ms 16    command           ("end",)                     → Send to device
1000ms                                                      → Script complete!
```

---

## Performance Characteristics

### Compilation Performance (100 scripts)

- **Total time**: 14ms (after optimization)
- **Lexer**: 9ms (70%)
- **Parser**: 4ms (27%)
- **Schema loading**: 0.156ms (1%)
- **Throughput**: 7,347 scripts/second

### Memory Usage

- **Lexer instance**: ~1KB
- **Token**: ~48 bytes each
- **Parser instance**: ~1KB
- **VMCode**: ~96 bytes each
- **Total for typical script**: ~5KB

### Scalability

- **Linear scaling**: O(n) with script count
- **100 scripts**: 14ms
- **500 scripts**: 70ms
- **1,000 scripts**: 140ms

---

## Key Optimizations

### 1. Schema Loading

- ✅ Singleton instance (loaded once)
- ✅ Compiled regex patterns (cached)
- ✅ Fast schema lookups (dict-based)

### 2. Lexer

- ✅ Deprecated pattern caching (pre-compiled)
- ✅ Early exit optimization (prefix check)
- ✅ Compiled regex patterns (reused)

### 3. Parser

- ✅ Valid commands tuple caching
- ✅ Direct token access (cursor-based)
- ✅ Minimal object creation

### 4. Schema-Driven Design

- ✅ Zero hardcoded data in Python
- ✅ Single source of truth (cli_syntax.json)
- ✅ Dynamic pattern generation
- ✅ Declarative configuration

---

## Related Files

### Core Compiler Files

- `lexer.py` - Lexical analysis (tokenization)
- `parser.py` - Syntax analysis (parsing)
- `syntax.py` - Schema loader and pattern generator
- `vm_code.py` - Intermediate representation
- `schema_loader.py` - Schema registry and validation

### Schema File

- `static/cli_syntax.json` - Unified schema (single source of truth)

### Execution Files (separate package)

- `lib/core/executor/api_manager.py` - API dispatcher
- `lib/core/executor/api_params.py` - Parameter adapter
- `lib/core/executor/apis/*.py` - API implementations

### Documentation

- `UNIFIED_SCHEMA_COMPLETE.md` - Schema architecture
- `PARSER_REFACTORING_COMPLETE.md` - Parser refactoring
- `PERFORMANCE_ANALYSIS.md` - Performance analysis
- `PERFORMANCE_OPTIMIZATION_RESULTS.md` - Optimization results
- `COMPILER_PERFORMANCE_SUMMARY.md` - Performance summary
- `COMPILATION_WORKFLOW.md` - This document

---

**Last Updated**: 2025-10-08
**Version**: 2.0 (Unified Schema Architecture)
**Status**: Production Ready
