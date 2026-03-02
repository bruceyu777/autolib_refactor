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
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Set up unified logging to prototype/logs/
_PROTOTYPE_DIR = Path(__file__).resolve().parent.parent
if str(_PROTOTYPE_DIR) not in sys.path:
    sys.path.insert(0, str(_PROTOTYPE_DIR))
try:
    from common.common_logging import setup_script_logging
    logger = setup_script_logging(__file__, log_dir=_PROTOTYPE_DIR / 'logs')
except ImportError:
    logger = logging.getLogger(__name__)

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
    
    def __init__(self, registry: ConversionRegistry, env_file: Optional[Path] = None):
        """
        Initialize transpiler with component dependencies
        
        Args:
            registry: Conversion registry for tracking include usage
            env_file: Optional environment configuration file to load VERSION
        """
        self.registry = registry
        self.env_file = env_file
        
        # Load VERSION from env config
        env_version = IncludeConverter.load_version_from_env_config(env_file)
        self.converter = IncludeConverter(registry, env_version=env_version)
        
        self.parser = DSLParser()
        self.test_gen = TestGenerator()
        self.conftest_gen = ConftestGenerator()
        logger.info("[DSLTranspiler] Initialized | env_file=%s | env_version=%s", env_file, env_version)
    
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
        logger.info("[transpile] START: '%s'", test_file)
        logger.debug("[transpile] output_dir='%s' env_file='%s'", output_dir, env_file)
        # Update converter if env_file is provided (may override default)
        if env_file:
            env_version = IncludeConverter.load_version_from_env_config(env_file)
            self.converter.env_version = env_version
            logger.debug("[transpile] Overriding env_version=%s from env_file=%s", env_version, env_file)
        
        # Step 1: Parse DSL test
        logger.info("[transpile][1/5] Parsing DSL test: '%s'", test_file.name)
        parsed = self.parser.parse_test_file(test_file)
        logger.info("[transpile][1/5] qaid=%s | title='%s' | sections=%d | includes=%d",
                    parsed['qaid'], parsed['title'], len(parsed['sections']), len(parsed['includes']))
        
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
        
        logger.info("[transpile] COMPLETE: '%s' | test='%s' | helpers=%d sections=%d",
                    test_file.name, test_output, result['helpers'], result['sections'])
        
        return result
    
    def _initialize_conftest(self, output_dir: Path, env_file: Optional[Path] = None) -> None:
        """
        Initialize or verify conftest.py existence
        
        Args:
            output_dir: Output directory where conftest.py should be
            env_file: Optional environment configuration file
        """
        logger.info("[transpile][2/5] Initializing conftest.py...")
        output_dir.mkdir(parents=True, exist_ok=True)
        conftest_file = output_dir / 'conftest.py'
        conftest_needs_header = (not conftest_file.exists()) or conftest_file.stat().st_size == 0

        if conftest_needs_header:
            conftest_content = self.conftest_gen.generate_header(env_file)
            conftest_file.write_text(conftest_content)
            logger.info("[transpile][2/5] Created conftest.py: '%s' (env_file=%s)", conftest_file, env_file)
        else:
            logger.debug("[transpile][2/5] Using existing conftest.py: '%s'", conftest_file)

        # Scaffold pytest.ini if missing
        pytest_ini = output_dir / 'pytest.ini'
        if not pytest_ini.exists():
            pytest_ini.write_text(self.conftest_gen.generate_pytest_ini())
            logger.info("[transpile][2/5] Created pytest.ini: '%s'", pytest_ini)

        # Scaffold Makefile if missing
        makefile = output_dir / 'Makefile'
        if not makefile.exists():
            makefile.write_text(self.conftest_gen.generate_makefile())
            logger.info("[transpile][2/5] Created Makefile: '%s'", makefile)
    
    def _convert_dependencies(self, includes: List[dict], output_dir: Path) -> List[str]:
        """
        Convert include dependencies to helper functions
        
        Args:
            includes: List of include dictionaries from parser
            output_dir: Output directory for helpers
            
        Returns:
            List of helper function names
        """
        logger.info("[convert_deps][3/5] Converting %d includes...", len(includes))
        
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
                logger.info("[convert_deps] Converting: '%s'", include_path)
                try:
                    self.converter.convert_include(
                        include_path,
                        resolved_path,
                        output_dir,
                        force=False
                    )
                except Exception:
                    logger.exception("[convert_deps] Failed to convert include: '%s'", include_path)
            else:
                logger.warning("[convert_deps] Resolved path does not exist: '%s' (from '%s')",
                               resolved_path, include_path)
        
        # Collect unique helper names
        helper_names = []
        for include in includes:
            include_path = include['path']
            filename = Path(include_path).stem
            helper_name = f"helper_{self.test_gen.sanitize_identifier(filename)}"
            if helper_name not in helper_names:
                helper_names.append(helper_name)
        
        logger.info("[convert_deps][3/5] Done. %d includes → %d helpers",
                    len(includes), len(helper_names))
        return helper_names
    
    def _update_registry(self, parsed: dict, helper_names: List[str]) -> None:
        """
        Update conversion registry with usage information
        
        Args:
            parsed: Parsed DSL structure
            helper_names: List of helper names used
        """
        logger.info("[update_registry][4/5] Updating registry for qaid=%s (%d includes)",
                    parsed['qaid'], len(parsed['includes']))
        for include in parsed['includes']:
            sanitized_used_by = self.test_gen.sanitize_identifier(f"test_{parsed['qaid']}")
            # Normalize path using same logic as converter (GLOBAL:VERSION → VERSION only)
            include_path = include['path']
            normalized_path = include_path.replace('GLOBAL:VERSION', self.converter.env_version)
            normalized_path = normalized_path.replace('GLOBAL/', f'{self.converter.env_version}/')
            self.registry.mark_usage(normalized_path, sanitized_used_by)
    
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
        Resolve include path to physical file.

        Logs every candidate path tried and their existence, to aid
        diagnosis of environment-specific missing helpers.
        """
        # Replace variables
        resolved = include_path.replace('GLOBAL:VERSION', 'current')
        resolved = resolved.replace('GLOBAL:Version', 'current')
        resolved = resolved.replace('testcase/', '')

        filename = Path(resolved).name

        tools_dir = Path(__file__).parent
        prototype_dir = tools_dir.parent

        candidates: list[tuple[str, Path]] = [
            ('sample_includes', prototype_dir / 'sample_includes' / filename),
        ]

        testcase_dir = prototype_dir.parent / 'testcase'
        parts = Path(resolved).parts
        if len(parts) >= 2 and parts[0] == 'current':
            candidates.append(('testcase/current-stripped', testcase_dir / '/'.join(parts[1:])))
        candidates.append(('testcase/direct', testcase_dir / resolved))

        logger.debug("[resolve_include] include_path='%s'", include_path)
        logger.debug("[resolve_include] resolved='%s' | testcase_dir='%s'", resolved, testcase_dir)

        for label, candidate in candidates:
            exists = candidate.exists()
            logger.debug("[resolve_include] %s: '%s'  exists=%s", label, candidate, exists)
            if exists:
                logger.info("[resolve_include] FOUND via %s: '%s'", label, candidate)
                return candidate

        logger.warning(
            "[resolve_include] NOT FOUND: '%s' (resolved='%s'). Tried %d candidates. cwd='%s'",
            include_path, resolved, len(candidates), Path.cwd()
        )
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
