# Quick Reference Card - DSL to pytest Migration

## 🎯 All Files You Can Check

### 1. Original DSL Test
```bash
# View original test
cat /home/fosqa/autolibv3/autolib_v3/testcase/ips/topology1/205812.txt

# 73 lines, includes 2 include directives, 4 device sections
```

### 2. Generated pytest Test
```bash
# View generated test
cat /home/fosqa/autolibv3/autolib_v3/prototype/output/test_205812.py

# 83 lines, uses fixtures, Python code, fully debuggable
```

### 3. Generated Fixtures
```bash
# View generated fixtures
cat /home/fosqa/autolibv3/autolib_v3/prototype/output/conftest.py

# 71 lines, auto-generated from include files
```

### 4. Conversion Registry
```bash
# View tracking database
cat /home/fosqa/autolibv3/autolib_v3/prototype/output/.conversion_registry.json | python3 -m json.tool

# Tracks: govdom1.txt → setup_govdom1, outvdom.txt → cleanup_outvdom
```

### 5. Fluent API Implementation
```bash
# View fluent API
cat /home/fosqa/autolibv3/autolib_v3/prototype/fluent_api/fluent.py       # 200+ lines
cat /home/fosqa/autolibv3/autolib_v3/prototype/fluent_api/mock_device.py  # 130+ lines
```

### 6. Transpiler Tools
```bash
# View transpiler components
cat /home/fosqa/autolibv3/autolib_v3/prototype/tools/conversion_registry.py  # Registry tracker
cat /home/fosqa/autolibv3/autolib_v3/prototype/tools/include_converter.py   # Include→fixture
cat /home/fosqa/autolibv3/autolib_v3/prototype/tools/dsl_transpiler.py      # Main transpiler
```

### 7. Documentation
```bash
# View comprehensive guides
cat /home/fosqa/autolibv3/autolib_v3/prototype/MIGRATION_PROCESS_GUIDE.md  # Complete process
cat /home/fosqa/autolibv3/autolib_v3/prototype/PROTOTYPE_SUMMARY.md        # Prototype summary
```

---

## 🚀 Quick Commands

### Run Complete Migration
```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype
python3 run_transpiler.py
```

### Compare All Formats
```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype
python3 compare_formats.py
```

### View Generated Files
```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype/output
ls -lh                  # See all generated files
cat test_205812.py      # View pytest test
cat conftest.py         # View fixtures
```

### Run Generated Test
```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype/output
pytest -v test_205812.py              # Run test
pytest -v -s test_205812.py           # Run with output
pytest -v -s --pdb test_205812.py     # Run with debugger
```

---

## 📊 Migration Process (5 Steps)

```
Original DSL (205812.txt)
          ↓
    [1. Parse DSL]
          ↓
    [2. Initialize conftest.py]
          ↓
    [3. Convert includes → fixtures]
    • govdom1.txt → setup_govdom1
    • outvdom.txt → cleanup_outvdom
          ↓
    [4. Update registry]
          ↓
    [5. Generate test_205812.py]
          ↓
Generated pytest (test_205812.py + conftest.py)
```

---

## 🔍 Generated vmcode (AutoLib v3)

**To generate vmcode from DSL**:
```bash
cd /home/fosqa/autolibv3/autolib_v3
python3 autotest.py testcase/ips/topology1/205812.txt

# View generated vmcode
cat outputs/205812/vmcode.txt
ls -lh outputs/205812/
```

**Note**: vmcode is the intermediate bytecode format used by AutoLib v3's VM executor. The pytest migration bypasses this and generates direct Python code instead.

---

## 📁 File Tree

```
/home/fosqa/autolibv3/autolib_v3/
│
├── testcase/ips/topology1/
│   └── 205812.txt                     ← 1. Original DSL test (START HERE)
│
├── outputs/205812/
│   └── vmcode.txt                     ← 2. AutoLib v3 generated vmcode
│
└── prototype/
    ├── output/
    │   ├── test_205812.py             ← 3. Generated pytest test
    │   ├── conftest.py                ← 4. Generated fixtures
    │   └── .conversion_registry.json  ← 5. Tracking database
    │
    ├── fluent_api/
    │   ├── fluent.py                  ← 6. Fluent API
    │   └── mock_device.py             ← 7. Mock device
    │
    ├── tools/
    │   ├── conversion_registry.py     ← 8. Registry tracker
    │   ├── include_converter.py       ← 9. Include converter
    │   └── dsl_transpiler.py          ← 10. Main transpiler
    │
    ├── run_transpiler.py              ← Quick runner
    ├── compare_formats.py             ← Format comparison tool
    ├── MIGRATION_PROCESS_GUIDE.md     ← Complete guide
    └── PROTOTYPE_SUMMARY.md           ← Summary doc
```

---

## 🔢 Stats

| Item | Count |
|------|-------|
| **Original DSL lines** | 73 |
| **Generated pytest lines** | 83 |
| **Generated fixtures lines** | 71 |
| **Include files converted** | 2 (govdom1.txt, outvdom.txt) |
| **Device sections** | 4 (3x FGT_A, 1x PC_05) |
| **Expect assertions** | 7 |
| **Conversion tools** | 3 (registry, converter, transpiler) |
| **Total prototype code** | ~1000 lines |

---

## ✅ What You Can Verify

1. **DSL parsing** - Check [tools/dsl_transpiler.py](tools/dsl_transpiler.py) `parse_test_file()`
2. **Include detection** - See regex patterns in `extract_includes()`
3. **Fixture generation** - Check [tools/include_converter.py](tools/include_converter.py) `convert_to_fixture()`
4. **Command grouping** - See `_group_commands()` for config block merging
5. **Quote handling** - Check `_quote_command()` for proper escaping
6. **Registry tracking** - View [tools/conversion_registry.py](tools/conversion_registry.py)
7. **Multi-device support** - See `convert_section()` context managers

---

## 💡 Key Insights

### DSL → vmcode (AutoLib v3 way)
```
DSL text → Lexer → Parser → Compiler → vmcode (bytecode) → VM Executor
```

### DSL → pytest (New way)
```
DSL text → Parser → Transpiler → Python code → pytest framework
```

**Advantages of pytest approach**:
- ✅ No intermediate bytecode
- ✅ Direct Python execution
- ✅ Full IDE support
- ✅ Standard debugging tools
- ✅ Native Python ecosystem access

---

## 🎓 Learning Path

1. **Start here**: Run comparison
   ```bash
   cd /home/fosqa/autolibv3/autolib_v3/prototype
   python3 compare_formats.py
   ```

2. **View original DSL**
   ```bash
   cat /home/fosqa/autolibv3/autolib_v3/testcase/ips/topology1/205812.txt
   ```

3. **View generated pytest**
   ```bash
   cat output/test_205812.py
   cat output/conftest.py
   ```

4. **Understand conversion**
   ```bash
   cat tools/dsl_transpiler.py | less
   ```

5. **Run the test**
   ```bash
   cd output && pytest -v test_205812.py
   ```

---

## 📞 Need Help?

- **See full process**: `cat MIGRATION_PROCESS_GUIDE.md`
- **See prototype summary**: `cat PROTOTYPE_SUMMARY.md`
- **Run comparison**: `python3 compare_formats.py`
- **Check registry stats**: `cd tools && python3 conversion_registry.py`

---

**Ready to migrate 200+ tests? This prototype proves it's viable! 🚀**
