# Compiler Architecture - General Concepts vs AutoLib v3

**Purpose**: Understand compilation fundamentals and compare mainstream language compilers (Python) with AutoLib v3's DSL compiler  
**Last Updated**: 2026-02-18

---

## Table of Contents

1. [Compiler Fundamentals](#compiler-fundamentals)
2. [Python Compilation Pipeline](#python-compilation-pipeline)
3. [AutoLib v3 Compilation Pipeline](#autolib-v3-compilation-pipeline)
4. [Side-by-Side Comparison](#side-by-side-comparison)
5. [Key Similarities](#key-similarities)
6. [Key Differences](#key-differences)
7. [When to Use Each Pattern](#when-to-use-each-pattern)

---

## Compiler Fundamentals

### What is a Compiler?

A **compiler** is a program that translates source code written in one language into another form, typically machine code or bytecode that can be executed by a computer or virtual machine.

### Universal Compilation Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                   UNIVERSAL COMPILER PIPELINE               │
└─────────────────────────────────────────────────────────────┘

Source Code (Text)
    │
    ▼
┌─────────────────┐
│  LEXER          │ ← Tokenization / Lexical Analysis
│  (Scanner)      │   • Breaks code into tokens
└────────┬────────┘   • Identifies keywords, operators, literals
         │            • Attaches metadata (line numbers, types)
         ▼
    Tokens
    (List of classified symbols)
         │
         ▼
┌─────────────────┐
│  PARSER         │ ← Syntax Analysis
│  (Syntax Tree)  │   • Validates syntax rules
└────────┬────────┘   • Builds Abstract Syntax Tree (AST)
         │            • Represents program structure
         ▼
    AST / Parse Tree
    (Hierarchical structure)
         │
         ▼
┌─────────────────┐
│  CODE GENERATOR │ ← Code Generation
│  (Backend)      │   • Converts AST to target code
└────────┬────────┘   • Optimization (optional)
         │            • Produces executable form
         ▼
    Target Code
    (Bytecode, Machine Code, or VM Instructions)
         │
         ▼
┌─────────────────┐
│  EXECUTOR       │ ← Runtime / Execution
│  (VM/CPU)       │   • Executes target code
└─────────────────┘   • Manages memory, I/O, flow control
```

### Key Phases Explained

| Phase | Input | Output | Purpose | Example |
|-------|-------|--------|---------|---------|
| **Lexer** | Source text | Tokens | Break into atomic units | `"if x == 5:"` → `[IF, IDENT(x), EQ_EQ, INT(5), COLON]` |
| **Parser** | Tokens | AST | Validate syntax, build structure | Tokens → Tree with if-node, condition-node, body-node |
| **Code Generator** | AST | Bytecode/VM Code | Convert structure to executable | AST → Bytecode instructions |
| **Executor** | Bytecode | Results | Run the program | Bytecode → Output/Side effects |

---

## Python Compilation Pipeline

### Overview

Python is a **compiled language** (often misunderstood as "interpreted only"). Python source code is compiled to bytecode, which is then executed by the Python Virtual Machine (PVM).

```
┌─────────────────────────────────────────────────────────────┐
│                   PYTHON COMPILATION PIPELINE               │
└─────────────────────────────────────────────────────────────┘

Python Source (.py)
    │
    ▼
┌─────────────────┐
│  Tokenizer      │ ← tokenize module (lib/tokenize.py)
└────────┬────────┘   • Uses regex patterns
         │            • Produces token stream
         ▼
    Token Stream
    [NAME, OP, NUMBER, NEWLINE, ...]
         │
         ▼
┌─────────────────┐
│  Parser         │ ← parser module (Grammar/python.gram)
└────────┬────────┘   • Uses PEG parser (Python 3.9+)
         │            • Builds AST
         ▼
    AST (Abstract Syntax Tree)
    Module(body=[If(...), Assign(...)])
         │
         ▼
┌─────────────────┐
│  Compiler       │ ← compile() / compiler package
└────────┬────────┘   • Converts AST to bytecode
         │            • Optimizes (constant folding, etc.)
         ▼
    Bytecode (.pyc)
    [LOAD_NAME, COMPARE_OP, POP_JUMP_IF_FALSE, ...]
         │
         ▼
┌─────────────────┐
│  PVM            │ ← Python Virtual Machine (eval loop)
│  (Interpreter)  │   • Stack-based execution
└─────────────────┘   • Interprets bytecode instructions
```

### Python Example: Step-by-Step

**Source Code**:
```python
# example.py
x = 10
if x > 5:
    print("Large")
else:
    print("Small")
```

---

#### Phase 1: Tokenization

**Command**: `python -m tokenize example.py`

**Output**:
```
1,0-1,1:    NAME           'x'
1,2-1,3:    OP             '='
1,4-1,6:    NUMBER         '10'
1,6-1,7:    NEWLINE        '\n'
2,0-2,2:    NAME           'if'
2,3-2,4:    NAME           'x'
2,5-2,6:    OP             '>'
2,7-2,8:    NUMBER         '5'
2,8-2,9:    OP             ':'
2,9-2,10:   NEWLINE        '\n'
3,0-3,4:    INDENT         '    '
3,4-3,9:    NAME           'print'
3,9-3,10:   OP             '('
3,10-3,17:  STRING         '"Large"'
3,17-3,18:  OP             ')'
3,18-3,19:  NEWLINE        '\n'
4,0-4,4:    NAME           'else'
4,4-4,5:    OP             ':'
4,5-4,6:    NEWLINE        '\n'
5,0-5,4:    INDENT         '    '
5,4-5,9:    NAME           'print'
5,9-5,10:   OP             '('
5,10-5,17:  STRING         '"Small"'
5,17-5,18:  OP             ')'
5,18-5,19:  NEWLINE        '\n'
6,0-6,0:    DEDENT         ''
6,0-6,0:    DEDENT         ''
6,0-6,0:    ENDMARKER      ''
```

**Key Tokens**:
- `NAME`: Identifiers (x, if, print)
- `OP`: Operators (=, >, :, (, ))
- `NUMBER`: Numeric literals (10, 5)
- `STRING`: String literals ("Large", "Small")
- `INDENT/DEDENT`: Python's significant whitespace
- `NEWLINE`: Line endings

---

#### Phase 2: Parsing (AST Generation)

**Command**: `python -c "import ast; print(ast.dump(ast.parse(open('example.py').read()), indent=2))"`

**Output** (simplified):
```python
Module(
  body=[
    Assign(
      targets=[Name(id='x', ctx=Store())],
      value=Constant(value=10)
    ),
    If(
      test=Compare(
        left=Name(id='x', ctx=Load()),
        ops=[Gt()],
        comparators=[Constant(value=5)]
      ),
      body=[
        Expr(
          value=Call(
            func=Name(id='print', ctx=Load()),
            args=[Constant(value='Large')],
            keywords=[]
          )
        )
      ],
      orelse=[
        Expr(
          value=Call(
            func=Name(id='print', ctx=Load()),
            args=[Constant(value='Small')],
            keywords=[]
          )
        )
      ]
    )
  ]
)
```

**AST Structure**:
```
Module
├── Assign
│   ├── targets: [Name(x)]
│   └── value: Constant(10)
└── If
    ├── test: Compare(x > 5)
    ├── body: [Call(print, ["Large"])]
    └── orelse: [Call(print, ["Small"])]
```

---

#### Phase 3: Bytecode Compilation

**Command**: `python -m dis example.py`

**Output**:
```
  1           0 LOAD_CONST               0 (10)
              2 STORE_NAME               0 (x)

  2           4 LOAD_NAME                0 (x)
              6 LOAD_CONST               1 (5)
              8 COMPARE_OP               4 (>)
             10 POP_JUMP_IF_FALSE       22

  3          12 LOAD_NAME                1 (print)
             14 LOAD_CONST               2 ('Large')
             16 CALL_FUNCTION            1
             18 POP_TOP
             20 JUMP_FORWARD             8 (to 30)

  5     >>   22 LOAD_NAME                1 (print)
             24 LOAD_CONST               3 ('Small')
             26 CALL_FUNCTION            1
             28 POP_TOP

  6     >>   30 LOAD_CONST               4 (None)
             32 RETURN_VALUE
```

**Bytecode Instructions**:
- `LOAD_CONST 0 (10)`: Push constant 10 onto stack
- `STORE_NAME 0 (x)`: Pop stack, store in variable x
- `LOAD_NAME 0 (x)`: Load variable x onto stack
- `COMPARE_OP 4 (>)`: Compare top two stack values (x > 5)
- `POP_JUMP_IF_FALSE 22`: Jump to instruction 22 if false
- `CALL_FUNCTION 1`: Call function with 1 argument
- `RETURN_VALUE`: Return top of stack

**Jump Instructions**:
- Line 2: `POP_JUMP_IF_FALSE 22` → If condition false, jump to instruction 22 (else block)
- Line 3: `JUMP_FORWARD 8` → After if-block, jump to instruction 30 (skip else)
- Instruction 22: Start of else block
- Instruction 30: After if/else

---

#### Phase 4: Execution (Python VM)

**PVM Execution Stack** (step-by-step):

```
Instruction 0: LOAD_CONST 0 (10)
    Stack: [10]

Instruction 2: STORE_NAME 0 (x)
    Stack: []
    Variables: {x: 10}

Instruction 4: LOAD_NAME 0 (x)
    Stack: [10]

Instruction 6: LOAD_CONST 1 (5)
    Stack: [10, 5]

Instruction 8: COMPARE_OP 4 (>)
    Stack: [True]  # 10 > 5 = True

Instruction 10: POP_JUMP_IF_FALSE 22
    Stack: []
    Action: Condition is True, do NOT jump (continue to 12)

Instruction 12: LOAD_NAME 1 (print)
    Stack: [<function print>]

Instruction 14: LOAD_CONST 2 ('Large')
    Stack: [<function print>, 'Large']

Instruction 16: CALL_FUNCTION 1
    Stack: [None]
    Output: "Large"

Instruction 18: POP_TOP
    Stack: []

Instruction 20: JUMP_FORWARD 8
    Action: Jump to instruction 30 (skip else block)

Instruction 30: LOAD_CONST 4 (None)
    Stack: [None]

Instruction 32: RETURN_VALUE
    Action: Return None, program ends
```

**Output**: `Large`

---

### Python Compilation Details

**Bytecode Format**:
```python
# Each instruction is 2 bytes (as of Python 3.6+)
# Format: [opcode, argument]
# Example: LOAD_CONST 0 → [0x64, 0x00]
```

**Code Object Structure**:
```python
import dis

code = compile('x = 10', '<string>', 'exec')

# Code object attributes
code.co_code        # Bytecode (bytes object)
code.co_consts      # Constants tuple: (10, None)
code.co_names       # Names tuple: ('x',)
code.co_varnames    # Local variables
code.co_stacksize   # Maximum stack depth
```

**Disassembly Breakdown**:
```python
  Line  Offset  Opcode         Argument    Description
  ----  ------  -------------  ----------  -----------
    1       0   LOAD_CONST     0 (10)      Push 10
            2   STORE_NAME     0 (x)       Store in x
            4   LOAD_CONST     1 (None)    Push None
            6   RETURN_VALUE                Return
```

---

## AutoLib v3 Compilation Pipeline

### Overview

AutoLib v3 compiles a **custom DSL** (Domain-Specific Language) into **VM codes** (Virtual Machine codes) that are executed by a custom executor.

```
┌─────────────────────────────────────────────────────────────┐
│               AUTOLIB V3 COMPILATION PIPELINE               │
└─────────────────────────────────────────────────────────────┘

DSL Source (.txt)
    │
    ▼
┌─────────────────┐
│  Lexer          │ ← lib/core/compiler/lexer.py
└────────┬────────┘   • Regex pattern matching
         │            • Token classification
         ▼
    Tokens
    [Token("keyword", "if", 98), Token("variable", "x", 98), ...]
         │
         ▼
┌─────────────────┐
│  Parser         │ ← lib/core/compiler/parser.py
└────────┬────────┘   • Schema-driven parsing
         │            • Control flow linking
         │            • No AST! Direct to VM codes
         ▼
    VM Codes
    [VMCode(98, "if_not_goto", ("x", "eq", "5", 103)), ...]
         │
         ▼
┌─────────────────┐
│  Executor       │ ← lib/core/executor/executor.py
│  (Custom VM)    │   • Program counter based
└─────────────────┘   • Stack-based control flow (if_stack)
                      • API dispatch system
```

### AutoLib v3 Example: Step-by-Step

**Source Code** (DSL):
```plaintext
[FGT_B]
    <strset counter 10>
    <if {$counter} > 5>
        comment Large value
    <else>
        comment Small value
    <fi>
```

---

#### Phase 1: Tokenization

**Lexer** (`lexer.py`):

```python
# Line pattern matching
line_pattern.match("[FGT_B]")  → section
line_pattern.match("<strset counter 10>")  → statement
line_pattern.match("<if {$counter} > 5>")  → statement
line_pattern.match("comment Large value")  → comment
```

**Tokens**:
```python
[
    Token("section", "FGT_B", 1),
    Token("keyword", "strset", 2),
    Token("identifier", "counter", 2),
    Token("number", "10", 2),
    Token("keyword", "if", 3),
    Token("variable", "counter", 3),
    Token("operator", ">", 3),
    Token("number", "5", 3),
    Token("comment", "Large value", 4),
    Token("keyword", "else", 5),
    Token("comment", "Small value", 6),
    Token("keyword", "fi", 7)
]
```

**Comparison to Python**:
```
Python Token:     Token.NAME, 'x', (1, 0), (1, 1), 'x = 10\n'
AutoLib Token:    Token("identifier", "counter", 2)

Both store: type, value, line_number
```

---

#### Phase 2: Parsing (Direct to VM Code)

**Parser** (`parser.py`):

```python
# AutoLib v3 does NOT build an AST
# It directly generates VM codes during parsing

# Step 1: Parse <strset>
_parse([...]) → VMCode(2, "strset", ("counter", "10"))

# Step 2: Parse <if>
_control_block(["expression", "script", ["else", "fi"]])
    _if() → VMCode(3, "if_not_goto", ())
    _expression() → Add params: ("counter", ">", "5")
    _script() → VMCode(4, "comment", ("Large value",))
    
    # Step 3: Parse <else>
    _else(vm_code_3) → prev_vm_code.add_parameter(5)
    VMCode(5, "else", ())
    _script() → VMCode(6, "comment", ("Small value",))
    
    # Step 4: Parse <fi>
    _fi(vm_code_5) → prev_vm_code.add_parameter(7)
    VMCode(7, "endif", ())
```

**VM Codes**:
```
1  switch_device FGT_B
2  strset counter 10
3  if_not_goto counter > 5 5
4  comment Large value
5  else 7
6  comment Small value
7  endif
```

**Comparison to Python Bytecode**:
```
Python Bytecode:  LOAD_NAME 0 (x), COMPARE_OP 4 (>), POP_JUMP_IF_FALSE 22
AutoLib VM Code:  3 if_not_goto counter > 5 5

Similarities:
- Both have operation + parameters
- Both have line numbers (Python offset, AutoLib DSL line)
- Both have jump targets

Differences:
- Python is stack-based (push/pop)
- AutoLib stores full condition in one instruction
- Python uses numeric offsets, AutoLib uses line numbers
```

---

#### Phase 3: Execution

**Executor** (`executor.py`):

```python
# Main execution loop
program_counter = 0
while program_counter < len(vm_codes):
    code = vm_codes[program_counter]
    
    # PC=0: switch_device FGT_B
    executor.cur_device = devices['FGT_B']
    
    # PC=1: strset counter 10
    env.set_var("counter", "10")
    
    # PC=2: if_not_goto counter > 5 5
    # Evaluate: counter (10) > 5 → TRUE
    if_stack.push(True)
    program_counter += 1  # Continue to line 3
    
    # PC=3: comment Large value
    print("Large value")
    program_counter += 1
    
    # PC=4: else 7
    if if_stack.top():  # True (if branch executed)
        executor.jump_forward(7)  # Skip else block
        program_counter = 6  # After jump
    
    # PC=6: endif
    if_stack.pop()
    program_counter += 1
    
    # Done
```

**Execution Trace**:
```
PC  VM Code                    Action                      if_stack
--  -------------------------  --------------------------  --------
0   switch_device FGT_B        Set active device           []
1   strset counter 10          counter = 10                []
2   if_not_goto counter > 5 5  Eval: 10 > 5 → TRUE        [True]
                               Continue to PC=3
3   comment Large value        Print "Large value"         [True]
4   else 7                     Stack top=True, jump to 7   [True]
                               PC = 6 after jump
6   endif                      Pop stack                   []
```

**Output**: `Large value`

**Comparison to Python VM**:
```
Python VM:
    - Stack-based (push/pop operands)
    - Numeric instruction offsets
    - Built-in opcodes (LOAD_NAME, COMPARE_OP)
    
AutoLib VM:
    - Hybrid: Stack for control flow (if_stack), not operands
    - DSL line numbers for jumps
    - Schema-driven APIs (any function can be an operation)
```

---

## Side-by-Side Comparison

### Phase 1: Lexical Analysis

| Aspect | Python | AutoLib v3 |
|--------|--------|------------|
| **Tool** | `tokenize` module (C implementation) | Custom `Lexer` class |
| **Algorithm** | Regex + DFA (Deterministic Finite Automaton) | Regex pattern matching |
| **Token Format** | `TokenInfo(type, string, start, end, line)` | `Token(type, data, line_number)` |
| **Types** | 63 token types (NAME, OP, NUMBER, etc.) | 9 types (section, command, api, keyword, etc.) |
| **Whitespace** | Significant (INDENT/DEDENT tokens) | Insignificant (except in strings) |
| **Output** | Token stream (generator) | Token list (stored) |

**Example**:
```
Python:   TokenInfo(NAME, 'x', (1,0), (1,1), 'x = 10\n')
AutoLib:  Token("identifier", "x", 1)

Both capture: Type, Value, Line Number
```

---

### Phase 2: Syntactic Analysis

| Aspect | Python | AutoLib v3 |
|--------|--------|------------|
| **Tool** | PEG parser (since 3.9) / LALR (before 3.9) | Recursive descent parser |
| **Grammar** | `Grammar/python.gram` (formal BNF) | Schema-driven (`cli_syntax.json`) |
| **Intermediate** | AST (Abstract Syntax Tree) | **None** (direct to VM codes) |
| **Structure** | Hierarchical tree (Module → Stmt → Expr) | Flat list of VM codes |
| **Validation** | Syntax rules from grammar | Schema validation |
| **Control Flow** | AST nodes (If, While, For) | VM codes with jump targets |

**Key Difference**: Python builds an AST, AutoLib goes **directly to executable form**.

**Why?**
- **Python**: General-purpose, needs optimization, multiple compilation targets
- **AutoLib**: Domain-specific, simpler semantics, prioritizes compilation speed

---

### Phase 3: Code Generation

| Aspect | Python | AutoLib v3 |
|--------|--------|------------|
| **Input** | AST | Tokens (no intermediate AST) |
| **Output** | Bytecode (.pyc file) | VM Codes (in-memory or .vm file) |
| **Backend** | `compile()` function / compiler package | Parser directly emits VM codes |
| **Optimization** | Constant folding, peephole, AST optimization | Minimal (deprecated command replacement) |
| **Instruction Set** | 120+ bytecode opcodes | ~40 operations (APIs + keywords) |
| **Format** | Binary bytecode (2 bytes per instruction) | Text VM codes (human-readable) |
| **Caching** | .pyc files | In-memory dict (compilation cache) |

**Example**:
```
Python Bytecode:     LOAD_CONST 0 (10)  STORE_NAME 0 (x)
AutoLib VM Code:     2 strset counter 10

Python: Stack-based, numeric opcodes
AutoLib: Direct API calls, named operations
```

---

### Phase 4: Execution

| Aspect | Python | AutoLib v3 |
|--------|--------|------------|
| **Runtime** | PVM (Python Virtual Machine) | Custom Executor |
| **Architecture** | Stack-based VM | Program counter + if_stack hybrid |
| **State** | Call stack, exception stack, value stack | program_counter, if_stack, cur_device |
| **Dispatch** | Giant switch statement on opcode | API handler with dynamic dispatch |
| **Control Flow** | Jump instructions (absolute offsets) | Jump methods (line number search) |
| **Jump Resolution** | Numeric bytecode offset | Scan VM codes for matching line_number |
| **API System** | Built-in functions + C extensions | Auto-discovered Python functions |

**Execution Model**:
```python
# Python VM (simplified)
while True:
    opcode = bytecode[offset]
    if opcode == LOAD_CONST:
        stack.push(consts[arg])
    elif opcode == COMPARE_OP:
        right = stack.pop()
        left = stack.pop()
        stack.push(compare(left, op, right))
    elif opcode == POP_JUMP_IF_FALSE:
        if not stack.pop():
            offset = arg  # Jump to numeric offset
    # ... 120+ opcodes

# AutoLib Executor (simplified)
while program_counter < len(vm_codes):
    code = vm_codes[program_counter]
    if code.operation == "if_not_goto":
        if not eval_expression(code.parameters):
            jump_forward(target_line)  # Scan for line_number
    elif code.operation in API_REGISTRY:
        api_func(executor, params)
    # ... dynamic API dispatch
```

---

## Key Similarities

### 1. Universal Compilation Phases

Both follow the classic compiler pipeline:

```
Source → Lexer → Parser → Code Generation → Execution
```

### 2. Token-Based Lexing

Both use tokens with:
- **Type classification** (keyword, operator, identifier, etc.)
- **Line number tracking** (for error reporting and debugging)
- **Value storage** (the actual text/data)

### 3. Control Flow via Jumps

Both implement control structures using jumps:

**Python**:
```
POP_JUMP_IF_FALSE 22  # Jump to offset 22 if false
JUMP_FORWARD 8        # Jump forward 8 instructions
```

**AutoLib**:
```
if_not_goto counter > 5 103  # Jump to line 103 if false
else 110                     # Jump to line 110
```

### 4. Stack-Based Control Flow

Both use stacks for nested structures:

**Python**: Block stack for loops, try/except, with statements

**AutoLib**: if_stack for nested if/else/while

### 5. Two-Pass Variable Resolution

**Python**: Compile-time name resolution + runtime lookup

**AutoLib**: Compile-time environment variables + runtime user variables

### 6. Extensibility

**Python**: Import system, C extensions

**AutoLib**: Plugin system, custom APIs

---

## Key Differences

### 1. Target Audience

| Python | AutoLib v3 |
|--------|------------|
| General-purpose programming | Domain-specific (FortiOS testing) |
| Any application domain | Device automation only |
| Millions of developers | Internal team |

---

### 2. Grammar Complexity

| Python | AutoLib v3 |
|--------|------------|
| Full programming language | Scripting language (limited constructs) |
| Classes, decorators, comprehensions, etc. | Variables, if/else, while loops, APIs |
| 300+ grammar productions | ~15 syntax patterns |

**Python Grammar** (sample):
```python
statement: compound_stmt | simple_stmt
compound_stmt: if_stmt | while_stmt | for_stmt | try_stmt | with_stmt | funcdef | classdef
if_stmt: 'if' test ':' suite ('elif' test ':' suite)* ['else' ':' suite]
```

**AutoLib Grammar** (schema-based):
```json
{
  "if": {
    "type": "control_block",
    "flow": ["expression", "script", ["elseif", "else", "fi"]]
  }
}
```

---

### 3. AST vs Direct VM Code

| Python | AutoLib v3 |
|--------|------------|
| **Builds AST** | **No AST** |
| Allows optimization passes | Limited optimization |
| Separates parsing from code gen | Parser generates VM codes directly |
| More flexible (multiple backends) | Faster compilation |

**Why the difference?**

- **Python**: Needs optimization (constant folding, loop unrolling), multiple targets (bytecode, machine code via PyPy/Nuitka)
- **AutoLib**: Simpler semantics, single target (custom executor), prioritizes compilation speed

---

### 4. Instruction Format

| Python | AutoLib v3 |
|--------|------------|
| **Binary bytecode** (`.pyc`) | **Text VM codes** (`.vm`) |
| 2 bytes per instruction | Variable length text |
| Opcode + numeric argument | Operation + named parameters |
| Machine-optimized | Human-readable |

**Example**:
```python
# Python bytecode (binary)
b'd\x00}\x00d\x01S\x00'
# Disassembled: LOAD_CONST 0 STORE_NAME 0 LOAD_CONST 1 RETURN_VALUE

# AutoLib VM code (text)
"2 strset counter 10"
```

---

### 5. Jump Resolution

| Python | AutoLib v3 |
|--------|------------|
| **Numeric offsets** | **Line numbers** |
| Direct array indexing | Linear search |
| O(1) jump performance | O(n) jump performance |
| Compact encoding | Human-readable debugging |

**Python Jump**:
```python
offset = 10  # Absolute bytecode offset
bytecode[offset]  # Direct access
```

**AutoLib Jump**:
```python
target_line = 103  # DSL source line number
# Scan VM codes until code.line_number == 103
while vm_codes[pc].line_number != target_line:
    pc += 1
```

---

### 6. Execution Model

| Python | AutoLib v3 |
|--------|------------|
| **Pure stack-based** | **Hybrid** (PC + if_stack) |
| All operands on value stack | Conditions in if_stack, data in variables |
| No named variables in VM | Variables resolved by name |
| Frame objects for scoping | Global variable environment |

**Python Stack Example**:
```python
# x = 10 + 5
LOAD_CONST 0 (10)     # Stack: [10]
LOAD_CONST 1 (5)      # Stack: [10, 5]
BINARY_ADD            # Stack: [15]
STORE_NAME 0 (x)      # Stack: []
```

**AutoLib Example**:
```python
# <intset x 10>
# <intchange x + 5>
strset x 10           # env.vars['x'] = 10
intchange x + 5       # env.vars['x'] = 10 + 5 = 15
```

---

### 7. Schema-Driven vs Grammar-Driven

| Python | AutoLib v3 |
|--------|------------|
| **Formal grammar** (BNF/PEG) | **JSON schema** |
| Grammar parser generators | Custom recursive descent |
| Syntax errors from parser | Schema validation errors |
| Language evolution requires grammar changes | Schema updates (JSON editing) |

**Python Grammar Change** (adding walrus operator):
```python
# Modify Grammar/python.gram
namedexpr_test: test [':=' test]
```

**AutoLib Schema Change** (adding new API):
```json
{
  "new_api": {
    "parse_mode": "options",
    "parameters": {
      "-var": {"alias": "variable", "type": "string"}
    }
  }
}
```

---

## When to Use Each Pattern

### Use Python-Style Compilation (AST-based) When:

✅ **General-purpose language** needs
- Multiple language features (classes, closures, generators, etc.)
- Complex optimization requirements
- Multiple compilation targets (bytecode, machine code, JavaScript)

✅ **Large scale projects**
- Millions of lines of code
- Performance-critical applications
- Long-term evolution (decades)

✅ **IDE/tooling support**
- Static analysis tools
- Code formatters (need AST)
- Refactoring tools

**Examples**: Python, Java, C#, TypeScript, Swift

---

### Use AutoLib-Style Compilation (Direct VM Code) When:

✅ **Domain-specific languages** (DSL)
- Limited, well-defined syntax
- Specific problem domain (not general-purpose)
- Fast compilation is priority

✅ **Embedded scripting**
- Configuration languages
- Automation scripts
- Test frameworks

✅ **Rapid development**
- Frequent syntax changes
- Schema-based evolution
- Quick prototyping

✅ **Human-readable intermediate**
- Debugging is critical
- Users need to understand compiled form
- Educational purposes

**Examples**: AutoLib v3, SQL, Regular Expressions, Make, Ansible YAML, Dockerfile

---

## Summary Comparison Table

| Feature | Python | AutoLib v3 |
|---------|--------|------------|
| **Type** | General-purpose language | Domain-specific language (DSL) |
| **Lexer** | tokenize module (C) | Custom Lexer (Python + regex) |
| **Parser** | PEG parser | Recursive descent (schema-driven) |
| **Intermediate** | AST (Abstract Syntax Tree) | None (direct to VM codes) |
| **Code Format** | Binary bytecode (.pyc) | Text VM codes (.vm) |
| **Instruction Set** | 120+ opcodes | ~40 operations (APIs) |
| **Execution Model** | Stack-based VM | PC + if_stack hybrid |
| **Jump Resolution** | Numeric offsets (O(1)) | Line numbers (O(n) scan) |
| **Variable Access** | Frame locals/globals (index-based) | Named environment variables |
| **Control Flow** | Jump bytecode instructions | Jump methods with line search |
| **API System** | Built-in functions + imports | Auto-discovered plugin APIs |
| **Optimization** | Extensive (constant folding, etc.) | Minimal (deprecated commands) |
| **Caching** | .pyc files on disk | In-memory dict |
| **Error Reporting** | Bytecode offset + source mapping | Direct line number (1:1 mapping) |
| **Debugging** | Requires dis module | VM codes are human-readable |
| **Extensibility** | Import system, C API | Plugin system, schema updates |
| **Performance** | Highly optimized (CPython, PyPy) | Sufficient for automation tasks |
| **Learning Curve** | Steep (complex VM, many opcodes) | Gentle (simple VM, readable codes) |

---

## Visual Comparison: Compilation Flow

### Python Pipeline

```
if x > 5:          →  [IF, NAME(x), OP(>), INT(5), COLON]
    print("Hi")       [INDENT, NAME(print), OP("("), STRING("Hi"), ...]
                      
                   →  If(
                        test=Compare(x > 5),
                        body=[Call(print, ["Hi"])]
                      )
                      
                   →  LOAD_NAME 0 (x)
                      LOAD_CONST 1 (5)
                      COMPARE_OP 4 (>)
                      POP_JUMP_IF_FALSE 22
                      LOAD_NAME 1 (print)
                      LOAD_CONST 2 ("Hi")
                      CALL_FUNCTION 1
                      
                   →  Stack manipulations, function calls, output
```

### AutoLib Pipeline

```
<if {$x} > 5>      →  [Token("keyword", "if", 3), 
    comment Hi         Token("variable", "x", 3),
<fi>                   Token("operator", ">", 3), ...]
                      
                   →  (No AST step)
                      
                   →  3 if_not_goto x > 5 5
                      4 comment Hi
                      5 endif
                      
                   →  if_stack.push(eval(x > 5))
                      print("Hi") if stack.top()
                      if_stack.pop()
```

---

## Conclusion

### Python's Approach: Flexibility & Optimization

- **AST intermediate** enables powerful optimizations
- **Stack-based VM** is well-studied, efficient
- **Binary bytecode** maximizes performance
- **Cost**: Complex implementation, harder to debug

### AutoLib's Approach: Simplicity & Readability

- **Direct VM code generation** is faster to compile
- **Text-based codes** are human-readable and debuggable
- **Schema-driven** makes language evolution easier
- **Cost**: Less optimization, slower jump resolution

### The Right Choice

Both are **correct** approaches for their domains:

- **Python**: Needs AST for general-purpose language features and optimization
- **AutoLib**: Benefits from direct compilation for DSL simplicity and debugging

**Key Insight**: Compiler architecture should match the **problem domain** and **user needs**, not follow trends blindly.

---

## Further Reading

### Python Internals
- [Python Developer's Guide - Parser](https://devguide.python.org/internals/parser/)
- [CPython Bytecode](https://docs.python.org/3/library/dis.html)
- [Python AST Module](https://docs.python.org/3/library/ast.html)

### Compiler Theory
- *Compilers: Principles, Techniques, and Tools* (Dragon Book)
- *Engineering a Compiler* by Cooper & Torczon
- [Crafting Interpreters](https://craftinginterpreters.com/) by Robert Nystrom

### AutoLib v3 Documentation
- [Compiler Deep Dive](COMPILER_DEEP_DIVE.md) - Implementation details
- [Executor Deep Dive](EXECUTOR_DEEP_DIVE.md) - Execution model
- [DSL Compilation Flow](DSL_COMPILATION_FLOW.md) - High-level pipeline

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-18  
**Framework**: AutoLib v3 V3R10B0007
