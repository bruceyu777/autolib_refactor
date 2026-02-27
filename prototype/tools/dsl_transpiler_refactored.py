"""
DSL to pytest Transpiler (Refactored)
Main orchestrator for converting AutoLib v3 DSL tests to pytest format

This module coordinates the transpilation process using specialized components:
- DSLParser: Parses DSL test files
- TestGenerator: Generates pytest test code
- ConftestGenerator: Generates conftest.py with fixtures and hooks
- IncludeConverter: Converts include files to helper functions
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional

# Import refactored modules
from conversion_registry import ConversionRegistry
from include_converter import IncludeConverter
from dsl_parser import DSLParser
from test_generator import TestGenerator
from conftest_generator import ConftestGenerator


class DSLTranspiler:
    """
    Main transpiler orchestrator
    
    Coordinates DSL parsing, dependency conversion, and pytest generation
    using specialized components for each concern.
    """
    
    def __init__(self, registry: ConversionRegistry):
        """
        Initialize transpiler with component dependencies
        
        Args:
            registry: Conversion registry for tracking include usage
        """
        self.registry = registry
        self.converter = IncludeConverter(registry)
        self.parser = DSLParser()
        self.test_gen = TestGenerator()
        self.conftest_gen = ConftestGenerator()
        self.logger = logging.getLogger(__name__)
    
    def transpile(self, test_file: Path, output_dir: Path, env_file: Optional[Path] = None) -> dict:
        """
        Main transpilation workflow
        
        Orchestrates the complete process:
        1. Parse DSL test file
        2. Initialize/update conftest.py
        3. Convert include dependencies to helpers
        4. Generate pytest test file
        5. Update conversion registry
        
        Args:
            test_file: DSL test file to convert
            output_dir: Output directory for generated files
            env_file: Optional environment configuration file
        
        Returns:
            dict with conversion results and statistics
        """
        print("\n" + "="*60)
        print(f"TRANSPILING: {test_file.name}")
        print("="*60)
        
        # Step 1: Parse DSL test
        print("\n[1/5] Parsing DSL test...")
        parsed = self.parser.parse_test_file(test_file)
        print(f"  ✓ QAID: {parsed['qaid']}")
        print(f"  ✓ Title: {parsed['title']}")
        print(f"  ✓ Sections: {len(parsed['sections'])}")
        print(f"  ✓ Includes: {len(parsed['includes'])}")
        
        # Step 2: Initialize conftest.py
        self._initialize_conftest(output_dir, env_file)
        
        # Step 3: Convert dependencies (includes → helpers)
        helper_names = self._convert_dependencies(parsed['includes'], output_dir)
        
        # Step 4: Update registry
        self._update_registry(parsed, helper_names)
        
        # Step 5: Generate test file
        test_output = self._generate_test_file(parsed, test_file, output_dir, helper_names)
        
        # Return results
        result = {
            'qaid': parsed['qaid'],
            'test_file': str(test_output),
            'helpers': len(parsed['includes']),
            'sections': len(parsed['sections']),
            'includes': len(parsed['includes'])
        }
        
        self._print_summary(test_output, result)
        
        return result
    
    def _initialize_conftest(self, output_dir: Path, env_file: Optional[Path] = None) -> None:
        """
        Initialize or verify conftest.py existence
        
        Args:
            output_dir: Output directory where conftest.py should be
            env_file: Optional environment configuration file
        """
        print("\n[2/5] Initializing conftest.py...")
        output_dir.mkdir(parents=True, exist_ok=True)
        conftest_file = output_dir / 'conftest.py'
        conftest_needs_header = (not conftest_file.exists()) or conftest_file.stat().st_size == 0

        if conftest_needs_header:
            conftest_content = self.conftest_gen.generate_header(env_file)
            conftest_file.write_text(conftest_content)
            print(f"  ✓ Created: {conftest_file}")
            if env_file:
                print(f"    Using env config: {env_file}")
        else:
            print(f"  ✓ Using existing: {conftest_file}")
    
    def _convert_dependencies(self, includes: List[dict], output_dir: Path) -> List[str]:
        """
        Convert include dependencies to helper functions
        
        Args:
            includes: List of include dictionaries from parser
            output_dir: Output directory for helpers
            
        Returns:
            List of helper function names
        """
        print("\n[3/5] Converting include dependencies...")
        
        # Resolve include paths
        for include in includes:
            include_path = include['path']
            resolved_path = self._resolve_include_path(include_path)
            include['resolved_path'] = resolved_path
        
        # Convert includes to helpers
        for include in includes:
            include_path = include['path']
            resolved_path = include['resolved_path']
            
            if resolved_path.exists():
                print(f"\n→ Converting dependency: {include_path}")
                try:
                    self.converter.convert_include(
                        include_path,
                        resolved_path,
                        output_dir,
                        force=False
                    )
                except Exception:
                    self.logger.exception("Failed to convert include: %s", include_path)
                    print(f"  ⚠️  Failed to convert include, continuing: {include_path}")
        
        # Collect unique helper names
        helper_names = []
        for include in includes:
            include_path = include['path']
            filename = Path(include_path).stem
            helper_name = f"helper_{self.test_gen.sanitize_identifier(filename)}"
            if helper_name not in helper_names:
                helper_names.append(helper_name)
        
        print(f"  ✓ Helpers generated: {len(includes)} includes converted")
        return helper_names
    
    def _update_registry(self, parsed: dict, helper_names: List[str]) -> None:
        """
        Update conversion registry with usage information
        
        Args:
            parsed: Parsed DSL structure
            helper_names: List of helper names used
        """
        print("\n[4/5] Updating registry...")
        for include in parsed['includes']:
            sanitized_used_by = self.test_gen.sanitize_identifier(f"test_{parsed['qaid']}")
            self.registry.mark_usage(include['path'], sanitized_used_by)
    
    def _generate_test_file(self, parsed: dict, original_file: Path, 
                           output_dir: Path, helper_names: List[str]) -> Path:
        """
        Generate pytest test file from parsed DSL
        
        Args:
            parsed: Parsed DSL structure
            original_file: Original DSL file path
            output_dir: Output directory
            helper_names: List of helper names to import
            
        Returns:
            Path to generated test file
        """
        print("\n[5/5] Generating test file...")
        
        # Generate test code
        test_code = self.test_gen.generate_test_header(
            parsed['qaid'], original_file, helper_names
        )
        test_code += self.test_gen.generate_test_function(parsed, helper_names)
        
        # Sanitize QAID for filename
        sanitized_qaid = self.test_gen.sanitize_identifier(parsed['qaid'])
        
        # Output test to testcases/ subdirectory
        testcases_dir = output_dir / 'testcases'
        testcases_dir.mkdir(exist_ok=True)
        test_output = testcases_dir / f"test_{sanitized_qaid}.py"
        test_output.write_text(test_code)
        
        print(f"  ✓ Created: {test_output}")
        return test_output
    
    def _resolve_include_path(self, include_path: str) -> Path:
        """
        Resolve include path to physical file
        
        Handles variable expansion and path resolution:
        - GLOBAL:VERSION → current version/branch
        - Searches in sample_includes and testcase directories
        
        Args:
            include_path: Include path from DSL
            
        Returns:
            Resolved Path object
        """
        # Replace variables
        resolved = include_path.replace('GLOBAL:VERSION', 'current')
        resolved = resolved.replace('GLOBAL:Version', 'current')
        resolved = resolved.replace('testcase/', '')
        
        filename = Path(resolved).name
        
        # Try sample includes first (for prototyping)
        tools_dir = Path(__file__).parent
        prototype_dir = tools_dir.parent
        sample_path = prototype_dir / 'sample_includes' / filename
        
        if sample_path.exists():
            return sample_path
        
        # Try actual testcase directory
        testcase_dir = prototype_dir.parent / 'testcase'
        parts = Path(resolved).parts
        
        if len(parts) >= 2 and parts[0] == 'current':
            # Reconstruct path: testcase/ips/topology1/filename
            actual_path = testcase_dir / '/'.join(parts[1:])
            if actual_path.exists():
                return actual_path
        
        # Last resort: try direct path from testcase root
        direct_path = testcase_dir / resolved
        if direct_path.exists():
            return direct_path
        
        # If nothing found, return original
        return Path(resolved)
    
    def _print_summary(self, test_output: Path, result: dict) -> None:
        """
        Print transpilation summary
        
        Args:
            test_output: Path to generated test file
            result: Result dictionary with statistics
        """
        print("\n" + "="*60)
        print("TRANSPILATION COMPLETE")
        print("="*60)
        print(f"Test file: {test_output}")
        print(f"Helpers: {result['helpers']} includes converted to callable helpers")
        print("="*60 + "\n")


def main():
    """CLI entry point for standalone usage"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Transpile DSL test to pytest',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s test_205812 --output-dir output
  %(prog)s test_205812 --output-dir output --env env.conf
        """
    )
    parser.add_argument('test_file', help='DSL test file to convert')
    parser.add_argument('--output-dir', '-o', default='prototype/output', 
                       help='Output directory (default: prototype/output)')
    parser.add_argument('--env', '-e', help='Environment configuration file')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    test_file = Path(args.test_file)
    output_dir = Path(args.output_dir)
    env_file = Path(args.env) if args.env else None
    
    # Validate inputs
    if not test_file.exists():
        print(f"Error: Test file not found: {test_file}")
        sys.exit(1)
    
    if env_file and not env_file.exists():
        print(f"Error: Environment file not found: {env_file}")
        sys.exit(1)
    
    # Initialize components
    registry = ConversionRegistry()
    transpiler = DSLTranspiler(registry)
    
    # Transpile
    try:
        result = transpiler.transpile(test_file, output_dir, env_file)
        
        # Show registry stats
        print("\nConversion Registry Statistics:")
        registry.print_stats()
        
        sys.exit(0)
        
    except Exception as e:
        print(f"\nError during transpilation: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
