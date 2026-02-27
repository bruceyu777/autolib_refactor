#!/bin/bash
echo "=========================================="
echo "Full Integration Test - Environment + Decorator"
echo "=========================================="
echo ""

echo "Test 1: Variable Resolution (Standalone)"
echo "-----------------------------------"
python3 test_variable_resolution.py | tail -15
echo ""

echo "Test 2: Decorator Resolution (All Methods)"
echo "-----------------------------------"
python3 test_decorator_resolution.py | tail -15
echo ""

echo "Test 3: pytest Integration (QAID 205812)"
echo "-----------------------------------"
cd output
pytest test__205812.py -v 2>&1 | grep -E "(PASS|FAIL|passed|failed)" | head -10
cd ..

echo ""
echo "=========================================="
echo "✅ Full Integration Test Complete!"
echo "=========================================="
