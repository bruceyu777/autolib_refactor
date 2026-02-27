# AutoLib v3 Documentation Index

**Framework Version**: V3R10B0007  
**Last Updated**: 2026-02-18

---

## 📚 Documentation Structure

### 🏗️ Architecture & Design

| Document | Purpose | Audience | Difficulty |
|----------|---------|----------|-----------|
| [**Software Architecture & Design Patterns**](SOFTWARE_ARCHITECTURE_DESIGN_PATTERNS.md) | Compare design alternatives for DSL frameworks, analyze AutoLib v3's architectural choices, evaluate trade-offs | Architects, Senior Developers | Advanced |
| [**Python-Based Testing Framework**](PYTHON_BASED_TESTING_FRAMEWORK.md) | Architecture for pytest-based testing reusing AutoLib v3 device/services layer, migration from DSL to Python | Architects, Python Developers | Advanced |
| [**Compiler Architecture Comparison**](COMPILER_ARCHITECTURE_COMPARISON.md) | Understand general compiler concepts using Python as example, compare with AutoLib v3's approach | Developers, Students | Intermediate |
| [**AutoLib v3 Workflow**](AUTOLIB_V3_WORKFLOW.md) | High-level overview of complete framework workflow from script to execution | All Users | Beginner |

---

### 🔧 Compiler & Execution

| Document | Purpose | Audience | Difficulty |
|----------|---------|----------|-----------|
| [**Compiler Deep Dive**](COMPILER_DEEP_DIVE.md) | Detailed internals of lexer, parser, control flow compilation, line number tracking | Core Developers | Advanced |
| [**Executor Deep Dive**](EXECUTOR_DEEP_DIVE.md) | VM code execution model, program counter, if_stack, API dispatch | Core Developers | Advanced |
| [**DSL Compilation Flow**](DSL_COMPILATION_FLOW.md) | 5-stage compilation pipeline from DSL to VM codes | Developers | Intermediate |
| [**DSL to Execution Example**](DSL_TO_EXECUTION_EXAMPLE.md) | End-to-end walkthrough of real test case compilation and execution | All Developers | Beginner |

---

### � Migration & Tooling

| Document | Purpose | Audience | Difficulty |
|----------|---------|----------|-----------|
| [**DSL to pytest Migration**](DSL_TO_PYTEST_MIGRATION.md) | Automated DSL-to-pytest conversion, fluent API design, migration strategy for 200+ tests | Architects, Python Developers | Advanced || [**Transpiler Example**](TRANSPILER_EXAMPLE.md) | Real test conversion walkthrough (205817.txt), validation, readability comparison | All Developers | Intermediate |
---

### �📖 User Guides

| Document | Purpose | Audience | Difficulty |
|----------|---------|----------|-----------|
| [**Component Reusability Guide**](COMPONENT_REUSABILITY_GUIDE.md) | Quick reference for reusing AutoLib v3 components in Python projects, migration checklist | Python Developers | Beginner |
| [**Variable Usage & Troubleshooting**](VARIABLE_USAGE_AND_TROUBLESHOOTING.md) | Variable syntax, interpolation, environment vs user variables, debugging | QA Engineers, Test Writers | Beginner |
| [**Include Directive**](INCLUDE_DIRECTIVE.md) | Script modularization, reusable components, include path resolution | Test Writers | Beginner |

---

## 🗺️ Documentation Navigation Guide

### I'm a... → Start here:

#### **QA Engineer / Test Writer**
1. Start: [AutoLib v3 Workflow](AUTOLIB_V3_WORKFLOW.md) - Get the big picture
2. Then: [Variable Usage & Troubleshooting](VARIABLE_USAGE_AND_TROUBLESHOOTING.md) - Master variables
3. Then: [Include Directive](INCLUDE_DIRECTIVE.md) - Organize tests
4. Reference: [DSL to Execution Example](DSL_TO_EXECUTION_EXAMPLE.md) - Real-world example

#### **New Developer / Contributor**
1. Start: [AutoLib v3 Workflow](AUTOLIB_V3_WORKFLOW.md) - Understand framework
2. Then: [DSL Compilation Flow](DSL_COMPILATION_FLOW.md) - Compilation basics
3. Then: [Compiler Deep Dive](COMPILER_DEEP_DIVE.md) - Implementation details
4. Then: [Executor Deep Dive](EXECUTOR_DEEP_DIVE.md) - Execution model
5. Reference: [DSL to Execution Example](DSL_TO_EXECUTION_EXAMPLE.md) - Trace real code

#### **Architect / Designer**
1. Start: [Software Architecture & Design Patterns](SOFTWARE_ARCHITECTURE_DESIGN_PATTERNS.md) - Design decisions
2. Then: [Compiler Architecture Comparison](COMPILER_ARCHITECTURE_COMPARISON.md) - Context vs mainstream
3. Then: [Compiler Deep Dive](COMPILER_DEEP_DIVE.md) - Implementation approach
4. Then: [Executor Deep Dive](EXECUTOR_DEEP_DIVE.md) - Execution strategy
5. Alternative: [Python-Based Testing Framework](PYTHON_BASED_TESTING_FRAMEWORK.md) - pytest approach

#### **Building Python/pytest Tests (No DSL)**
1. **Start**: [Python-Based Testing Framework](PYTHON_BASED_TESTING_FRAMEWORK.md) - Complete architecture and guide
2. **Quick Ref**: [Component Reusability Guide](COMPONENT_REUSABILITY_GUIDE.md) - What to copy, what to skip
3. **Reference**: [AutoLib v3 Workflow](AUTOLIB_V3_WORKFLOW.md) - Understand device/services layer
4. **Reuse**: Device and Services modules (no compiler/executor needed)

#### **Migrating Existing DSL Tests to pytest**
1. **Start**: [DSL to pytest Migration](DSL_TO_PYTEST_MIGRATION.md) - Automated conversion strategy
2. **Concrete Example**: [Transpiler Example](TRANSPILER_EXAMPLE.md) - Real 205817.txt conversion walkthrough
3. **Architecture**: [Python-Based Testing Framework](PYTHON_BASED_TESTING_FRAMEWORK.md) - pytest framework design
4. **API Reuse**: [DSL to pytest Migration](DSL_TO_PYTEST_MIGRATION.md) - How to reuse existing APIs
5. **Tooling**: [DSL to pytest Migration](DSL_TO_PYTEST_MIGRATION.md) - Transpiler and validation tools

#### **Student / Learning Compilers**
1. Start: [Compiler Architecture Comparison](COMPILER_ARCHITECTURE_COMPARISON.md) - General concepts
2. Then: [DSL Compilation Flow](DSL_COMPILATION_FLOW.md) - Simple pipeline
3. Then: [Compiler Deep Dive](COMPILER_DEEP_DIVE.md) - Real implementation
4. Compare: [Software Architecture & Design Patterns](SOFTWARE_ARCHITECTURE_DESIGN_PATTERNS.md) - Design alternatives

---

## 📋 Topic Index

### Architecture Topics
- Design patterns (Command, Strategy, Factory, Observer, Template Method)
- Alternative architectures (Interpreter, AST Compiler, Embedded Python)
- Trade-off analysis (simplicity vs performance vs features)
- Evolution and scalability paths
- When to use which pattern

### Compiler Topics
- Lexical analysis (tokenization, regex patterns)
- Syntactic analysis (recursive descent, schema-driven parsing)
- Control flow compilation (if/else/while, forward/backward jumps)
- Line number tracking (source line to jump target)
- VM code generation (direct emission, no AST)
- Compilation caching

### Execution Topics
- Program counter mechanism
- if_stack control flow management
- Jump resolution (forward jumps, backward loops)
- API dispatch and parameter handling
- Device context switching
- Variable interpolation at runtime

### Variable Topics
- Syntax: `$VAR` vs `{$VAR}`
- Environment variables (compile-time)
- User variables (runtime: strset, intset, setvar)
- Interpolation timing
- Troubleshooting common issues

### Control Flow Topics
- If/elseif/else/fi constructs
- While/endwhile loops
- Loop/until constructs
- Nested control flow
- Break/continue support

---

## 🔍 Quick Reference

### Common Questions → Documentation Links

| Question | See Document | Section |
|----------|-------------|---------|
| How does compilation work? | [DSL Compilation Flow](DSL_COMPILATION_FLOW.md) | Full document |
| Why no AST? | [Software Architecture](SOFTWARE_ARCHITECTURE_DESIGN_PATTERNS.md) | Decision 1 |
| How to use pytest instead of DSL? | [Python-Based Testing Framework](PYTHON_BASED_TESTING_FRAMEWORK.md) | Full document |
| How to migrate DSL tests to pytest? | [DSL to pytest Migration](DSL_TO_PYTEST_MIGRATION.md) | Full document |
| Can AutoLib v3 APIs be reused in pytest? | [DSL to pytest Migration](DSL_TO_PYTEST_MIGRATION.md) | API Reusability Analysis |
| How to auto-convert DSL to pytest? | [DSL to pytest Migration](DSL_TO_PYTEST_MIGRATION.md) | DSL Transpiler Architecture |
| How to make Python tests readable? | [DSL to pytest Migration](DSL_TO_PYTEST_MIGRATION.md) | Fluent API Design |
| Which AutoLib v3 components can I reuse? | [Python-Based Testing Framework](PYTHON_BASED_TESTING_FRAMEWORK.md) | Reusable Components |
| How are variables resolved? | [Variable Usage](VARIABLE_USAGE_AND_TROUBLESHOOTING.md) | Variable Resolution |
| How do jumps work? | [Compiler Deep Dive](COMPILER_DEEP_DIVE.md) | Control Flow Linking |
| How is the if_stack used? | [Executor Deep Dive](EXECUTOR_DEEP_DIVE.md) | Control Flow Management |
| How to add new API? | [AutoLib v3 Workflow](AUTOLIB_V3_WORKFLOW.md) | Custom API Development |
| Why not use Python directly? | [Software Architecture](SOFTWARE_ARCHITECTURE_DESIGN_PATTERNS.md) | Option 3 Analysis |
| DSL vs Python: which to choose? | [Software Architecture](SOFTWARE_ARCHITECTURE_DESIGN_PATTERNS.md) | Decision Tree |
| How to migrate from DSL to Python? | [Python-Based Testing Framework](PYTHON_BASED_TESTING_FRAMEWORK.md) | Migration from DSL |
| How fast is compilation? | [Compiler Architecture Comparison](COMPILER_ARCHITECTURE_COMPARISON.md) | Performance Comparison |
| What design patterns are used? | [Software Architecture](SOFTWARE_ARCHITECTURE_DESIGN_PATTERNS.md) | Design Pattern Deep Dive |
| How to debug tests? | [AutoLib v3 Workflow](AUTOLIB_V3_WORKFLOW.md) | Debug Support |

---

## 📊 Documentation Metrics

| Metric | Value |
|--------|-------|
| Total Documents | 12 |
| Total Pages (estimated) | ~400 |
| Code Examples | 300+ |
| Diagrams | 35+ |
| Coverage | Architecture, Compiler, Execution, User Guide, Python/pytest, Migration, Tooling, Real Examples |
| Last Major Update | 2026-02-18 |

---

## 🤝 Contributing to Documentation

### Documentation Standards

**Structure**:
- Start with Table of Contents
- Use clear section headers
- Include code examples
- Add diagrams where helpful
- Cross-reference related docs

**Code Examples**:
- Show both DSL and implementation
- Include expected output
- Explain line-by-line for complex cases
- Use real-world scenarios

**Style**:
- Write for your audience (QA vs Developer vs Architect)
- Use tables for comparisons
- Use bullet points for lists
- Highlight key insights with **bold**
- Mark important notes with ⚠️

### Adding New Documentation

1. Create file in `docs/` folder
2. Follow naming convention: `TOPIC_NAME.md`
3. Add to this index under appropriate section
4. Add to [AUTOLIB_V3_WORKFLOW.md](AUTOLIB_V3_WORKFLOW.md) "Deep Dive Topics" if relevant
5. Cross-reference from related documents

---

## 📝 Changelog

### 2026-02-18 - Major Release: Python/pytest Framework Documentation & Migration Tooling
- ✅ **NEW**: [DSL to pytest Migration](DSL_TO_PYTEST_MIGRATION.md) - Automated conversion strategy, fluent API design, transpiler architecture
  - API reusability analysis (how to reuse existing AutoLib v3 APIs in pytest)
  - Automated DSL→pytest transpiler design (VM codes → Python AST → formatted pytest)
  - Fluent API patterns for readability (method chaining, context managers, assertion helpers)
  - Migration tools (transpiler CLI, validation tool, coverage analyzer)
  - Readability comparison (DSL vs naive Python vs fluent API vs structured builder)
  - 9-week implementation plan
- ✅ **NEW**: [Transpiler Example](TRANSPILER_EXAMPLE.md) - Real test conversion walkthrough
  - Step-by-step conversion of real test case (205817.txt - IPS sensor deletion)
  - Shows complete transpiler workflow (DSL → VM codes → Python AST → pytest)
  - Validation results (100% match with DSL execution)
  - Readability analysis (84% of DSL clarity retained)
  - Conversion metrics and statistics
- ✅ **NEW**: [Python-Based Testing Framework](PYTHON_BASED_TESTING_FRAMEWORK.md) - Complete architecture for pytest-based testing
- ✅ **NEW**: [Component Reusability Guide](COMPONENT_REUSABILITY_GUIDE.md) - Quick reference for component reuse
- ✅ Added [Software Architecture & Design Patterns](SOFTWARE_ARCHITECTURE_DESIGN_PATTERNS.md) - 6 architecture alternatives analyzed
- ✅ Added [Compiler Architecture Comparison](COMPILER_ARCHITECTURE_COMPARISON.md) - Python vs AutoLib v3
- ✅ Enhanced [Compiler Deep Dive](COMPILER_DEEP_DIVE.md) with line number mechanism
- ✅ Created comprehensive documentation index (README.md)
- ✅ Updated quick reference with migration questions

### Previous Updates
- Created [Compiler Deep Dive](COMPILER_DEEP_DIVE.md)
- Created [Executor Deep Dive](EXECUTOR_DEEP_DIVE.md)
- Created [Variable Usage & Troubleshooting](VARIABLE_USAGE_AND_TROUBLESHOOTING.md)
- Created [Include Directive](INCLUDE_DIRECTIVE.md)
- Created [DSL to Execution Example](DSL_TO_EXECUTION_EXAMPLE.md)

---

## 📬 Feedback

Documentation questions or suggestions? Contact the AutoLib v3 team or create an issue in the project repository.

---

**Happy Testing! 🚀**
