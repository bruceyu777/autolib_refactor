# DSL to pytest Migration Prototype

**Test Case**: 205812.txt - IPS custom signature persistence after reboot  
**Environment**: env.fortistack.ips.conf  
**Date**: 2026-02-23

## Prototype Structure

```
prototype/
├── README.md                    # This file
├── sample_includes/             # Sample include files (DSL)
│   ├── govdom1.txt
│   └── outvdom.txt
├── tools/                       # Transpiler tools
│   ├── conversion_registry.py  # Registry implementation
│   ├── include_converter.py    # Include → fixture converter
│   └── dsl_transpiler.py       # Main transpiler
├── output/                      # Generated pytest files
│   ├── conftest.py             # Auto-generated fixtures
│   ├── test_205812.py          # Converted test
│   └── .conversion_registry.json  # Tracking database
└── fluent_api/                 # Fluent API implementation
    └── fluent.py               # FluentFortiGate, TestBed
```

## Workflow

**Step 1**: Convert includes to fixtures
```bash
python prototype/tools/include_converter.py \
    prototype/sample_includes/govdom1.txt \
    prototype/output/
```

**Step 2**: Convert test with fixture injection
```bash
python prototype/tools/dsl_transpiler.py \
    testcase/ips/topology1/205812.txt \
    prototype/output/test_205812.py
```

**Step 3**: Run pytest test
```bash
cd prototype/output
pytest test_205812.py -v
```

## Key Features Demonstrated

✅ Include dependency resolution  
✅ Fixture generation from includes  
✅ Conversion registry tracking  
✅ Fixture parameter injection  
✅ Fluent API usage  
✅ Multi-device support (FGT_A, PC_05)  
✅ QAID result tracking  
