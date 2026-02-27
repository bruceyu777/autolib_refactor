# Compiler Deep Dive - DSL to VM Code Conversion

**Module**: `lib/core/compiler/`  
**Version**: AutoLib v3 V3R10B0007  
**Purpose**: Understand how DSL is compiled to VM codes, especially control flow and line number tracking

---

## Table of Contents

1. [Compilation Architecture](#compilation-architecture)
2. [Lexical Analysis (Tokenization)](#lexical-analysis-tokenization)
3. [Syntax-Driven Parsing](#syntax-driven-parsing)
4. [Control Flow Compilation](#control-flow-compilation)
5. [Line Number Tracking](#line-number-tracking)
6. [VM Code Generation](#vm-code-generation)
7. [Real Compilation Examples](#real-compilation-examples)
8. [Schema-Driven System](#schema-driven-system)

---

## Compilation Architecture

### Three-Phase Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                   PHASE 1: LEXICAL ANALYSIS                 │
│  DSL Source → Tokens (with types and line numbers)          │
│  File: lexer.py                                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   PHASE 2: SYNTAX PARSING                   │
│  Tokens → VM Codes (with jump targets and parameters)       │
│  File: parser.py                                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   PHASE 3: EXECUTION                        │
│  VM Codes → Device Commands → Results                       │
│  File: executor.py (covered in EXECUTOR_DEEP_DIVE.md)       │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | File | Responsibility |
|-----------|------|----------------|
| **Lexer** | `lexer.py` | Tokenize DSL into typed tokens with line numbers |
| **Parser** | `parser.py` | Convert tokens to VM codes using syntax rules |
| **Syntax** | `syntax.py` | Load and manage syntax definitions from schema |
| **Schema** | `cli_syntax.json` | Define APIs, keywords, control flow patterns |
| **VMCode** | `vm_code.py` | VM instruction data structure |
| **Compiler** | `compiler.py` | Orchestrate compilation with caching |
| **Script** | `script.py` | Compiled script container |

---

## Lexical Analysis (Tokenization)

### Token Structure

```python
class Token(dict):
    def __init__(self, _type, data, line_number):
        self._type = _type        # Token type: section, command, api, keyword, etc.
        self._data = data         # Token content (actual string)
        self._line_number = line_number  # Source file line number (1-based)
```

**Example**:
```python
Token(
    _type="keyword",
    data="if",
    line_number=15
)
```

### Lexer Pattern Matching

**File**: `lexer.py`

The lexer uses **regex patterns** defined in `syntax.py` to match different line types:

```python
LINE_PATTERN_TABLE = {
    "commented_section": r"#\s*\[[A-Z_0-9]+\]",
    "commented_line": r"#.*",
    "section": r"\[(?P<section_name>[A-Z_0-9]+)\]",
    "statement": "<GENERATED>",  # From keywords in schema
    "comment": r"[Cc]omment[s]*\s*:*\s*(?P<comment_content>.*)",
    "include": r"include\s+(?P<file_name>.+)",
    "api": "<GENERATED>",  # From APIs in schema
    "command": r".+",  # Catch-all (lowest priority)
}
```

### Tokenization Process

**Step 1: Line Type Detection**

```python
def parse_line(self, line):
    self.cur_line = rf"{line}"
    match = script_syntax.line_pattern.match(self.cur_line)
    self.cur_groupdict = match.groupdict()
    
    # Process matched line type
    for line_type, matched_content in self.cur_groupdict.items():
        if matched_content:
            handler = getattr(self, line_type)
            handler()  # e.g., self.section(), self.api(), etc.
```

**Step 2: Token Generation**

Each handler creates tokens based on matched content:

```python
def section(self):
    """Handle [DEVICE_NAME] section headers."""
    section_name = self.cur_groupdict["section_name"]
    self.add_token("section", section_name)

def api(self):
    """Handle API calls (e.g., expect, setvar)."""
    self._parse_with_leftover("api", self.cur_line)

def statement(self):
    """Handle keywords (e.g., <if>, <while>, <strset>)."""
    content = self.cur_groupdict["statement_content"].strip()
    # Parse keyword and tokenize remaining content
    match = re.match(r"(?P<first>.+?)\s+(?P<leftover>.+)|(?P<second>.+)$", content)
    # ... tokenize keyword + leftover
```

### Real Tokenization Example

**DSL Source** (line 15):
```plaintext
<if {$platform_type} eq FortiGate-VM64>
```

**Tokenization Steps**:

1. **Line Match**: `statement` pattern matches `<if ...>`
2. **Extract Content**: `"if {$platform_type} eq FortiGate-VM64"`
3. **Parse Keyword**: `"if"` → Token(`keyword`, `"if"`, `15`)
4. **Tokenize Leftover**: `"{$platform_type} eq FortiGate-VM64"`
   - `{$platform_type}` → Token(`variable`, `"platform_type"`, `15`)
   - `eq` → Token(`operator`, `"eq"`, `15`)
   - `FortiGate-VM64` → Token(`identifier`, `"FortiGate-VM64"`, `15`)

**Result**: 4 tokens, all with `line_number=15`

```python
[
    Token("keyword", "if", 15),
    Token("variable", "platform_type", 15),
    Token("operator", "eq", 15),
    Token("identifier", "FortiGate-VM64", 15)
]
```

### Token Pattern Recognition

**Variable Tokens**:
```python
# Pattern: \{?\$(?P<variable_name>[^\s]+?)\s*\}?
# Matches: $VAR or {$VAR}

"platform_type" → Token("variable", "platform_type", line_number)
"{$retry_count}" → Token("variable", "retry_count", line_number)
```

**Number Tokens**:
```python
# Pattern: (?P<number_content>\d+)

"5" → Token("number", "5", line_number)
"300" → Token("number", "300", line_number)
```

**String Tokens**:
```python
# Pattern: "(?:\"|[^"\\]|\\.)*?"

'"admin\\n"' → Token("string", 'admin\\n', line_number)
```

---

## Syntax-Driven Parsing

### Parser State Machine

```python
class Parser:
    def __init__(self, file_name, tokens, lines):
        self.tokens = tokens          # Token stream from lexer
        self.cursor = 0               # Current token position
        self.vm_codes = []            # Generated VM codes
        self.file_name = file_name    # Source file path
        self.lines = lines            # Source file lines (for error reporting)
        self.cur_line_number = 0      # Current DSL line being parsed
        self.devices = set()          # Discovered device names
        self.called_files = set()     # Included files
        self.cur_section = None       # Current device section
```

### Main Parsing Loop

```python
def run(self):
    while self._cur_token is not None:
        self._script()  # Process one script element
    return self.vm_codes, self.devices, self.called_files

def _script(self):
    """Process one script element (section, command, API, keyword)."""
    token = self._cur_token
    
    # Validate token type
    if not script_syntax.is_valid_script_type(token.type):
        self._raise_syntax_error(f"Unexpected token type '{token.type}'")
    
    # Top-level categories: API or keyword
    if script_syntax.at_top_level_category(token.type):
        # Get syntax definition from schema
        syntax_definition = script_syntax.get_token_syntax_definition(token)
        operation, matched_rule = syntax_definition
        
        # Dispatch to handler (e.g., _parse, _control_block, _parse_options)
        getattr(self, f"_{operation}")(matched_rule)
    else:
        # Simple handlers: section, command, comment, include
        func = self._get_func_handler()
        func()
        self._advance()
```

### Syntax Definition Retrieval

**File**: `syntax.py`

```python
def get_token_syntax_definition(self, token):
    """
    Get parsing definition for a token from unified schema.
    
    Returns: (operation, matched_rule) tuple
    - operation: Parser method to call (_parse, _control_block, _parse_options)
    - matched_rule: Rules for parsing parameters/structure
    """
    token_type = token.type
    token_str = token.str
    
    if token_type == "api":
        return self._get_api_syntax_definition(token_str)
    
    if token_type == "keyword":
        return self._get_keyword_syntax_definition(token_str)
    
    return None
```

**API Syntax** (`expect` example):

```python
# Schema: cli_syntax.json
{
  "expect": {
    "parse_mode": "options",
    "parameters": {
      "-e": {"alias": "rule", "position": 0, "required": true},
      "-for": {"alias": "qaid", "position": 1, "default": "NO_QAID"},
      "-t": {"alias": "wait_seconds", "position": 2, "type": "int", "default": 5}
    }
  }
}

# Returns:
("parse_options", [
    {"-e": None, "-for": "NO_QAID", "-t": "5"},  # Default values
    [[identifier, None], [[identifier, number, string], None]]  # Option parsing rules
])
```

**Keyword Syntax** (`if` example):

```python
# Schema: cli_syntax.json
{
  "if": {
    "type": "control_block",
    "flow": ["expression", "script", ["elseif", "else", "fi"]]
  }
}

# Returns:
("control_block", ["expression", "script", ["elseif", "else", "fi"]])
```

---

## Control Flow Compilation

### Control Block Parser

**Method**: `_control_block(exp_stats, prev_code=None)`

**Purpose**: Parse nested control flow structures (if/while/loop)

**Algorithm**:
```python
def _control_block(self, exp_stats, prev_code=None):
    """
    Recursively parse control flow blocks.
    
    Args:
        exp_stats: Expected statements ["expression", "script", ["elseif", "else", "fi"]]
        prev_code: Previous VM code (for linking control flow blocks)
    
    Returns:
        Generated VM code
    """
    # 1. Get handler for current keyword (e.g., _if, _while, _loop)
    func = self._get_func_handler("str")
    
    # 2. Execute handler to create VM code (may link to prev_code)
    vm_code = func(prev_code)
    
    # 3. Advance past keyword
    self._advance()
    
    # 4. Process expected statements from schema "flow"
    if not exp_stats:
        return vm_code
    
    cur_block_end = exp_stats[-1]  # ["elseif", "else", "fi"]
    
    for exp_stat in exp_stats:
        if exp_stat == "expression":
            # Parse expression (condition)
            expression_tokens = self._expression()
            for token in expression_tokens:
                vm_code.add_parameter(token)
        
        elif exp_stat == "script":
            # Parse script body until block end keyword
            while not self._eof() and not self._is_ctrl_blk_end(cur_block_end):
                self._script()
        
        else:
            # Nested control keyword (elseif/else/fi)
            if self._eof():
                self._raise_syntax_error(f"Unexpected EOF, missed {cur_block_end}")
            
            # Get nested keyword's flow
            exp_stats = script_syntax.get_keyword_cli_syntax(self._cur_token.str)
            
            # Recursively parse nested block, passing current vm_code as prev_code
            self._control_block(exp_stats, vm_code)
    
    return vm_code
```

### Control Flow Handlers

#### If Block

```python
def _if(self, _):
    """
    Generate VM code for if statement.
    
    Returns: VMCode with empty parameters (filled later by elseif/else/fi)
    """
    return self._add_vm_code(
        self._cur_token.line_number,
        "if_not_goto",
        ()  # Parameters added later
    )
```

**Flow**:
1. Create `if_not_goto` VM code at current line
2. `_control_block` parses expression → adds expression tokens as parameters
3. `_control_block` parses script body → generates VM codes for body
4. `_control_block` encounters `elseif`/`else`/`fi` → recursive call with prev_code

#### Elseif Block

```python
def _elseif(self, prev_vm_code):
    """
    Generate VM code for elseif statement.
    
    Args:
        prev_vm_code: Previous if/elseif VM code (to link jump target)
    
    Returns: New elseif VM code
    """
    # Add current line number as jump target to previous block
    prev_vm_code.add_parameter(self._cur_token.line_number)
    
    # Create new elseif VM code
    return self._add_vm_code(
        self._cur_token.line_number,
        "elseif",
        ()  # Parameters added later
    )
```

**Linking Mechanism**:
```
if_not_goto (line 15) → params: [expression...] + [103]  ← elseif line number
elseif (line 103) → params: [expression...] + [107]  ← else line number
else (line 107) → params: [110]  ← endif line number
endif (line 110) → params: []
```

#### Else Block

```python
def _else(self, prev_vm_code):
    """
    Generate VM code for else statement.
    
    Args:
        prev_vm_code: Previous if/elseif VM code
    
    Returns: else VM code
    """
    if prev_vm_code is None:
        self._raise_syntax_error("else without if")
    
    # Link previous block to else line
    prev_vm_code.add_parameter(self._cur_token.line_number)
    
    # Create else VM code
    return self._add_vm_code(
        self._cur_token.line_number,
        "else",
        ()  # endif line added later
    )
```

#### Fi (Endif) Block

```python
def _fi(self, prev_vm_code):
    """
    Generate VM code for endif statement.
    
    Args:
        prev_vm_code: Previous else/elseif VM code
    
    Returns: endif VM code
    """
    if prev_vm_code is None:
        self._raise_syntax_error("fi without if")
    
    # Link previous block to endif line
    prev_vm_code.add_parameter(self._cur_token.line_number)
    
    # Create endif VM code (ends control flow)
    return self._add_vm_code(
        self._cur_token.line_number,
        "endif",
        ()
    )
```

#### Loop Block

```python
def _loop(self, _):
    """
    Generate VM code for loop statement.
    
    Returns: loop VM code (marker for loop start)
    """
    return self._add_vm_code(
        self._cur_token.line_number,
        "loop",
        ()  # Condition added by _control_block
    )

def _until(self, prev_vm_code):
    """
    Generate VM code for until statement (loop end).
    
    Args:
        prev_vm_code: loop VM code (to get loop start line)
    
    Returns: until VM code with loop start line
    """
    return self._add_vm_code(
        self._cur_token.line_number,
        "until",
        (prev_vm_code.line_number,)  # Loop start line for jump-back
    )
```

#### While Block

```python
def _while(self, _):
    """
    Generate VM code for while statement.
    
    Returns: loop VM code (while = loop internally)
    """
    return self._add_vm_code(
        self._cur_token.line_number,
        "loop",
        ()
    )

def _endwhile(self, prev_vm_code):
    """
    Generate VM code for endwhile statement.
    
    Args:
        prev_vm_code: while VM code (to get loop start line)
    
    Returns: until VM code with loop start line
    """
    return self._add_vm_code(
        self._cur_token.line_number,
        "until",
        (prev_vm_code.line_number,)  # Loop start line for jump-back
    )
```

---

## Line Number Tracking

### Line Number Flow

```
┌─────────────────────────────────────────────────────────────┐
│  DSL Source (first_case.txt)                                │
│  Line 15: <if {$platform_type} eq FortiGate-VM64>           │
│  Line 16:     comment Branch A                              │
│  Line 17: <elseif {$platform_type} eq FortiGate-VM64-KVM>   │
│  Line 18:     comment Branch B                              │
│  Line 19: <else>                                            │
│  Line 20:     comment Branch C                              │
│  Line 21: <fi>                                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼ LEXER
┌─────────────────────────────────────────────────────────────┐
│  Tokens (with line numbers)                                 │
│  Token("keyword", "if", 15)                                 │
│  Token("variable", "platform_type", 15)                     │
│  Token("operator", "eq", 15)                                │
│  Token("identifier", "FortiGate-VM64", 15)                  │
│  Token("comment", "Branch A", 16)                           │
│  Token("keyword", "elseif", 17)                             │
│  ...                                                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼ PARSER
┌─────────────────────────────────────────────────────────────┐
│  VM Codes (with line numbers and jump targets)              │
│  98  if_not_goto platform_type eq FortiGate-VM64 103        │
│  99  comment Branch A                                       │
│  103 elseif platform_type eq FortiGate-VM64-KVM 107         │
│  104 comment Branch B                                       │
│  107 else 110                                               │
│  108 comment Branch C                                       │
│  110 endif                                                  │
└─────────────────────────────────────────────────────────────┘
```

### Line Number Usage

**1. Token Line Numbers** (Lexer):
```python
Token(_type="keyword", data="if", line_number=15)
```
- Tracks **source file line** (1-based)
- Used for error reporting
- Passed to VM code during parsing

**2. VM Code Line Numbers** (Parser):
```python
VMCode(line_number=15, operation="if_not_goto", parameters=(...))
```
- Stores **DSL source line** for debugging
- Used as **jump targets** in control flow
- Maps VM code back to source for error messages

**3. Jump Targets** (Control Flow):
```python
# if_not_goto at line 98
VMCode(98, "if_not_goto", ("platform_type", "eq", "FortiGate-VM64", 103))
#                                                                    ^^^
#                                                         Jump to line 103 if false
```

### Where Line Numbers Come From

**Critical Understanding**: Jump target line numbers come from `self._cur_token.line_number` when the **target keyword** is encountered during parsing.

#### Forward Jumps (If/Elseif/Else → Next Block)

```python
# Parser encounters <elseif> at DSL line 103
token = Token("keyword", "elseif", 103)  # Token from lexer
self._cur_token = token
self._cur_token.line_number  # = 103

# _elseif() is called with prev_vm_code (the if block)
def _elseif(self, prev_vm_code):
    # Add CURRENT token's line number to PREVIOUS block
    prev_vm_code.add_parameter(self._cur_token.line_number)
    #                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^
    #                          This is 103 - the elseif's line!
    
    # Previous if block now knows: "jump to line 103"
    return self._add_vm_code(self._cur_token.line_number, "elseif", ())
```

**Example Timeline**:
```
Time 1: Parser at line 98 (<if>)
    _if() creates: VMCode(98, "if_not_goto", ())
    Jump target: NOT YET KNOWN

Time 2: Parser moves forward, encounters line 103 (<elseif>)
    self._cur_token.line_number = 103
    _elseif(vm_code_98) adds: vm_code_98.add_parameter(103)
    Jump target: NOW KNOWN! Jump to 103
```

#### Backward Jumps (While/Loop → Until/Endwhile)

```python
# Parser encounters <while> at DSL line 44
token = Token("keyword", "while", 44)
self._cur_token = token

# _while() creates loop marker
def _while(self, _):
    vm_code = VMCode(self._cur_token.line_number, "loop", ())
    # vm_code.line_number = 44  ← STORED for later use
    return vm_code

# Parser encounters <endwhile> at DSL line 59
token = Token("keyword", "endwhile", 59)
self._cur_token = token

# _endwhile() uses PREVIOUS line number for jump-back
def _endwhile(self, prev_vm_code):
    # prev_vm_code is the loop marker from line 44
    loop_start_line = prev_vm_code.line_number  # = 44
    
    return self._add_vm_code(
        self._cur_token.line_number,  # Current line 59
        "until",
        (prev_vm_code.line_number,)   # Jump back to line 44
        #^^^^^^^^^^^^^^^^^^^^^^^^^^^
        # This is 44 - the loop start line!
    )
```

**Example Timeline**:
```
Time 1: Parser at line 44 (<while>)
    _while() creates: VMCode(44, "loop", (...))
    Stores line_number=44 in VMCode object

Time 2: Parser moves forward through loop body (lines 45-58)

Time 3: Parser encounters line 59 (<endwhile>)
    self._cur_token.line_number = 59
    prev_vm_code.line_number = 44 (from loop marker)
    _endwhile(vm_code_44) creates: VMCode(59, "until", (44, ...))
    Jump target: 44 (backward jump to loop start)
```

### Summary: Two Sources of Line Numbers

| Jump Type | Source | When Captured | Example |
|-----------|--------|---------------|---------|
| **Forward Jump** (if→elseif→else→fi) | `self._cur_token.line_number` | When **next** keyword encountered | Line 103 captured when parser reaches `<elseif>` |
| **Backward Jump** (while→endwhile) | `prev_vm_code.line_number` | When **loop start** keyword encountered | Line 44 stored when parser reaches `<while>`, used when `<endwhile>` encountered |

**Key Code Patterns**:

```python
# Forward: Add NEXT block's line to CURRENT block
def _elseif(self, prev_vm_code):
    prev_vm_code.add_parameter(self._cur_token.line_number)  # Next block's line
    return self._add_vm_code(...)

# Backward: Use PREVIOUS block's line in CURRENT block
def _endwhile(self, prev_vm_code):
    return self._add_vm_code(
        self._cur_token.line_number,      # Current line
        "until",
        (prev_vm_code.line_number,)       # Previous loop start line
    )
```

---

### Control Flow Linking Example

**DSL**:
```plaintext
Line 98:  <if {$platform_type} eq FortiGate-VM64>
Line 99:      comment Branch A
Line 103: <elseif {$platform_type} eq FortiGate-VM64-KVM>
Line 104:     comment Branch B
Line 107: <else>
Line 108:     comment Branch C
Line 110: <fi>
```

**Parsing Timeline** (How Line Numbers Become Jump Targets):

| Step | Current Token | Action | VM Code Created/Modified | Key Insight |
|------|---------------|--------|-------------------------|-------------|
| 1 | `if` at line 98 | `_if()` called | `VMCode(98, "if_not_goto", ())` | **No jump target yet!** |
| 2 | Expression tokens | Parse expression | `VMCode(98, ..., ("platform_type", "eq", "FortiGate-VM64"))` | Condition added |
| 3 | Script body | Parse `comment` | `VMCode(99, "comment", ("Branch A",))` | Body executed |
| 4 | `elseif` at line 103 | `_elseif(vm_code_98)` | `vm_code_98.add_parameter(103)` | **Line 103 from `self._cur_token.line_number`** |
|  |  |  | `VMCode(103, "elseif", ())` | New block created |
| 5 | Expression tokens | Parse expression | `VMCode(103, ..., ("platform_type", "eq", "VM64-KVM"))` | |
| 6 | Script body | Parse `comment` | `VMCode(104, "comment", ("Branch B",))` | |
| 7 | `else` at line 107 | `_else(vm_code_103)` | `vm_code_103.add_parameter(107)` | **Line 107 from `self._cur_token.line_number`** |
|  |  |  | `VMCode(107, "else", ())` | New block created |
| 8 | Script body | Parse `comment` | `VMCode(108, "comment", ("Branch C",))` | |
| 9 | `fi` at line 110 | `_fi(vm_code_107)` | `vm_code_107.add_parameter(110)` | **Line 110 from `self._cur_token.line_number`** |
|  |  |  | `VMCode(110, "endif", ())` | Block ends |

**The Key Mechanism**:
```python
# When parser encounters <elseif> at line 103:
def _elseif(self, prev_vm_code):
    # self._cur_token.line_number is 103 (current keyword's line)
    prev_vm_code.add_parameter(self._cur_token.line_number)  # Add 103 to if block
    # Previous if block now knows: "jump to line 103 if I fail"
    return self._add_vm_code(self._cur_token.line_number, "elseif", ())
```

**Final Jump Chain**:
```
if_not_goto at line 98 → params end with 103 → "Jump to 103 if false"
elseif at line 103 → params end with 107 → "Jump to 107 if matched/failed"
else at line 107 → params end with 110 → "Jump to 110"
endif at line 110 → no params → "Pop if_stack and continue"
```

**Source of Line Numbers**:
- **Forward jumps** (if/elseif/else): Use `self._cur_token.line_number` when **next** block is encountered
- **Backward jumps** (while/until): Use `prev_vm_code.line_number` from **loop start** block

---

## VM Code Generation

### VMCode Structure

```python
class VMCode:
    def __init__(self, line_number, operation, parameters, schema=None):
        self.line_number = line_number    # DSL source line (for debugging/jumps)
        self.operation = operation        # API name or control flow keyword
        self.parameters = parameters      # Tuple of parameters
        self._schema = schema             # Optional schema for validation
    
    def __str__(self):
        parameters = " ".join(str(p) for p in self.parameters)
        return f"{self.line_number} {self.operation} {parameters}"
    
    def add_parameter(self, parameter):
        """Add parameter (used for control flow jump targets)."""
        self.parameters = (*self.parameters, parameter)
```

### VM Code Examples

**Device Switching**:
```python
# DSL: [FGT_B]
VMCode(2, "switch_device", ("FGT_B",))
```

**Variable Assignment**:
```python
# DSL: <strset QAID_MAIN 205817>
VMCode(11, "strset", ("QAID_MAIN", "205817"))
```

**API Call**:
```python
# DSL: expect -e "Version:" -for {$QAID} -t 5
VMCode(50, "expect", ("Version:", "QAID", "5", "unmatch", None, None, "yes", None, "3"))
```

**Control Flow**:
```python
# DSL: <if {$retry_count} < {$max_retries}>
VMCode(44, "if_not_goto", ("retry_count", "<", "max_retries", 58))

# DSL: <until {$retry_count} eq {$max_retries}>
VMCode(59, "until", (44, "retry_count", "eq", "max_retries"))
```

### VM Code Dumping

**File**: `parser.py`

```python
def dump_vm_codes(self):
    """Write VM codes to .vm file for debugging."""
    vm_file = output.compose_compiled_file(Path(self.file_name).stem, "codes.vm")
    with open(vm_file, "w") as f:
        for vm_code in self.vm_codes:
            f.write(f"{vm_code}\n")
```

**Example Output** (`codes.vm`):
```
2 switch_device FGT_B
11 strset QAID_MAIN 205817
37 intset retry_count 0
38 intset max_retries 3
44 loop retry_count < max_retries
45 intchange retry_count + 1
46 comment Attempt {$retry_count} of {$max_retries}...
49 command get system status
50 expect Version: FortiGate QAID_CONN_RETRY 5 unmatch None None yes None 3
59 until 44 retry_count eq max_retries
```

---

## Real Compilation Examples

### Example 1: Simple If Statement

**DSL**:
```plaintext
Line 15: <if {$status} eq up>
Line 16:     comment System is up
Line 17: <fi>
```

**Tokens**:
```python
[
    Token("keyword", "if", 15),
    Token("variable", "status", 15),
    Token("operator", "eq", 15),
    Token("identifier", "up", 15),
    Token("comment", "System is up", 16),
    Token("keyword", "fi", 17)
]
```

**Parsing Flow**:
1. Token `if` → `_control_block(["expression", "script", ["fi"]])`
2. `_if()` → `VMCode(15, "if_not_goto", ())`
3. Parse `expression` → Add params: `("status", "eq", "up")`
4. Parse `script` → `VMCode(16, "comment", ("System is up",))`
5. Token `fi` → `_fi(prev_vm_code)` → prev_vm_code.add_parameter(17)
6. `VMCode(17, "endif", ())`

**VM Codes**:
```
15 if_not_goto status eq up 17
16 comment System is up
17 endif
```

**Control Flow**:
```
if status != "up":
    jump to line 17  # Skip comment
else:
    execute line 16  # Show comment
    continue to line 17
Pop if_stack
```

---

### Example 2: If/Elseif/Else

**DSL**:
```plaintext
Line 98:  <if {$platform_type} eq FortiGate-VM64>
Line 99:      comment Standard VM
Line 103: <elseif {$platform_type} eq FortiGate-VM64-KVM>
Line 104:     comment KVM platform
Line 107: <else>
Line 108:     comment Unknown platform
Line 110: <fi>
```

**Tokens** (simplified):
```python
[
    Token("keyword", "if", 98),
    Token("variable", "platform_type", 98),
    Token("operator", "eq", 98),
    Token("identifier", "FortiGate-VM64", 98),
    # ... tokens for line 99
    Token("keyword", "elseif", 103),
    # ... expression tokens
    # ... tokens for line 104
    Token("keyword", "else", 107),
    # ... tokens for line 108
    Token("keyword", "fi", 110)
]
```

**Parsing Flow** (Detailed):

```python
# Step 1: Parse <if>
_control_block(["expression", "script", ["elseif", "else", "fi"]], prev_code=None)
    _if(None) → vm_code_98 = VMCode(98, "if_not_goto", ())
    
    # Parse expression
    _expression() → ["platform_type", "eq", "FortiGate-VM64"]
    vm_code_98.add_parameter("platform_type")
    vm_code_98.add_parameter("eq")
    vm_code_98.add_parameter("FortiGate-VM64")
    # vm_code_98.parameters = ("platform_type", "eq", "FortiGate-VM64")
    
    # Parse script
    while not ctrl_blk_end:
        _script() → VMCode(99, "comment", ("Standard VM",))
    
    # Step 2: Parse <elseif>
    _control_block(["expression", "script", ["elseif", "else", "fi"]], prev_code=vm_code_98)
        _elseif(vm_code_98):
            vm_code_98.add_parameter(103)  # Add jump target
            # vm_code_98.parameters = ("platform_type", "eq", "FortiGate-VM64", 103)
            vm_code_103 = VMCode(103, "elseif", ())
        
        # Parse expression
        _expression() → ["platform_type", "eq", "FortiGate-VM64-KVM"]
        vm_code_103.parameters = ("platform_type", "eq", "FortiGate-VM64-KVM")
        
        # Parse script
        _script() → VMCode(104, "comment", ("KVM platform",))
        
        # Step 3: Parse <else>
        _control_block(["script", "fi"], prev_code=vm_code_103)
            _else(vm_code_103):
                vm_code_103.add_parameter(107)  # Add jump target
                # vm_code_103.parameters = ("platform_type", "eq", "FortiGate-VM64-KVM", 107)
                vm_code_107 = VMCode(107, "else", ())
            
            # Parse script
            _script() → VMCode(108, "comment", ("Unknown platform",))
            
            # Step 4: Parse <fi>
            _control_block([], prev_code=vm_code_107)
                _fi(vm_code_107):
                    vm_code_107.add_parameter(110)  # Add jump target
                    # vm_code_107.parameters = (110,)
                    VMCode(110, "endif", ())
```

**Final VM Codes**:
```
98  if_not_goto platform_type eq FortiGate-VM64 103
99  comment Standard VM
103 elseif platform_type eq FortiGate-VM64-KVM 107
104 comment KVM platform
107 else 110
108 comment Unknown platform
110 endif
```

**Jump Target Graph**:
```
98 (if_not_goto) ────────┐
                         │ if false, jump to 103
                         ▼
99 (comment)         103 (elseif) ────────┐
                                          │ if prev true OR this false, jump to 107
                                          ▼
                     104 (comment)    107 (else) ────────┐
                                                         │ jump to 110
                                                         ▼
                                      108 (comment)  110 (endif)
```

---

### Example 3: While Loop

**DSL**:
```plaintext
Line 37: <intset retry_count 0>
Line 38: <intset max_retries 3>
Line 44: <while {$retry_count} < {$max_retries}>
Line 45:     <intchange {$retry_count} + 1>
Line 46:     comment Attempt {$retry_count}
Line 50:     expect -e "Version:" -for {$QAID} -t 5
Line 59: <endwhile {$retry_count} eq {$max_retries}>
```

**Tokens** (simplified):
```python
[
    Token("keyword", "intset", 37),
    Token("identifier", "retry_count", 37),
    Token("number", "0", 37),
    Token("keyword", "intset", 38),
    Token("identifier", "max_retries", 38),
    Token("number", "3", 38),
    Token("keyword", "while", 44),
    Token("variable", "retry_count", 44),
    Token("operator", "<", 44),
    Token("variable", "max_retries", 44),
    # ... tokens for loop body
    Token("keyword", "endwhile", 59),
    # ... exit condition tokens
]
```

**Parsing Timeline** (Loop Jump Target):

| Step | Current Token | Action | VM Code Created/Modified | Key Insight |
|------|---------------|--------|-------------------------|-------------|
| 1 | `intset` at line 37 | `_parse()` | `VMCode(37, "intset", ("retry_count", "0"))` | Variable init |
| 2 | `intset` at line 38 | `_parse()` | `VMCode(38, "intset", ("max_retries", "3"))` | Variable init |
| 3 | `while` at line 44 | `_while()` | `VMCode(44, "loop", ())` | **Loop start marker** |
|  |  |  |  | **Stores line_number=44** |
| 4 | Expression tokens | Parse expression | `VMCode(44, "loop", ("retry_count", "<", "max_retries"))` | Entry condition |
| 5 | Script body | Parse commands | `VMCode(45, "intchange", ...)` | Loop body |
|  |  |  | `VMCode(46, "comment", ...)` | |
|  |  |  | `VMCode(50, "expect", ...)` | |
| 6 | `endwhile` at line 59 | `_endwhile(vm_code_44)` | **Uses `prev_vm_code.line_number`** | **Line 44 from loop marker!** |
|  |  |  | `VMCode(59, "until", (44, ...))` | Jump back target set |
|  |  |  |  | Parameter 0 = 44 (loop start) |

**The Key Difference**:
```python
# Forward jumps (if/elseif/else): Use CURRENT line
def _elseif(self, prev_vm_code):
    prev_vm_code.add_parameter(self._cur_token.line_number)  # Current token's line
    # "Jump forward to the line I'm on now"

# Backward jumps (while/until): Use PREVIOUS line
def _endwhile(self, prev_vm_code):
    return self._add_vm_code(
        self._cur_token.line_number,
        "until",
        (prev_vm_code.line_number,)  # Previous loop marker's line
    )
    # "Jump backward to the line where loop started"
```

**Final VM Codes**:
```
37 intset retry_count 0
38 intset max_retries 3
44 loop retry_count < max_retries        ← Loop start (line_number=44)
45 intchange retry_count + 1
46 comment Attempt {$retry_count}
50 expect Version: FortiGate QAID 5 unmatch None None yes None 3
59 until 44 retry_count eq max_retries   ← Jump back to line 44
          ^^
          Loop start line from prev_vm_code.line_number
```

**Execution Flow**:
```
Line 44 (loop): Entry point (marker only)
Line 45-50: Loop body
Line 59 (until): Check exit condition
    If retry_count == max_retries → Exit (PC + 1)
    Else → executor.jump_backward(44)  ← Uses first parameter (44)
```

---

## Schema-Driven System

### Unified Schema (cli_syntax.json)

**Structure**:
```json
{
  "apis": {
    "expect": { "parse_mode": "options", "parameters": {...} },
    "setvar": { "parse_mode": "positional", "parameters": [...] }
  },
  "valid_commands": ["get ", "show ", "config ", "end", "next"],
  "script_types": ["section", "command", "api", "keyword", ...],
  "deprecated_commands": {
    "^oldcmd\\s+(.*)$": "newcmd \"\\1\""
  },
  "keywords": {
    "if": {
      "type": "control_block",
      "flow": ["expression", "script", ["elseif", "else", "fi"]]
    },
    "while": {
      "type": "control_block",
      "flow": ["expression", "script", "endwhile"]
    },
    "strset": {
      "type": "parse",
      "rules": [[identifier, null], [[identifier, number, string], null]]
    }
  }
}
```

### Custom API Discovery

**File**: `compiler.py`

```python
@classmethod
def _ensure_patterns_refreshed(cls):
    """
    One-time discovery of custom APIs from plugins/apis/.
    
    Regenerates lexer patterns to include custom APIs.
    """
    if not cls._patterns_refreshed:
        with cls._refresh_lock:
            if not cls._patterns_refreshed:
                logger.debug("Refreshing patterns for custom APIs")
                script_syntax.refresh_patterns()
                cls._patterns_refreshed = True
```

**File**: `syntax.py`

```python
def refresh_patterns(self):
    """
    Discover custom APIs and regenerate patterns.
    
    Flow:
    1. Import api_manager (after all modules loaded)
    2. Discover APIs from plugins/apis/
    3. Create default schema for custom APIs
    4. Merge with static APIs
    5. Regenerate API pattern
    6. Recompile line pattern
    """
    from lib.core.executor.api_manager import discover_apis
    
    discovered_apis, _ = discover_apis()
    
    all_apis = dict(self.schema["apis"])
    for api_name in discovered_apis:
        if api_name not in all_apis:
            all_apis[api_name] = self._create_default_api_schema()
    
    self.schema["apis"] = all_apis
    
    # Regenerate patterns
    api_pattern_list = [
        self._api_pattern_for_api(api_name, all_apis[api_name])
        for api_name in all_apis
    ]
    api_pattern_list = sorted(api_pattern_list, key=len, reverse=True)
    ScriptSyntax.LINE_PATTERN_TABLE["api"] = r"|".join(api_pattern_list)
    
    # Recompile line pattern
    self.line_pattern = re.compile(...)
```

### Default Schema for Custom APIs

```python
@staticmethod
def _create_default_api_schema():
    """
    Default schema for dynamically discovered custom APIs.
    
    Uses "options" parse mode with common parameters.
    """
    return {
        "category": "custom",
        "parse_mode": "options",
        "parameters": {
            "-var": {"alias": "var", "type": "string", "position": 0},
            "-file": {"alias": "file", "type": "string", "position": 1},
            "-value": {"alias": "value", "type": "string", "position": 2},
            "-name": {"alias": "name", "type": "string", "position": 3}
        },
        "description": "Dynamically discovered custom API"
    }
```

---

## Summary

### Compilation Pipeline

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  DSL Source     │────▶│  Lexer           │────▶│  Tokens         │
│  (first.txt)    │     │  (Pattern Match) │     │  (Type + Line#) │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                           │
                        ┌──────────────────┐               │
                        │  Schema          │◀──────────────┘
                        │  (cli_syntax.json)│
                        └────────┬─────────┘
                                 │
                                 ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │  Parser          │────▶│  VM Codes       │
                        │  (Syntax Rules)  │     │  (Executable)   │
                        └──────────────────┘     └─────────────────┘
```

### Key Mechanisms

1. **Tokenization**: Regex pattern matching with line number preservation
2. **Syntax Lookup**: Schema-driven parsing rules from cli_syntax.json
3. **Control Flow**: Recursive `_control_block()` with prev_vm_code linking
4. **Line Number Tracking**: 
   - Tokens carry source line numbers
   - VM codes store line numbers for jumps
   - Control flow links blocks via line number parameters
5. **VM Code Generation**: VMCode objects with operation, parameters, line number
6. **Jump Targets**: Added via `add_parameter()` during recursive parsing

### Control Flow Summary

| DSL Construct | VM Operation | Jump Mechanism |
|---------------|--------------|----------------|
| `<if>` | `if_not_goto` | Jump to elseif/else/fi if false |
| `<elseif>` | `elseif` | Jump to next elseif/else/fi if false or prev matched |
| `<else>` | `else` | Jump to fi if prev matched |
| `<fi>` | `endif` | Pop if_stack |
| `<while>` | `loop` | Entry marker |
| `<endwhile>` | `until` | Jump back to loop start if condition false |
| `<loop>` | `loop` | Entry marker |
| `<until>` | `until` | Jump back to loop start if condition false |

### Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `lexer.py` | 318 | Tokenize DSL into typed tokens |
| `parser.py` | 294 | Convert tokens to VM codes |
| `syntax.py` | 447 | Load schema and manage patterns |
| `vm_code.py` | 56 | VM instruction data structure |
| `compiler.py` | 74 | Orchestrate compilation with caching |
| `cli_syntax.json` | 1147 | Define APIs, keywords, control flow |

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-18  
**Framework Version**: AutoLib v3 V3R10B0007
