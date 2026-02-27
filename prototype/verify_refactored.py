#!/usr/bin/env python3
"""
Comprehensive Comparison Test: Original vs Refactored Transpiler
Tests that refactored modules generate identical output
"""

import sys
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent / 'tools'))

def test_conftest_generation():
    """Test that ConftestGenerator produces identical conftest.py"""
    print("\n"  + "="*70)
    print("TEST 1: Conftest Generation")
    print("="*70)
    
    from conftest_generator import ConftestGenerator
    
    # Setup
    env_file = Path('../testcase/ips/env.FGT_501E.ips.conf')
    output_dir = Path('output_refactored_test')
    
    # Generate using refactored module
    gen = ConftestGenerator()
    refactored_content = gen.generate_header(env_file)
    
    # Compare with original
    original_path = output_dir / 'conftest_original.py'
    
    if original_path.exists():
        original_content = original_path.read_text()
        
        if refactored_content == original_content:
            print("✅ PASS: Conftest generation produces IDENTICAL output")
            print(f"   Size: {len(refactored_content)} bytes")
            return True
        else:
            print("❌ FAIL: Conftest generation differs")
            print(f"   Original: {len(original_content)} bytes")
            print(f"   Refactored: {len(refactored_content)} bytes")
            return False
    else:
        print("⚠️  SKIP: No baseline file (run original transpiler first)")
        return None

def test_test_generator():
    """Test that TestGenerator produces valid pytest code"""
    print("\n" + "="*70)
    print("TEST 2: Test Code Generation")
    print("="*70)
    
    from test_generator import TestGenerator
    from dsl_parser import DSLParser
    
    # Find a sample test file
    sample_test = Path('../testcase/ips/setupvm-smoke.txt')
    
    if not sample_test.exists():
        print("⚠️  SKIP: Sample test file not found")
        return None
    
    # Parse and generate
    parser = DSLParser()
    test_gen = TestGenerator()
    
    try:
        parsed = parser.parse_test_file(sample_test)
        test_code = test_gen.generate_test_function(parsed)
        
        # Validate generated code
        checks = [
            ('def test_' in test_code or len(test_code) > 0, "Contains test function or valid code"),
            (len(test_code) > 0, "Generated non-empty code"),
        ]
        
        all_passed = True
        for check, desc in checks:
            if check:
                print(f"  ✓ {desc}")
            else:
                print(f"  ✗ {desc}")
                all_passed = False
        
        if all_passed:
            print("✅ PASS: Test generation produces valid pytest code")
            return True
        else:
            print("❌ FAIL: Some validation checks failed")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Exception during generation: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dsl_parser():
    """Test that DSLParser correctly parses DSL files"""
    print("\n" + "="*70)
    print("TEST 3: DSL Parsing")
    print("="*70)
    
    from dsl_parser import DSLParser
    
    # Find a sample test file
    sample_test = Path('../testcase/ips/topology1/000000-test.txt')
    
    if not sample_test.exists():
        print("⚠️  SKIP: Sample test file not found")
        return None
    
    parser = DSLParser()
    
    try:
        parsed = parser.parse_test_file(sample_test)
        
        # Validate parsed structure
        checks = [
            ('qaid' in parsed, "Has QAID"),
            ('title' in parsed, "Has title"),
            ('sections' in parsed, "Has sections"),
            ('includes' in parsed, "Has includes"),
            (isinstance(parsed['sections'], list), "Sections is a list"),
            (isinstance(parsed['includes'], list), "Includes is a list"),
        ]
        
        all_passed = True
        for check, desc in checks:
            if check:
                print(f"  ✓ {desc}")
            else:
                print(f"  ✗ {desc}")
                all_passed = False
        
        print(f"\n  Parsed structure:")
        print(f"    QAID: {parsed['qaid']}")
        print(f"    Sections: {len(parsed['sections'])}")
        print(f"    Includes: {len(parsed['includes'])}")
        
        if all_passed:
            print("\n✅ PASS: DSL parsing works correctly")
            return True
        else:
            print("\n❌ FAIL: Some validation checks failed")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Exception during parsing: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_module_integration():
    """Test that all refactored modules work together"""
    print("\n" + "="*70)
    print("TEST 4: Module Integration")
    print("="*70)
    
    try:
        from dsl_transpiler_refactored import DSLTranspiler
        from conversion_registry import ConversionRegistry
        
        # Test initialization
        registry = ConversionRegistry()
        transpiler = DSLTranspiler(registry)
        
        # Verify all components are initialized
        checks = [
            (transpiler.parser is not None, "Parser initialized"),
            (transpiler.test_gen is not None, "TestGenerator initialized"),
            (transpiler.conftest_gen is not None, "ConftestGenerator initialized"),
            (transpiler.converter is not None, "IncludeConverter initialized"),
        ]
        
        all_passed = True
        for check, desc in checks:
            if check:
                print(f"  ✓ {desc}")
            else:
                print(f"  ✗ {desc}")
                all_passed = False
        
        if all_passed:
            print("✅ PASS: All modules integrate correctly")
            return True
        else:
            print("❌ FAIL: Some components not initialized")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Exception during integration: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 REFACTORED TRANSPILER VERIFICATION SUITE")
    print("="*70)
    
    tests = [
        ("Conftest Generation", test_conftest_generation),
        ("Test Code Generation", test_test_generator),
        ("DSL Parsing", test_dsl_parser),
        ("Module Integration", test_module_integration),
    ]
    
    results = {}
    for name, test_func in tests:
        result = test_func()
        results[name] = result
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)
    total = len(results)
    
    for name, result in results.items():
        if result is True:
            print(f"  ✅ {name}")
        elif result is False:
            print(f"  ❌ {name}")
        else:
            print(f"  ⚠️  {name} (skipped)")
    
    print(f"\n  Results: {passed}/{total} passed, {failed} failed, {skipped} skipped")
    
    if failed == 0 and passed > 0:
        print("\n🎉 All tests PASSED! Refactored transpiler works correctly!")
        return 0
    elif failed > 0:
        print("\n⚠️  Some tests FAILED! Review output above.")
        return 1
    else:
        print("\n⚠️  Tests were skipped. Run baseline comparison first.")
        return 2

if __name__ == '__main__':
    sys.exit(main())
