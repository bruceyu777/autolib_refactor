#!/usr/bin/env python3
"""
DSL to pytest Transpiler Runner

Converts AutoLib DSL test scripts to pytest format.
Supports single file, batch folder, or group file (grp.*) conversion.

Usage:
    # Single file conversion
    python run_transpiler.py -f testcase/ips/205812.txt
    
    # Batch folder conversion
    python run_transpiler.py -d testcase/ips/topology1/
    
    # Group file conversion (maintains test order)
    python run_transpiler.py -g testcase/ips/grp.ips_nat.full
    
    # Custom output directory
    python run_transpiler.py -f test.txt -o custom_output/
    
    # Example: Default test
    python run_transpiler.py  # Uses default test 205812.txt

Note: Some tests may require mocker updates (mock_device.py) to handle
      specific command patterns or output formats.
"""

import sys
import argparse
from pathlib import Path
from typing import List, Dict

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent / 'tools'))

from conversion_registry import ConversionRegistry
from dsl_transpiler import DSLTranspiler
from grp_parser import GrpFileParser


def convert_file(test_file: Path, output_dir: Path, registry: ConversionRegistry, 
                 transpiler: DSLTranspiler, env_file: Path = None) -> Dict:
    """Convert a single DSL test file to pytest"""
    print(f"\n📄 Converting: {test_file.name}")
    print(f"   Source: {test_file}")
    if env_file:
        print(f"   Env:    {env_file}")
    
    if not test_file.exists():
        print(f"   ❌ Error: File not found")
        return None
    
    try:
        result = transpiler.transpile(test_file, output_dir, env_file=env_file)
        print(f"   ✅ Generated: test_{result['qaid']}.py")
        return result
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def convert_folder(folder: Path, output_dir: Path, registry: ConversionRegistry,
                   transpiler: DSLTranspiler, env_file: Path = None) -> List[Dict]:
    """Convert all DSL test files in a folder"""
    # Find all .txt files in folder
    test_files = sorted(folder.glob('*.txt'))
    
    if not test_files:
        print(f"⚠️  No .txt files found in {folder}")
        return []
    
    print(f"\n📁 Found {len(test_files)} test file(s) in {folder}")
    
    results = []
    success_count = 0
    fail_count = 0
    
    for test_file in test_files:
        result = convert_file(test_file, output_dir, registry, transpiler, env_file)
        if result:
            results.append(result)
            success_count += 1
        else:
            fail_count += 1
    
    print(f"\n📊 Batch Conversion Summary:")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Failed:  {fail_count}")
    print(f"   📝 Total:   {len(test_files)}")
    
    return results


def show_generated_files(output_dir: Path):
    """Display generated files with sizes"""
    print("\n📁 Generated Files:")
    print("-"*70)
    
    # Python test files
    py_files = sorted(output_dir.glob('*.py'))
    for file in py_files:
        size = file.stat().st_size
        print(f"  {file.name:<40} ({size:>6} bytes)")
    
    # Registry file
    registry_file = output_dir / '.conversion_registry.json'
    if registry_file.exists():
        size = registry_file.stat().st_size
        print(f"  {registry_file.name:<40} ({size:>6} bytes)")
    
    print("-"*70)


def convert_grp_file(grp_file: Path, output_dir: Path, registry: ConversionRegistry,
                     transpiler: DSLTranspiler, env_file: Path = None) -> List[Dict]:
    """
    Convert all DSL test files defined in a group file
    Maintains test execution order as defined in grp file
    """
    print(f"\n📋 Processing Group File: {grp_file.name}")
    print(f"   Source: {grp_file}")
    if env_file:
        print(f"   Env:    {env_file}")
    
    # Parse grp file
    try:
        grp_parser = GrpFileParser(str(grp_file))
        entries = grp_parser.parse()
    except Exception as e:
        print(f"   ❌ Error parsing grp file: {e}")
        return []
    
    print(f"   📊 Found {len(entries)} test(s) in group file")
    
    # Show grp file summary
    grp_parser.print_summary()
    
    # Convert each DSL script in order
    results = []
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    for entry in entries:
        # Resolve DSL script path
        dsl_script = grp_parser.resolve_script_path(entry)
        
        if not dsl_script.exists():
            print(f"\n📄 [{entry.order}] {entry.test_id}")
            print(f"   ⚠️  Skipped: DSL script not found: {dsl_script}")
            skip_count += 1
            continue
        
        # Convert the DSL script
        print(f"\n📄 [{entry.order}] Converting: {entry.test_id}")
        print(f"   Source: {dsl_script}")
        
        try:
            result = transpiler.transpile(dsl_script, output_dir, env_file=env_file)
            print(f"   ✅ Generated: {entry.pytest_name}")
            
            # Add order metadata to result
            result['grp_order'] = entry.order
            result['grp_test_id'] = entry.test_id
            
            results.append(result)
            success_count += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")
            fail_count += 1
    
    # Save test execution order
    order_file = output_dir / '.pytest-order.txt'
    grp_parser.save_order_file(str(order_file))
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"📊 Group File Conversion Summary:")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Failed:  {fail_count}")
    print(f"   ⚠️  Skipped: {skip_count}")
    print(f"   📝 Total:   {len(entries)}")
    print(f"{'='*70}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Convert AutoLib DSL test scripts to pytest format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert single file
  %(prog)s -f /path/to/testcase/205812.txt
  
  # Convert all tests in folder
  %(prog)s -d /path/to/testcase/ips/topology1/
  
  # Convert tests from group file (maintains execution order)
  %(prog)s -g /path/to/testcase/ips/grp.ips_nat.full
  
  # Custom output directory
  %(prog)s -f test.txt -o /tmp/pytest_output/
  
  # Specify environment configuration file
  %(prog)s -f test.txt -e env.fortistack.ips.conf
  
  # Use default test (205812.txt)
  %(prog)s

Note:
  Environment file is auto-detected if not specified.
  Group files (-g) define test execution sequences.
  Some tests may require updates to mock_device.py to simulate
  specific FortiGate/device behaviors and command outputs.
        """
    )
    
    parser.add_argument('-f', '--file', 
                        type=Path,
                        help='Single DSL test file to convert (.txt)')
    
    parser.add_argument('-d', '--dir', 
                        type=Path,
                        help='Directory containing DSL test files for batch conversion')
    
    parser.add_argument('-g', '--grp-file',
                        type=Path,
                        dest='grp_file',
                        help='Group file (grp.*) defining test execution sequence')
    
    parser.add_argument('-o', '--output',
                        type=Path,
                        default=Path(__file__).parent / 'output',
                        help='Output directory for generated pytest files (default: ./output)')
    
    parser.add_argument('-e', '--env',
                        type=Path,
                        help='Environment configuration file (e.g., env.fortistack.ips.conf). '
                             'If not specified, will auto-detect in testcase directory.')
    
    args = parser.parse_args()
    
    # Determine input source
    input_count = sum([bool(args.file), bool(args.dir), bool(args.grp_file)])
    if input_count > 1:
        print("❌ Error: Can only specify one of --file, --dir, or --grp-file")
        sys.exit(1)
    
    # Default to test 205812.txt if no input specified
    if input_count == 0:
        default_test = Path('/home/fosqa/autolibv3/autolib_v3/testcase/ips/topology1/205812.txt')
        if default_test.exists():
            args.file = default_test
            print(f"ℹ️  Using default test: {default_test.name}")
        else:
            print("❌ Error: No input specified and default test not found")
            print("   Use --file, --dir, or --grp-file to specify input")
            sys.exit(1)
    
    output_dir = args.output
    
    # Auto-detect or validate environment file
    env_file = args.env
    if not env_file:
        # Try to auto-detect env file in testcase directory
        # Look for env*.conf files near the test files
        if args.file:
            search_dir = args.file.parent
        elif args.dir:
            search_dir = args.dir
        elif args.grp_file:
            search_dir = args.grp_file.parent
        else:
            search_dir = Path('/home/fosqa/autolibv3/autolib_v3/testcase/ips')
        
        # Search for env*.conf files
        env_files = list(search_dir.glob('env*.conf'))
        if env_files:
            env_file = env_files[0]
            print(f"ℹ️  Auto-detected environment file: {env_file.name}")
        else:
            # Try parent directory
            env_files = list(search_dir.parent.glob('env*.conf'))
            if env_files:
                env_file = env_files[0]
                print(f"ℹ️  Auto-detected environment file: {env_file.name}")
    
    if env_file and not env_file.exists():
        print(f"⚠️  Warning: Environment file not found: {env_file}")
        print(f"           Will use minimal default configuration")
        env_file = None
    
    # Print header
    print("\n" + "="*70)
    print("🚀 DSL to pytest Transpiler")
    print("="*70)
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")
    
    # Initialize registry and transpiler
    registry = ConversionRegistry(str(output_dir / '.conversion_registry.json'))
    transpiler = DSLTranspiler(registry)
    
    # Convert based on input type
    if args.file:
        # Single file conversion
        result = convert_file(args.file, output_dir, registry, transpiler, env_file)
        if not result:
            sys.exit(1)
        next_step = f"cd {output_dir} && pytest -v test_{result['qaid']}.py"
    elif args.grp_file:
        # Group file conversion (with test ordering)
        results = convert_grp_file(args.grp_file, output_dir, registry, transpiler, env_file)
        if not results:
            sys.exit(1)
        next_step = f"cd {output_dir} && make test-grp GRP={args.grp_file.name}"
    else:
        # Batch folder conversion
        results = convert_folder(args.dir, output_dir, registry, transpiler, env_file)
        if not results:
            sys.exit(1)
        next_step = f"cd {output_dir} && pytest -v"
    
    # Show registry stats
    print("\n" + "="*70)
    registry.print_stats()
    
    # Show generated files
    show_generated_files(output_dir)
    
    print("\n✅ Transpilation complete!")
    print(f"\n💡 Next step: {next_step}")
    print(f"\n⚠️  Note: If tests fail, you may need to update mock_device.py")
    print(f"          to handle specific command patterns for your tests.\n")


if __name__ == '__main__':
    main()
