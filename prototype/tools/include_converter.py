"""
Include Converter: DSL include files → pytest helper functions
Converts reusable DSL scripts to callable helper functions
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from conversion_registry import ConversionRegistry


class IncludeConverter:
    """Convert include files to pytest helper functions"""
    
    def __init__(self, registry: ConversionRegistry) -> None:
        self.registry = registry
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def _sanitize_identifier(name: str) -> str:
        """Sanitize a string into a valid Python identifier.

        Args:
            name: Raw identifier name.

        Returns:
            Sanitized identifier with invalid characters replaced by underscores.
        """
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        if sanitized and sanitized[0].isdigit():
            sanitized = f"_{sanitized}"
        return sanitized
    
    def generate_helper_name(self, include_path: str, include_file: Path) -> str:
        """Generate helper function name from include path"""
        filename = self._sanitize_identifier(include_file.stem)  # govdom1, outvdom, etc.
        
        # Convert to valid Python function name
        # govdom1 → helper_govdom1
        # outvdom → helper_outvdom
        return f'helper_{filename}'
    
    def convert_to_helper(self, include_file: Path, helper_name: str) -> str:
        """Convert include file to helper function."""
        content = include_file.read_text().strip()

        param_vars, dynamic_vars = self._split_variables(content)
        param_list = "fgt"
        if param_vars:
            param_list = "fgt, " + ", ".join(param_vars)

        helper_code = f'''
def {helper_name}({param_list}):
    """
    Auto-generated from: {include_file}

    Original DSL:
{self._indent_content(content, 8)}

    Parameters:
        fgt: FluentFortiGate device instance
'''
        if param_vars:
            for var in param_vars:
                helper_code += f"        {var}: Value for ${var.upper()}\n"

        helper_code += '    """\n'

        blocks = self._parse_blocks(content.split('\n'))
        helper_code += self._render_blocks(
            blocks,
            indent="    ",
            param_vars=set(param_vars),
            dynamic_vars=dynamic_vars,
        )

        return helper_code
    
    def _indent_content(self, content: str, spaces: int) -> str:
        """Indent content for docstring"""
        indent = ' ' * spaces
        return '\n'.join(indent + line for line in content.split('\n'))
    
    def extract_variables(self, content: str) -> List[str]:
        """Extract variable names from DSL content."""
        variables = set()

        for match in re.finditer(r'\$(\w+)', content):
            variables.add(match.group(1))

        for match in re.finditer(r'\{\$(\w+)\}', content):
            variables.add(match.group(1))

        return sorted(variables)

    def _split_variables(self, content: str) -> Tuple[List[str], set[str]]:
        """Split variables into helper params and dynamic env vars.

        Args:
            content: DSL include content.

        Returns:
            Tuple of (param_vars, dynamic_vars).
        """
        variables = self.extract_variables(content)
        dynamic_vars = set()
        param_vars = []

        # Variables created via setvar should be treated as dynamic vars.
        for match in re.finditer(r'setvar\s+-e\s+".*?"\s+-to\s+(\w+)', content, re.IGNORECASE):
            dynamic_vars.add(match.group(1))

        for var in variables:
            if var.isupper() or var in dynamic_vars:
                dynamic_vars.add(var)
            else:
                param_vars.append(var.lower())

        return param_vars, dynamic_vars

    def _parse_blocks(self, lines: List[str]) -> List[dict]:
        """Parse DSL lines into command and control-flow blocks."""
        blocks, _, _ = self._parse_block_until(lines, 0, stop_tokens=None)
        return blocks

    def _parse_block_until(
        self,
        lines: List[str],
        start_index: int,
        stop_tokens: Optional[List[str]] = None,
    ) -> Tuple[List[dict], int, Optional[str]]:
        """Parse lines until a stop token is found.

        Args:
            lines: DSL lines.
            start_index: Start index.
            stop_tokens: List of tokens to stop on.

        Returns:
            Tuple of (blocks, next_index, stop_token).
        """
        blocks: List[dict] = []
        i = start_index

        while i < len(lines):
            raw_line = lines[i]
            line = raw_line.strip()

            if not line or line.startswith('#'):
                i += 1
                continue

            token = self._match_control_token(line)
            if stop_tokens and token in stop_tokens:
                return blocks, i, token

            if token == '<if>':
                condition_str = line[3:-1].strip()
                condition = self._parse_condition(condition_str)
                if_body, i, stop_token = self._parse_block_until(
                    lines,
                    i + 1,
                    stop_tokens=['<elseif>', '<else>', '<fi>'],
                )
                branches = [{'condition': condition, 'body': if_body}]
                else_body: List[dict] = []

                while stop_token == '<elseif>':
                    condition_str = lines[i].strip()[7:-1].strip()
                    condition = self._parse_condition(condition_str)
                    elif_body, i, stop_token = self._parse_block_until(
                        lines,
                        i + 1,
                        stop_tokens=['<elseif>', '<else>', '<fi>'],
                    )
                    branches.append({'condition': condition, 'body': elif_body})

                if stop_token == '<else>':
                    else_body, i, stop_token = self._parse_block_until(
                        lines,
                        i + 1,
                        stop_tokens=['<fi>'],
                    )

                blocks.append({'type': 'if_chain', 'branches': branches, 'else_body': else_body})
                i += 1
                continue

            blocks.append({'type': 'command', 'command': line})
            i += 1

        return blocks, i, None

    def _match_control_token(self, line: str) -> Optional[str]:
        """Return the control token type for a line if present."""
        if re.match(r'^<if\s+.+>$', line, re.IGNORECASE):
            return '<if>'
        if re.match(r'^<elseif\s+.+>$', line, re.IGNORECASE):
            return '<elseif>'
        if re.match(r'^<else>$', line, re.IGNORECASE):
            return '<else>'
        if re.match(r'^<fi>$', line, re.IGNORECASE):
            return '<fi>'
        return None

    def _parse_condition(self, condition_str: str) -> dict:
        """Parse a DSL condition string into a structured dict."""
        # Pattern: $VAR operator VALUE
        match = re.match(r'\$(\w+)\s*(<|>|eq|ne|<=|>=)\s+(.+)', condition_str.strip())
        if match:
            return {
                'left_type': 'dynamic',
                'left_var': match.group(1),
                'operator': match.group(2),
                'right': match.group(3).strip(),
            }

        # Pattern: DEVICE:VAR operator VALUE
        match = re.match(r'(\w+):(\w+)\s*(<|>|eq|ne|<=|>=)\s+(.+)', condition_str.strip())
        if match:
            return {
                'left_type': 'device_env',
                'left_var': f"{match.group(1)}:{match.group(2)}",
                'operator': match.group(3),
                'right': match.group(4).strip(),
            }

        return {'left_type': None, 'left_var': None, 'operator': None, 'right': None}

    def _translate_condition(
        self,
        condition: dict,
        param_vars: set[str],
        dynamic_vars: set[str],
    ) -> str:
        """Translate parsed condition into a Python expression."""
        operator = condition.get('operator')
        if not operator:
            return 'True'

        op_map = {'<': '<', '>': '>', '<=': '<=', '>=': '>=', 'eq': '==', 'ne': '!='}
        python_op = op_map.get(operator, operator)

        left_type = condition.get('left_type')
        left_var = condition.get('left_var')

        if left_type == 'device_env' and left_var:
            left = f"fgt.testbed.read_env_variables('{left_var}')"
        elif left_var:
            if left_var.lower() in param_vars:
                left = left_var.lower()
            else:
                left = f"fgt.testbed.env.get_dynamic_var('{left_var}')"
        else:
            return 'True'

        right_raw = condition.get('right', '')
        right = self._normalize_condition_value(right_raw, param_vars, dynamic_vars)

        if operator in ['<', '>', '<=', '>=']:
            left = f"int({left})"
            if right.startswith("fgt.testbed.env") or right in param_vars:
                right = f"int({right})"

        return f"{left} {python_op} {right}"

    def _normalize_condition_value(
        self,
        value: str,
        param_vars: set[str],
        dynamic_vars: set[str],
    ) -> str:
        """Normalize a condition value to a Python expression or literal."""
        value = value.strip().strip('"').strip("'")

        var_match = re.match(r'^\$(\w+)$', value)
        if var_match:
            var_name = var_match.group(1)
            if var_name.lower() in param_vars:
                return var_name.lower()
            return f"fgt.testbed.env.get_dynamic_var('{var_name}')"

        try:
            int(value)
            return value
        except ValueError:
            return f"'{value}'"

    def _render_blocks(
        self,
        blocks: List[dict],
        indent: str,
        param_vars: set[str],
        dynamic_vars: set[str],
    ) -> str:
        """Render parsed blocks into helper function code."""
        code = ""
        for block in blocks:
            if block['type'] == 'command':
                command = self._render_command(block['command'], param_vars, dynamic_vars)
                code += f"{indent}fgt.execute({command})\n"
            elif block['type'] == 'if_chain':
                branches = block['branches']
                else_body = block.get('else_body', [])

                for idx, branch in enumerate(branches):
                    condition = self._translate_condition(branch['condition'], param_vars, dynamic_vars)
                    keyword = 'if' if idx == 0 else 'elif'
                    code += f"{indent}{keyword} {condition}:\n"
                    body_code = self._render_blocks(branch['body'], indent + '    ', param_vars, dynamic_vars)
                    code += body_code if body_code.strip() else f"{indent}    pass\n"

                if else_body:
                    code += f"{indent}else:\n"
                    body_code = self._render_blocks(else_body, indent + '    ', param_vars, dynamic_vars)
                    code += body_code if body_code.strip() else f"{indent}    pass\n"
        return code

    def _render_command(self, command: str, param_vars: set[str], dynamic_vars: set[str]) -> str:
        """Render a DSL command into a Python string literal or f-string."""
        command = command.replace('{', '{{').replace('}', '}}')

        def replace_var(match: re.Match) -> str:
            var_name = match.group(1) or match.group(2)
            if not var_name:
                return match.group(0)
            if var_name.lower() in param_vars:
                return f"{{{var_name.lower()}}}"
            return f"{{fgt.testbed.env.get_dynamic_var('{var_name}')}}"

        replaced = re.sub(r'\{\$(\w+)\}|\$(\w+)', replace_var, command)

        # Escape backslashes and double quotes for Python string
        replaced = replaced.replace('\\', '\\\\').replace('"', '\\"')

        if '{' in replaced or '}' in replaced:
            return f'f"{replaced}"'
        return f'"{replaced}"'
    
    def convert_include(self, include_path: str, include_file: Path, output_dir: Path, force: bool = False) -> dict:
        """
        Convert include file to helper function
        
        Args:
            include_path: Logical path (e.g., testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt)
            include_file: Physical file path
            output_dir: Output directory for generated pytest files
        
        Returns:
            dict: Conversion information
        """
        # Check if already converted
        if self.registry.is_converted(include_path) and not force:
            print(f"  ✓ Already converted: {include_path}")
            return self.registry.get_conversion(include_path)
        
        # Generate helper name
        helper_name = self.generate_helper_name(include_path, include_file)
        
        # Generate helper code
        helper_code = self.convert_to_helper(include_file, helper_name)
        
        # Write helper to dedicated helpers directory
        helpers_dir = output_dir / 'testcases' / 'helpers'
        helpers_dir.mkdir(parents=True, exist_ok=True)
        init_file = helpers_dir / '__init__.py'
        if not init_file.exists():
            init_file.write_text('')

        helper_file = helpers_dir / f"{helper_name}.py"
        helper_file.write_text(helper_code)
        
        conversion_info = {
            'type': 'helper',
            'helper_name': helper_name,
            'helper_file': str(helper_file),
            'hash': self.registry.calculate_hash(include_file),
            'dependencies': [],
            'used_by': []
        }
        
        # Record conversion
        self.registry.add_conversion(include_path, conversion_info)
        
        print(f"  ✓ Converted helper: {include_path} → {helper_name}")
        
        return conversion_info


def main():
    """CLI entry point"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert DSL include files to pytest fixtures')
    parser.add_argument('include_file', help='Include file to convert')
    parser.add_argument('output_dir', help='Output directory')
    parser.add_argument('--include-path', help='Logical include path (optional)')
    
    args = parser.parse_args()
    
    include_file = Path(args.include_file)
    output_dir = Path(args.output_dir)
    
    if not include_file.exists():
        print(f"Error: Include file not found: {include_file}")
        sys.exit(1)
    
    # Generate logical path if not provided
    include_path = args.include_path or str(include_file)
    
    # Initialize registry and converter
    registry = ConversionRegistry()
    converter = IncludeConverter(registry)
    
    # Convert include
    print(f"\nConverting include: {include_file}")
    result = converter.convert_include(include_path, include_file, output_dir)
    
    print(f"\n✓ Conversion complete!")
    print(f"  Type: {result['type']}")
    print(f"  Name: {result.get('fixture_name') or result.get('helper_name')}")
    print(f"  File: {result.get('fixture_file') or result.get('helper_file')}")


if __name__ == '__main__':
    main()
