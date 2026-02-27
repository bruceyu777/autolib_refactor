#!/usr/bin/env python3
"""
DSL Group File Parser

Parses DSL group files (grp.*) to extract test execution sequences.
Group files define test IDs and their corresponding DSL script paths.

Format:
    ID                     Scripts                                          Comment
    205812                 testcase/trunk/ips/topology1/205812.txt         "test description"
    topology1-nat.txt      testcase/trunk/ips/topology1/topology1-nat.txt  "setup script"

Lines starting with '#' are comments and are skipped.
Conditional blocks <if>...</if> are currently skipped.
"""

import re
import os
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class GrpTestEntry:
    """Represents a single test entry from a grp file"""
    test_id: str           # Test identifier (e.g., "205812", "topology1-nat.txt")
    script_path: str       # Path to DSL script
    comment: str           # Test description
    line_number: int       # Line number in grp file (for debugging)
    pytest_name: str       # Generated pytest filename
    order: int             # Execution order (0-based)

    def __repr__(self):
        return f"GrpTestEntry({self.order}: {self.test_id} -> {self.pytest_name})"


class GrpFileParser:
    """Parser for DSL group files"""
    
    # Regex patterns
    COMMENT_LINE = re.compile(r'^\s*#')
    EMPTY_LINE = re.compile(r'^\s*$')
    CONDITIONAL_START = re.compile(r'^\s*<if\s+')
    CONDITIONAL_END = re.compile(r'^\s*<fi>')
    
    # Test entry pattern: ID  Scripts  ["Comment"]
    # Handles tabs and multiple spaces as separators
    TEST_ENTRY = re.compile(
        r'^(?P<test_id>\S+)\s+'                    # Test ID (no spaces)
        r'(?P<script_path>\S+)'                    # Script path (no spaces)
        r'(?:\s+(?P<comment>"[^"]*"))?'           # Optional comment in quotes
    )
    
    def __init__(self, grp_file_path: str):
        """
        Initialize parser with grp file path
        
        Args:
            grp_file_path: Path to grp file (absolute or relative)
        """
        self.grp_file_path = Path(grp_file_path)
        self.grp_dir = self.grp_file_path.parent
        self.entries: List[GrpTestEntry] = []
        
        if not self.grp_file_path.exists():
            raise FileNotFoundError(f"Group file not found: {grp_file_path}")
    
    def parse(self) -> List[GrpTestEntry]:
        """
        Parse the grp file and return list of test entries in order
        
        Returns:
            List of GrpTestEntry objects in execution order
        """
        self.entries = []
        order = 0
        in_conditional_block = False
        
        with open(self.grp_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                # Skip conditional blocks (not currently supported)
                if self.CONDITIONAL_START.match(line):
                    in_conditional_block = True
                    continue
                if self.CONDITIONAL_END.match(line):
                    in_conditional_block = False
                    continue
                if in_conditional_block:
                    continue
                
                # Skip comments and empty lines
                if self.COMMENT_LINE.match(line) or self.EMPTY_LINE.match(line):
                    continue
                
                # Try to parse as test entry
                match = self.TEST_ENTRY.match(line)
                if match:
                    test_id = match.group('test_id')
                    script_path = match.group('script_path')
                    comment = match.group('comment') or ''
                    comment = comment.strip('"')  # Remove quotes
                    
                    # Generate pytest filename from test ID
                    pytest_name = self._generate_pytest_name(test_id)
                    
                    entry = GrpTestEntry(
                        test_id=test_id,
                        script_path=script_path,
                        comment=comment,
                        line_number=line_num,
                        pytest_name=pytest_name,
                        order=order
                    )
                    
                    self.entries.append(entry)
                    order += 1
        
        return self.entries
    
    def _generate_pytest_name(self, test_id: str) -> str:
        """
        Generate pytest filename from test ID
        
        Examples:
            205812              -> test__205812.py
            topology1-nat.txt   -> test__topology1_nat.py
            updateSSH-nat.txt   -> test__updateSSH_nat.py
        
        Args:
            test_id: Test identifier from grp file
            
        Returns:
            Pytest filename (e.g., "test__205812.py")
        """
        # Remove .txt extension if present
        name = test_id
        if name.endswith('.txt'):
            name = name[:-4]
        
        # Replace hyphens and dots with underscores
        name = name.replace('-', '_').replace('.', '_')
        
        # Add test__ prefix and .py extension
        return f"test__{name}.py"
    
    def resolve_script_path(self, entry: GrpTestEntry) -> Path:
        """
        Resolve the full path to the DSL script
        
        The script_path in grp files can be:
        - Relative to grp file directory
        - Absolute path
        - Path using testcase/ prefix
        
        Args:
            entry: GrpTestEntry to resolve
            
        Returns:
            Path object to the DSL script
        """
        script_path = Path(entry.script_path)
        
        # If absolute path, use as-is
        if script_path.is_absolute():
            return script_path
        
        # Try relative to grp file directory first
        candidate = self.grp_dir / script_path
        if candidate.exists():
            return candidate
        
        # Try removing testcase/trunk/ips prefix and looking in grp_dir
        # Example: testcase/trunk/ips/topology1/205812.txt -> topology1/205812.txt
        parts = script_path.parts
        if parts[0] == 'testcase' and len(parts) > 3:
            # Skip to the part after testcase/trunk/ips
            relative_path = Path(*parts[3:])
            candidate = self.grp_dir / relative_path
            if candidate.exists():
                return candidate
        
        # Return original path (may not exist, caller should handle)
        return self.grp_dir / script_path
    
    def get_test_ids(self) -> List[str]:
        """Get list of test IDs in order"""
        return [entry.test_id for entry in self.entries]
    
    def get_pytest_names(self) -> List[str]:
        """Get list of pytest filenames in order"""
        return [entry.pytest_name for entry in self.entries]
    
    def get_dsl_scripts(self) -> List[Tuple[str, Path]]:
        """
        Get list of (test_id, dsl_script_path) tuples in order
        
        Returns:
            List of tuples: (test_id, resolved_script_path)
        """
        return [
            (entry.test_id, self.resolve_script_path(entry))
            for entry in self.entries
        ]
    
    def print_summary(self):
        """Print summary of parsed grp file"""
        print(f"\n{'='*80}")
        print(f"Group File: {self.grp_file_path.name}")
        print(f"Total Tests: {len(self.entries)}")
        print(f"{'='*80}\n")
        
        print(f"{'Order':<8} {'Test ID':<25} {'Pytest Name':<30}")
        print(f"{'-'*80}")
        
        for entry in self.entries:
            print(f"{entry.order:<8} {entry.test_id:<25} {entry.pytest_name:<30}")
        
        print(f"\n{'='*80}\n")
    
    def save_order_file(self, output_path: Optional[str] = None):
        """
        Save test execution order to a file for pytest ordering
        
        Args:
            output_path: Path to save order file (default: .pytest-order.txt in output dir)
        """
        if output_path is None:
            output_path = Path.cwd() / '.pytest-order.txt'
        else:
            output_path = Path(output_path)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Test execution order from: {self.grp_file_path.name}\n")
            f.write(f"# Generated automatically - do not edit manually\n\n")
            
            for entry in self.entries:
                # Format: order:pytest_name
                f.write(f"{entry.order}:{entry.pytest_name}\n")
        
        print(f"Saved test order to: {output_path}")
        return output_path


def main():
    """CLI interface for grp file parser"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Parse DSL group files and extract test sequences'
    )
    parser.add_argument(
        'grp_file',
        help='Path to grp file (e.g., grp.ips_nat.full)'
    )
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Print summary of tests in grp file'
    )
    parser.add_argument(
        '--save-order',
        action='store_true',
        help='Save test execution order to .pytest-order.txt'
    )
    parser.add_argument(
        '--output-dir',
        help='Output directory for order file (default: current directory)'
    )
    
    args = parser.parse_args()
    
    # Parse grp file
    grp_parser = GrpFileParser(args.grp_file)
    entries = grp_parser.parse()
    
    if args.summary:
        grp_parser.print_summary()
    
    if args.save_order:
        output_path = None
        if args.output_dir:
            output_path = Path(args.output_dir) / '.pytest-order.txt'
        grp_parser.save_order_file(output_path)
    
    # If no options, just print test names
    if not (args.summary or args.save_order):
        print("\nPytest test names (in execution order):")
        for entry in entries:
            print(f"  {entry.pytest_name}")
        print(f"\nTotal: {len(entries)} tests\n")


if __name__ == '__main__':
    main()
