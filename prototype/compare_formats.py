#!/usr/bin/env python3
"""
Compare DSL, vmcode (if available), and pytest formats
Shows the migration transformation side-by-side
"""

from pathlib import Path
import sys


def print_section(title, content, width=80):
    """Print a formatted section"""
    print("\n" + "="*width)
    print(f" {title}")
    print("="*width)
    print(content)


def read_file_safe(filepath):
    """Read file safely, return content or error message"""
    try:
        with open(filepath) as f:
            return f.read()
    except FileNotFoundError:
        return f"[File not found: {filepath}]"
    except Exception as e:
        return f"[Error reading file: {e}]"


def main():
    # File paths
    dsl_file = Path('/home/fosqa/autolibv3/autolib_v3/testcase/ips/topology1/205812.txt')
    vmcode_file = Path('/home/fosqa/autolibv3/autolib_v3/outputs/205812/vmcode.txt')
    pytest_file = Path(__file__).parent / 'output' / 'test_205812.py'
    conftest_file = Path(__file__).parent / 'output' / 'conftest.py'
    
    print("\n" + "🔍 DSL to pytest Migration Comparison".center(80, "="))
    print("Test Case: 205812 (IPS Custom Signature Persistence)".center(80))
    
    # 1. Original DSL
    dsl_content = read_file_safe(dsl_file)
    # Show first 50 lines
    dsl_preview = '\n'.join(dsl_content.split('\n')[:50])
    print_section("1. ORIGINAL DSL (205812.txt)", dsl_preview)
    print(f"\nTotal lines: {len(dsl_content.split(chr(10)))}")
    print(f"File location: {dsl_file}")
    
    # 2. Generated vmcode (if exists)
    vmcode_content = read_file_safe(vmcode_file)
    if "[File not found" in vmcode_content:
        print_section("2. GENERATED VMCODE (Not Generated Yet)", 
                     "To generate vmcode:\n"
                     "  cd /home/fosqa/autolibv3/autolib_v3\n"
                     "  python3 autotest.py testcase/ips/topology1/205812.txt\n"
                     "  cat outputs/205812/vmcode.txt")
    else:
        # Show first 50 lines
        vmcode_preview = '\n'.join(vmcode_content.split('\n')[:50])
        print_section("2. GENERATED VMCODE (AutoLib v3 Compiler)", vmcode_preview)
        print(f"\nTotal lines: {len(vmcode_content.split(chr(10)))}")
        print(f"File location: {vmcode_file}")
    
    # 3. Generated pytest test
    pytest_content = read_file_safe(pytest_file)
    print_section("3. GENERATED PYTEST TEST (test_205812.py)", pytest_content)
    print(f"\nTotal lines: {len(pytest_content.split(chr(10)))}")
    print(f"File location: {pytest_file}")
    
    # 4. Generated fixtures
    conftest_content = read_file_safe(conftest_file)
    print_section("4. GENERATED FIXTURES (conftest.py)", conftest_content)
    print(f"\nTotal lines: {len(conftest_content.split(chr(10)))}")
    print(f"File location: {conftest_file}")
    
    # Summary comparison
    print("\n" + "="*80)
    print(" CONVERSION SUMMARY")
    print("="*80)
    print(f"{'Format':<20} {'Lines':<10} {'Readable':<12} {'IDE Support':<15}")
    print("-"*80)
    
    dsl_lines = len(dsl_content.split('\n')) if "[File" not in dsl_content else "N/A"
    vmcode_lines = len(vmcode_content.split('\n')) if "[File" not in vmcode_content else "N/A"
    pytest_lines = len(pytest_content.split('\n')) if "[File" not in pytest_content else "N/A"
    conftest_lines = len(conftest_content.split('\n')) if "[File" not in conftest_content else "N/A"
    
    print(f"{'Original DSL':<20} {str(dsl_lines):<10} {'High':<12} {'None':<15}")
    print(f"{'AutoLib vmcode':<20} {str(vmcode_lines):<10} {'Low':<12} {'None':<15}")
    print(f"{'pytest test':<20} {str(pytest_lines):<10} {'Very High':<12} {'Full':<15}")
    print(f"{'pytest fixtures':<20} {str(conftest_lines):<10} {'Very High':<12} {'Full':<15}")
    
    print("\n" + "="*80)
    print(" KEY ADVANTAGES OF PYTEST MIGRATION")
    print("="*80)
    print("✅ Native Python code (no custom DSL)")
    print("✅ Full IDE support (autocomplete, type hints, refactoring)")
    print("✅ Standard pytest features (fixtures, parametrize, markers)")
    print("✅ Python debugger support (pdb, IDE debuggers)")
    print("✅ Reusable fixtures from include files")
    print("✅ Clear error messages and stack traces")
    print("✅ Extensible with Python ecosystem (requests, pandas, etc.)")
    
    print("\n" + "="*80)
    print(" FILE LOCATIONS")
    print("="*80)
    print(f"DSL test:      {dsl_file}")
    print(f"vmcode:        {vmcode_file}")
    print(f"pytest test:   {pytest_file}")
    print(f"conftest:      {conftest_file}")
    print(f"Registry:      {pytest_file.parent / '.conversion_registry.json'}")
    
    print("\n" + "="*80)
    print(" NEXT STEPS")
    print("="*80)
    print("1. Review generated pytest test:")
    print(f"   cat {pytest_file}")
    print("")
    print("2. Review generated fixtures:")
    print(f"   cat {conftest_file}")
    print("")
    print("3. Run the pytest test:")
    print(f"   cd {pytest_file.parent} && pytest -v test_205812.py")
    print("")
    print("4. View conversion registry:")
    print(f"   cat {pytest_file.parent}/.conversion_registry.json | python3 -m json.tool")
    print("")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
