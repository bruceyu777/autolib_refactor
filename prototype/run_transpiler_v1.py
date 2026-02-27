#!/usr/bin/env python3
"""
Quick runner script to transpile test 205812.txt
"""

import sys
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent / 'tools'))

from conversion_registry import ConversionRegistry
from dsl_transpiler import DSLTranspiler


def main():
    # Paths
    test_file = Path('/home/fosqa/autolibv3/autolib_v3/testcase/ips/topology1/205812.txt')
    output_dir = Path(__file__).parent / 'output'
    
    print("\n🚀 DSL to pytest Transpiler - Prototype Demo")
    print("="*70)
    
    # Check test file exists
    if not test_file.exists():
        print(f"❌ Error: Test file not found: {test_file}")
        sys.exit(1)
    
    print(f"Input file: {test_file}")
    print(f"Output dir: {output_dir}")
    print("="*70)
    
    # Initialize registry and transpiler
    registry = ConversionRegistry(str(output_dir / '.conversion_registry.json'))
    transpiler = DSLTranspiler(registry)
    
    # Transpile
    result = transpiler.transpile(test_file, output_dir)
    
    # Show registry stats
    print("\n")
    registry.print_stats()
    
    # Show generated files
    print("\n📁 Generated Files:")
    print("-"*70)
    for file in sorted(output_dir.rglob('*.py')):
        size = file.stat().st_size
        rel_path = str(file.relative_to(output_dir))
        print(f"  {rel_path:<40} ({size:>6} bytes)")
    
    registry_file = output_dir / '.conversion_registry.json'
    if registry_file.exists():
        size = registry_file.stat().st_size
        rel_path = str(registry_file.relative_to(output_dir))
        print(f"  {rel_path:<40} ({size:>6} bytes)")
    
    print("-"*70)
    print("\n✅ Transpilation complete!")
    print(f"\n💡 Next step: cd {output_dir} && pytest -v test_{result['qaid']}.py\n")


if __name__ == '__main__':
    main()
