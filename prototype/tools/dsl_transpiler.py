"""
DSL to pytest Transpiler
Main transpiler that converts AutoLib v3 DSL tests to pytest format
with dependency tracking and include handling
"""

import logging
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from conversion_registry import ConversionRegistry
from include_converter import IncludeConverter


class DSLTranspiler:
    """Convert DSL test files to pytest"""
    
    def __init__(self, registry: ConversionRegistry):
        self.registry = registry
        self.converter = IncludeConverter(registry)
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def sanitize_identifier(name: str) -> str:
        """Convert string to valid Python identifier by replacing invalid chars with underscores"""
        # Replace hyphens and other invalid chars with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # Ensure it doesn't start with a digit (prepend underscore)
        if sanitized and sanitized[0].isdigit():
            sanitized = '_' + sanitized
        return sanitized
    
    def parse_test_file(self, test_file: Path) -> dict:
        """
        Parse DSL test file and extract structure
        
        Returns:
            dict with:
                - qaid: Test QAID
                - title: Test title
                - sections: List of [device, commands] sections
                - includes: List of include paths
        """
        content = test_file.read_text()
        
        # Extract QAID from filename or content
        qaid = test_file.stem
        
        # Extract title (first comment or filename)
        title_match = re.search(r'#\s*(.+)', content)
        title = title_match.group(1) if title_match else qaid
        
        # Parse sections: [DEVICE_NAME] ... content ...
        sections = []
        current_device = None
        current_commands = []
        
        for line in content.split('\n'):
            line = line.rstrip()
            
            # Device section marker
            device_match = re.match(r'\[(\w+)\]', line)
            if device_match:
                # Save previous section
                if current_device and current_commands:
                    sections.append({
                        'device': current_device,
                        'commands': current_commands
                    })
                
                # Start new section
                current_device = device_match.group(1)
                current_commands = []
            
            elif current_device:
                current_commands.append(line)
        
        # Save last section
        if current_device and current_commands:
            sections.append({
                'device': current_device,
                'commands': current_commands
            })
        
        # Extract include directives
        includes = self.extract_includes(content)
        
        return {
            'qaid': qaid,
            'title': title,
            'sections': sections,
            'includes': includes
        }
    
    def extract_includes(self, content: str) -> List[dict]:
        """Extract include directives from content"""
        includes = []
        
        # Pattern: include testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt
        # Can be indented with spaces
        for match in re.finditer(r'^\s*include\s+(.+\.txt)', content, re.IGNORECASE | re.MULTILINE):
            include_path = match.group(1).strip()
            includes.append({
                'path': include_path,
                'resolved_path': self.resolve_include_path(include_path)
            })
        
        return includes
    
    def resolve_include_path(self, include_path: str) -> Path:
        """
        Resolve include path to physical file
        
        Handles variable expansion:
        - GLOBAL:VERSION → current version/branch
        - Resolves relative paths
        """
        # Replace variables
        resolved = include_path.replace('GLOBAL:VERSION', 'current')
        resolved = resolved.replace('GLOBAL:Version', 'current')  # Handle case variation
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
        # Extract path components (e.g., current/ips/topology1/govdom1.txt)
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
    
    def convert_dependencies(self, includes: List[dict], output_dir: Path, force: bool = False) -> None:
        """
        Convert include dependencies to helper functions
        Helpers are written to testcases/helpers and can be called inline in tests
        """
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
                        force=force
                    )
                except Exception:
                    self.logger.exception("Failed to convert include: %s", include_path)
                    print(f"  ⚠️  Failed to convert include, continuing: {include_path}")
                # No need to collect helper names - they will be called inline
    
    def convert_section(self, section: dict, qaid: str, indent: str = "    ") -> str:
        """Convert single device section to pytest code"""
        device = section['device']
        commands = section['commands']
        
        # Start device context
        device_var = device.lower()
        pytest_code = f"{indent}with testbed.device('{device}') as {device_var}:\n"
        
        # Collect commands into logical blocks
        blocks = self._group_commands(commands)
        
        # Convert blocks using shared helper
        blocks_code = self._convert_blocks(blocks, qaid, device_var, indent + '    ')
        pytest_code += blocks_code
        
        return pytest_code
    
    def _find_elseif_else_tags(self, commands: List[str], start_idx: int, end_idx: int) -> List[dict]:
        """
        Find all <elseif> and <else> tags within an if block (between start and end)
        Returns list of {'type': 'elseif' or 'else', 'index': int, 'condition': str or None}
        """
        tags = []
        depth = 0
        for i in range(start_idx + 1, end_idx):
            line = commands[i].strip()
            
            # Track nested if blocks
            if line.startswith('<if'):
                depth += 1
            elif line.startswith('<fi>'):
                depth -= 1
            elif depth == 0:  # Only process at same nesting level
                # Check for <elseif condition>
                elseif_match = re.match(r'<elseif\s+(.+)>', line)
                if elseif_match:
                    condition_str = elseif_match.group(1)
                    condition = self._parse_condition(condition_str)
                    tags.append({'type': 'elseif', 'index': i, 'condition': condition})
                elif line.startswith('<else>'):
                    tags.append({'type': 'else', 'index': i, 'condition': None})
        
        return tags
    
    def _find_block_end(self, commands: List[str], start_idx: int, start_tag: str, end_tag: str) -> int:
        """
        Find matching end tag for control flow block
        Handles nested blocks correctly
        """
        depth = 1
        for i in range(start_idx + 1, len(commands)):
            line = commands[i].strip()
            
            # Check for nested start tags
            if line.startswith(start_tag):
                depth += 1
            # Check for end tags
            elif line.startswith(end_tag):
                depth -= 1
                if depth == 0:
                    return i
        
        return -1  # No matching end found
    
    def _parse_condition(self, condition_str: str) -> dict:
        """
        Parse DSL condition into structured format
        Examples:
          {$retry_count} < {$max_retries}
          $PLATFORM_TYPE eq FortiGate-600C
          FGT_A:LOCATION eq robot
        """
        # Pattern 1: {$var} operator value (braced variable)
        match = re.match(r'\{\$(\w+)\}\s*(<|>|eq|ne|<=|>=)\s+(.+)', condition_str.strip())
        if match:
            var_name = match.group(1)
            operator = match.group(2)
            value = match.group(3).strip()
            
            # Check if value is a variable reference {$var}
            var_match = re.match(r'\{\$(\w+)\}', value)
            if var_match:
                value_var = var_match.group(1)
                return {'var': var_name, 'operator': operator, 'value_var': value_var, 'value_type': 'var'}
            else:
                # Literal value (string or number)
                return {'var': var_name, 'operator': operator, 'value': value, 'value_type': 'literal'}
        
        # Pattern 2: $var operator value (unbraced variable - used in if/elseif conditions)
        match = re.match(r'\$(\w+)\s*(<|>|eq|ne|<=|>=)\s+(.+)', condition_str.strip())
        if match:
            var_name = match.group(1)
            operator = match.group(2)
            value = match.group(3).strip()
            
            # Check if value is a variable reference $var
            var_match = re.match(r'\$(\w+)', value)
            if var_match:
                value_var = var_match.group(1)
                return {'var': var_name, 'operator': operator, 'value_var': value_var, 'value_type': 'var'}
            else:
                # Literal value (string or number)
                return {'var': var_name, 'operator': operator, 'value': value, 'value_type': 'literal'}
        
        # Pattern 3: DEVICE:VARIABLE operator value
        match = re.match(r'(\w+):(\w+)\s*(<|>|eq|ne|<=|>=)\s+(.+)', condition_str.strip())
        if match:
            device = match.group(1)
            var_name = match.group(2)
            operator = match.group(3)
            value = match.group(4).strip()
            
            # DEVICE:VARIABLE is resolved via testbed.read_env_variables()
            return {
                'device_var': f"{device}:{var_name}",
                'operator': operator,
                'value': value,
                'value_type': 'device_env'
            }
        
        return {'var': None, 'operator': None, 'value': None, 'value_type': None}
    
    def _translate_condition_to_python(self, condition: dict, device_var: Optional[str] = None) -> str:
        """
        Translate DSL condition to Python expression
        DSL: {$retry_count} < {$max_retries}
        Python: int(device.testbed.env.get_dynamic_var('retry_count')) < int(device.testbed.env.get_dynamic_var('max_retries'))
        
        Or: FGT_A:LOCATION eq robot
        Python: device.testbed.read_env_variables('FGT_A:LOCATION') == 'robot'
        """
        operator = condition['operator']
        value_type = condition.get('value_type')
        
        # Determine env access - use device_var.testbed.env if available
        if device_var:
            env_prefix = f"{device_var}.testbed.env"
            testbed_prefix = f"{device_var}.testbed"
        else:
            env_prefix = "env"
            testbed_prefix = "testbed"
        
        # Map DSL operators to Python
        op_map = {
            '<': '<',
            '>': '>',
            '<=': '<=',
            '>=': '>=',
            'eq': '==',
            'ne': '!='
        }
        python_op = op_map.get(operator, operator)
        
        # Handle DEVICE:VARIABLE pattern (from environment file)
        if value_type == 'device_env':
            device_var_ref = condition['device_var']
            value = condition['value']
            
            # Resolve DEVICE:VARIABLE via testbed.read_env_variables()
            left = f"{testbed_prefix}.read_env_variables('{device_var_ref}')"
            
            # Value is always a string for env comparisons
            try:
                int(value)
                right = value  # Numeric literal
            except ValueError:
                right = f"'{value}'"  # String literal
            
            return f"{left} {python_op} {right}"
        
        # Handle {$VAR} pattern (from script variables)
        var_name = condition.get('var')
        if not var_name:
            return "True"  # Fallback
        
        # Build left side (always a variable)
        left = f"{env_prefix}.get_dynamic_var('{var_name}')"
        
        # Build right side (variable or literal)
        if value_type == 'var':
            value_var = condition['value_var']
            right = f"{env_prefix}.get_dynamic_var('{value_var}')"
        else:
            # Literal value - try to parse as number, otherwise string
            value = condition['value']
            try:
                int(value)
                right = value  # Numeric literal
            except ValueError:
                right = f"'{value}'"  # String literal
        
        # For numeric comparisons, convert to int
        if operator in ['<', '>', '<=', '>=']:
            left = f"int({left})"
            if value_type == 'var':
                right = f"int({right})"
        
        return f"{left} {python_op} {right}"
    
    def _group_commands(self, commands: List[str]) -> List[dict]:
        """Group commands into logical blocks for better formatting"""
        blocks = []
        config_block = []
        in_config = False
        config_depth = 0
        
        i = 0
        while i < len(commands):
            line = commands[i].strip()
            
            if not line or line.startswith('#'):
                i += 1
                continue
            
            # Include directive - convert to helper call
            include_match = re.match(r'include\s+(.+\.txt)', line, re.IGNORECASE)
            if include_match:
                include_path = include_match.group(1).strip()
                # Extract filename from path (e.g., govdom1.txt → govdom1)
                filename = Path(include_path).stem
                helper_name = f"helper_{self.sanitize_identifier(filename)}"
                blocks.append({
                    'type': 'helper_call',
                    'helper_name': helper_name,
                    'include_path': include_path
                })
                i += 1
                continue
            
            # Variable declarations
            # <strset VAR value>
            strset_match = re.match(r'<strset\s+(\w+)\s+(.+)>', line)
            if strset_match:
                var_name = strset_match.group(1)
                value = strset_match.group(2)
                blocks.append({
                    'type': 'varset',
                    'var_type': 'str',
                    'var_name': var_name,
                    'value': value
                })
                i += 1
                continue
            
            # <intset VAR value>
            intset_match = re.match(r'<intset\s+(\w+)\s+(.+)>', line)
            if intset_match:
                var_name = intset_match.group(1)
                value = intset_match.group(2)
                blocks.append({
                    'type': 'varset',
                    'var_type': 'int',
                    'var_name': var_name,
                    'value': value
                })
                i += 1
                continue
            
            # <intchange VAR + value> or <intchange VAR - value>
            intchange_match = re.match(r'<intchange\s+\{\$(\w+)\}\s*([+\-])\s*(\d+)>', line)
            if intchange_match:
                var_name = intchange_match.group(1)
                operation = intchange_match.group(2)
                value = intchange_match.group(3)
                blocks.append({
                    'type': 'varupdate',
                    'var_name': var_name,
                    'operation': operation,
                    'value': value
                })
                i += 1
                continue
            
            # Control flow: <if condition>
            if_match = re.match(r'<if\s+(.+)>', line)
            if if_match:
                condition_str = if_match.group(1)
                condition = self._parse_condition(condition_str)
                
                # Find matching <fi>
                end_idx = self._find_block_end(commands, i, '<if', '<fi>')
                if end_idx > i:
                    # Find all <elseif> and <else> tags within the if block
                    branch_tags = self._find_elseif_else_tags(commands, i, end_idx)
                    
                    if branch_tags:
                        # Build branches list: if + elseif's + else
                        branches = []
                        
                        # First branch: if
                        first_end = branch_tags[0]['index'] if branch_tags else end_idx
                        if_body_commands = commands[i+1:first_end]
                        if_body_blocks = self._group_commands(if_body_commands)
                        branches.append({
                            'type': 'if',
                            'condition': condition,
                            'body': if_body_blocks
                        })
                        
                        # Middle branches: elseif's
                        for idx, tag in enumerate(branch_tags):
                            if tag['type'] == 'elseif':
                                # Find where this elseif body ends
                                next_idx = branch_tags[idx+1]['index'] if idx+1 < len(branch_tags) else end_idx
                                body_commands = commands[tag['index']+1:next_idx]
                                body_blocks = self._group_commands(body_commands)
                                branches.append({
                                    'type': 'elif',
                                    'condition': tag['condition'],
                                    'body': body_blocks
                                })
                            elif tag['type'] == 'else':
                                # Last branch: else
                                body_commands = commands[tag['index']+1:end_idx]
                                body_blocks = self._group_commands(body_commands)
                                branches.append({
                                    'type': 'else',
                                    'body': body_blocks
                                })
                        
                        blocks.append({
                            'type': 'if_elif_else',
                            'branches': branches
                        })
                    else:
                        # No elseif/else, just if body
                        body_commands = commands[i+1:end_idx]
                        body_blocks = self._group_commands(body_commands)
                        
                        blocks.append({
                            'type': 'if',
                            'condition': condition,
                            'body': body_blocks
                        })
                    
                    i = end_idx + 1  # Skip to after <fi>
                    continue
                else:
                    # No matching end found, treat as regular command
                    blocks.append({'type': 'command', 'command': line})
                    i += 1
                    continue
            
            # Control flow: <while condition>
            while_match = re.match(r'<while\s+(.+)>', line)
            if while_match:
                condition_str = while_match.group(1)
                condition = self._parse_condition(condition_str)
                
                # Find matching <endwhile>
                end_idx = self._find_block_end(commands, i, '<while', '<endwhile')
                if end_idx > i:
                    # Extract body commands
                    body_commands = commands[i+1:end_idx]
                    body_blocks = self._group_commands(body_commands)
                    
                    blocks.append({
                        'type': 'while',
                        'condition': condition,
                        'body': body_blocks
                    })
                    i = end_idx + 1  # Skip to after <endwhile>
                    continue
                else:
                    # No matching end found, treat as regular command
                    blocks.append({'type': 'command', 'command': line})
                    i += 1
                    continue
            
            # Expect assertion
            # Use a more robust pattern that captures everything between quotes, including escaped quotes
            expect_match = re.match(r'expect\s+-e\s+"(.+?)"\s+(?:-for|-t|-fail|$)', line, re.IGNORECASE)
            if expect_match:
                # Flush any pending config block
                if config_block:
                    blocks.append({'type': 'config_block', 'lines': config_block})
                    config_block = []
                    in_config = False
                
                pattern = expect_match.group(1)
                should_fail = '-fail match' in line
                blocks.append({'type': 'expect', 'pattern': pattern, 'should_fail': should_fail})
                i += 1
                continue
            
            # Config block start
            if re.match(r'^config\s+', line, re.IGNORECASE):
                # Start new config block
                if config_block and not in_config:
                    blocks.append({'type': 'config_block', 'lines': config_block})
                    config_block = []
                
                in_config = True
                config_depth = 1
                config_block.append(line)
                i += 1
                continue
            
            # Config block end
            if line.lower() == 'end' and in_config:
                config_block.append(line)
                config_depth -= 1
                
                if config_depth == 0:
                    # End of config block
                    blocks.append({'type': 'config_block', 'lines': config_block})
                    config_block = []
                    in_config = False
                i += 1
                continue
            
            # Inside config block
            if in_config:
                config_block.append(line)
                # Track nested config blocks
                if re.match(r'^config\s+', line, re.IGNORECASE):
                    config_depth += 1
                i += 1
                continue
            
            # Regular command
            blocks.append({'type': 'command', 'command': line})
            i += 1
        
        # Flush any pending config block
        if config_block:
            blocks.append({'type': 'config_block', 'lines': config_block})
        
        return blocks
    
    def _resolve_variables(self, text: str, device_var: str = "device") -> tuple[str, bool]:
        """
        Resolve variable references {$VAR} in text to Python f-string format
        Returns (resolved_text, has_variables)
        """
        # Check if text contains variable references
        if not re.search(r'\{\$\w+\}', text):
            return text, False
        
        # Replace {$VAR} with {device.testbed.env.get_dynamic_var('VAR')} for f-string
        def replace_var(match):
            var_name = match.group(1)
            return f"{{{device_var}.testbed.env.get_dynamic_var('{var_name}')}}"
        
        resolved = re.sub(r'\{\$(\w+)\}', replace_var, text)
        return resolved, True
    
    def _convert_blocks(self, blocks: List[dict], qaid: str, device_var: str, indent: str) -> str:
        """
        Convert list of command blocks to pytest code
        Used for both top-level and nested (control flow body) blocks
        """
        pytest_code = ""
        
        for i, block in enumerate(blocks):
            if block['type'] == 'varset':
                var_name = block['var_name']
                var_type = block['var_type']
                value = block['value']
                
                # Resolve variable references
                value, has_vars = self._resolve_variables(value, device_var)
                
                if var_type == 'int':
                    if has_vars:
                        pytest_code += f'{indent}{device_var}.testbed.env.add_var("{var_name}", f"{value}")\n'
                    else:
                        pytest_code += f'{indent}{device_var}.testbed.env.add_var("{var_name}", {value})\n'
                else:  # str
                    if has_vars:
                        pytest_code += f'{indent}{device_var}.testbed.env.add_var("{var_name}", f"{value}")\n'
                    else:
                        pytest_code += f'{indent}{device_var}.testbed.env.add_var("{var_name}", "{value}")\n'
            
            elif block['type'] == 'varupdate':
                var_name = block['var_name']
                operation = block['operation']
                value = block['value']
                
                if operation == '+':
                    pytest_code += f'{indent}{device_var}.testbed.env.add_var("{var_name}", int({device_var}.testbed.env.get_dynamic_var("{var_name}")) + {value})\n'
                else:  # -
                    pytest_code += f'{indent}{device_var}.testbed.env.add_var("{var_name}", int({device_var}.testbed.env.get_dynamic_var("{var_name}")) - {value})\n'
            
            elif block['type'] == 'helper_call':
                # Generate inline helper function call
                helper_name = self.sanitize_identifier(block['helper_name'])
                pytest_code += f'{indent}{helper_name}({device_var})\n'
            
            elif block['type'] == 'if':
                condition = block['condition']
                python_condition = self._translate_condition_to_python(condition, device_var)
                pytest_code += f'{indent}if {python_condition}:\n'
                
                # Process body recursively
                body_code = self._convert_blocks(block['body'], qaid, device_var, indent + '    ')
                pytest_code += body_code
            
            elif block['type'] == 'if_else':
                condition = block['condition']
                python_condition = self._translate_condition_to_python(condition, device_var)
                pytest_code += f'{indent}if {python_condition}:\n'
                
                # Process if body
                if_body_code = self._convert_blocks(block['if_body'], qaid, device_var, indent + '    ')
                if if_body_code.strip():
                    pytest_code += if_body_code
                else:
                    pytest_code += f'{indent}    pass\n'
                
                # Process else body
                pytest_code += f'{indent}else:\n'
                else_body_code = self._convert_blocks(block['else_body'], qaid, device_var, indent + '    ')
                if else_body_code.strip():
                    pytest_code += else_body_code
                else:
                    pytest_code += f'{indent}    pass\n'
            
            elif block['type'] == 'if_elif_else':
                # Handle if/elif/else chains
                branches = block['branches']
                
                for branch_idx, branch in enumerate(branches):
                    if branch['type'] == 'if':
                        condition = branch['condition']
                        python_condition = self._translate_condition_to_python(condition, device_var)
                        pytest_code += f'{indent}if {python_condition}:\n'
                        
                        # Process if body
                        body_code = self._convert_blocks(branch['body'], qaid, device_var, indent + '    ')
                        if body_code.strip():
                            pytest_code += body_code
                        else:
                            pytest_code += f'{indent}    pass\n'
                    
                    elif branch['type'] == 'elif':
                        condition = branch['condition']
                        python_condition = self._translate_condition_to_python(condition, device_var)
                        pytest_code += f'{indent}elif {python_condition}:\n'
                        
                        # Process elif body
                        body_code = self._convert_blocks(branch['body'], qaid, device_var, indent + '    ')
                        if body_code.strip():
                            pytest_code += body_code
                        else:
                            pytest_code += f'{indent}    pass\n'
                    
                    elif branch['type'] == 'else':
                        pytest_code += f'{indent}else:\n'
                        
                        # Process else body
                        body_code = self._convert_blocks(branch['body'], qaid, device_var, indent + '    ')
                        if body_code.strip():
                            pytest_code += body_code
                        else:
                            pytest_code += f'{indent}    pass\n'
            
            elif block['type'] == 'while':
                condition = block['condition']
                python_condition = self._translate_condition_to_python(condition, device_var)
                pytest_code += f'{indent}while {python_condition}:\n'
                
                # Process body recursively
                body_code = self._convert_blocks(block['body'], qaid, device_var, indent + '    ')
                pytest_code += body_code
            
            elif block['type'] == 'config_block':
                config_lines = '\n'.join(['    ' + line for line in block['lines']])
                
                # Check if next block is expect
                if i + 1 < len(blocks) and blocks[i + 1]['type'] == 'expect':
                    next_block = blocks[i + 1]
                    pattern = next_block['pattern']
                    should_fail = next_block.get('should_fail', False)
                    
                    pytest_code += f'{indent}{device_var}.execute("""\n{config_lines}\n{indent}""")'
                    if should_fail:
                        pytest_code += f'.expect({repr(pattern)}, qaid="{qaid}", should_fail=True)\n'
                    else:
                        pytest_code += f'.expect({repr(pattern)}, qaid="{qaid}")\n'
                    
                    blocks[i + 1] = {'type': 'processed'}
                else:
                    pytest_code += f'{indent}{device_var}.execute("""\n{config_lines}\n{indent}""")\n'
            
            elif block['type'] == 'command':
                cmd = block['command']
                # Resolve variables in command
                resolved_cmd, has_vars = self._resolve_variables(cmd, device_var)
                
                # Generate command with  proper quoting
                if has_vars:
                    # Use f-string for variable interpolation
                    # Check for double quotes in command to choose appropriate wrapper
                    if '"' in resolved_cmd:
                        quoted_cmd = f"f'{resolved_cmd}'"
                    else:
                        quoted_cmd = f'f"{resolved_cmd}"'
                else:
                    quoted_cmd = self._quote_command(cmd)
                
                # Check if next block is expect
                if i + 1 < len(blocks) and blocks[i + 1]['type'] == 'expect':
                    next_block = blocks[i + 1]
                    pattern = next_block['pattern']
                    should_fail = next_block.get('should_fail', False)
                    
                    pytest_code += f'{indent}{device_var}.execute({quoted_cmd})'
                    if should_fail:
                        pytest_code += f'.expect({repr(pattern)}, qaid="{qaid}", should_fail=True)\n'
                    else:
                        pytest_code += f'.expect({repr(pattern)}, qaid="{qaid}")\n'
                    
                    blocks[i + 1] = {'type': 'processed'}
                else:
                    pytest_code += f'{indent}{device_var}.execute({quoted_cmd})\n'
            
            elif block['type'] == 'expect':
                # Standalone expect - checks output from last command
                pattern = block['pattern']
                should_fail = block.get('should_fail', False)
                
                # Generate standalone expect call on device
                # This checks the last command's output (tracked by executor)
                if should_fail:
                    pytest_code += f'{indent}{device_var}.expect({repr(pattern)}, qaid="{qaid}", should_fail=True)\n'
                else:
                    pytest_code += f'{indent}{device_var}.expect({repr(pattern)}, qaid="{qaid}")\n'
            
            elif block['type'] == 'processed':
                continue
        
        return pytest_code
    
    def _quote_command(self, command: str) -> str:
        """Quote command appropriately based on content"""
        # If command contains double quotes, use single quotes
        if '"' in command and "'" not in command:
            return f"'{command}'"
        # If command contains single quotes, use double quotes
        elif "'" in command and '"' not in command:
            return f'"{command}"'
        # If contains both or neither, use double quotes and escape
        elif '"' in command and "'" in command:
            # Escape double quotes
            escaped = command.replace('\\', '\\\\').replace('"', '\\"')
            return f'"{escaped}"'
        else:
            return f'"{command}"'
    
    def generate_test_function(self, parsed: dict) -> str:
        """Generate complete pytest test function"""
        qaid = parsed['qaid']
        title = parsed['title']
        sections = parsed['sections']
        
        # Sanitize QAID for use as function name
        sanitized_qaid = self.sanitize_identifier(qaid)
        
        # Test only needs testbed parameter (helpers called inline)
        param_str = 'testbed'
        
        # Start test function
        test_code = f'''
def test_{sanitized_qaid}({param_str}):
    """
    {title}
    
    QAID: {qaid}
    """
'''
        
        # Add sections
        for section in sections:
            test_code += self.convert_section(section, qaid)
        
        # Add result reporting
        test_code += f'''
    # All assertions tracked under QAID {qaid}
    testbed.results.report("{qaid}")
'''
        
        return test_code
    
    def generate_conftest_header(self, env_file: Optional[Path] = None) -> str:
        """Generate conftest.py header with environment configuration"""
        
        # Base imports and setup
        header = '''"""
Auto-generated conftest.py
Contains fixtures converted from DSL include files
"""

import pytest
from pathlib import Path
import sys

# Add fluent API to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'fluent_api'))

from fluent import TestBed
'''
        
        # Add env parser if env_file is provided
        if env_file:
            # Convert to absolute path for reliability
            abs_env_file = env_file.resolve() if isinstance(env_file, Path) else Path(env_file).resolve()
            
            header += f'''
# Add tools to path for env parser
sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))

from env_parser import parse_env_file


# Environment configuration file
ENV_FILE = r'{abs_env_file}'


@pytest.fixture
def testbed():
    """
    TestBed fixture with device connections
    Loads environment from {abs_env_file.name}
    
    Note: Set use_mock=True for prototype testing with mock devices.
          Set use_mock=False (or remove parameter) for real device testing.
          Can also set environment variable: USE_MOCK_DEVICES=true
    """
    # Load environment configuration from file
    env_config = parse_env_file(ENV_FILE)
    
    # For prototype: use mock devices
    # For production: use_mock=False or remove parameter to use real devices
    testbed = TestBed(env_config, use_mock=True)
    return testbed
'''
        else:
            # Fallback to minimal hardcoded config
            header += '''

@pytest.fixture
def testbed():
    """
    TestBed fixture with device connections
    Uses minimal default configuration
    
    Note: Set use_mock=True for prototype testing with mock devices.
          Set use_mock=False (or remove parameter) for real device testing.
          Can also set environment variable: USE_MOCK_DEVICES=true
          
    Warning: No environment file specified! Using minimal defaults.
             For real testing, specify -e/--env parameter with env config file.
    """
    # Create minimal env config for devices
    env_config = {
        'FGT_A': {'hostname': 'FGT_A', 'type': 'fortigate'},
        'FGT_B': {'hostname': 'FGT_B', 'type': 'fortigate'},
        'FGT_C': {'hostname': 'FGT_C', 'type': 'fortigate'},
        'PC_01': {'hostname': 'PC_01', 'type': 'linux'},
        'PC_02': {'hostname': 'PC_02', 'type': 'linux'},
        'PC_05': {'hostname': 'PC_05', 'type': 'linux'},
    }
    
    # For prototype: use mock devices
    # For production: use_mock=False or remove parameter to use real devices
    testbed = TestBed(env_config, use_mock=True)
    return testbed
'''
        
        # Add pytest hooks for test execution tracking
        header += '''
import logging
from datetime import datetime
import json


# ===== Pytest Hooks =====

def pytest_addoption(parser):
    """Add custom command line options for group file support"""
    parser.addoption(
        "--grp-file",
        action="store",
        default=None,
        help="Group file name to enforce test execution order"
    )


def pytest_collection_modifyitems(config, items):
    """
    Reorder tests based on group file order and filter out tests not in group
    Reads .pytest-order.txt to determine test execution sequence
    """
    # Check if order file exists
    order_file = Path(__file__).parent / '.pytest-order.txt'
    
    if not order_file.exists():
        # No order file, use default pytest collection order
        return
    
    # Read test order from file
    # Format: order:pytest_filename
    # Example: 0:test__205812.py
    test_order = {}
    grp_file_name = None
    
    try:
        with open(order_file, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    # Try to extract grp file name from comment
                    if 'from:' in line:
                        parts = line.split('from:')
                        if len(parts) > 1:
                            grp_file_name = parts[1].strip()
                    continue
                
                # Parse order:filename
                if ':' in line:
                    order, filename = line.split(':', 1)
                    test_order[filename.strip()] = int(order.strip())
    
    except Exception as e:
        print(f"Warning: Failed to read test order file: {e}")
        return
    
    # If order file is empty, return
    if not test_order:
        return
    
    # Reorder items based on order file and filter out tests not in group
    def get_order(item):
        """Get order for a test item"""
        # Extract filename from item nodeid
        # Example: testcases/test__205812.py::test__205812 -> test__205812.py
        nodeid_file = item.nodeid.split('::')[0]
        # Get just the filename without directory path
        filename = Path(nodeid_file).name
        
        # Return order if found, otherwise -1 to mark for deselection
        return test_order.get(filename, -1)
    
    # Deselect tests not in the group file
    items_to_remove = []
    for item in items:
        if get_order(item) == -1:
            items_to_remove.append(item)
    
    for item in items_to_remove:
        items.remove(item)
    
    # Sort remaining items by order
    items[:] = sorted(items, key=get_order)
    
    # Print reordering info if verbose
    if config.option.verbose > 0 and grp_file_name:
        print(f"\\n📋 Test execution order from: {grp_file_name}")
        print(f"   Reordered {len(items)} tests from group file")
        print(f"   Deselected {len(items_to_remove)} tests not in group\\n")


# ===== Test Execution Tracking =====

# Global list to track test execution order and outcomes
_test_execution_order = []
_test_execution_counter = 0
_test_outcomes = {}  # Dictionary to store test outcomes


def pytest_runtest_makereport(item, call):
    """
    Hook to track test execution order and outcomes
    """
    global _test_execution_counter, _test_outcomes
    
    if call.when == "call":
        # Increment counter when test is about to run
        _test_execution_counter += 1
        item.execution_sequence = _test_execution_counter
        item.user_properties.append(("execution_order", f"#{_test_execution_counter}"))
    
    # Capture outcome from any phase (setup, call, or teardown)
    test_file = Path(item.nodeid.split('::')[0]).name.replace('.py', '')
    
    if call.excinfo is not None:
        # If there's an exception in any phase, mark as failed
        _test_outcomes[test_file] = {
            'outcome': 'FAILED',
            'nodeid': item.nodeid
        }
    elif call.when == "call" and call.excinfo is None:
        # Only mark as passed after successful call phase
        # Don't overwrite a failure from setup
        if test_file not in _test_outcomes or _test_outcomes[test_file]['outcome'] != 'FAILED':
            _test_outcomes[test_file] = {
                'outcome': 'PASSED',
                'nodeid': item.nodeid
            }


def pytest_sessionfinish(session, exitstatus):
    """
    Generate execution order summary after all tests complete
    Also save test results to JSON for report generation
    """
    
    # Create reports directory if it doesn't exist
    reports_dir = Path(__file__).parent / 'reports'
    reports_dir.mkdir(exist_ok=True)
    
    # Save test results to JSON
    results_file = reports_dir / 'test_results.json'
    try:
        with open(results_file, 'w') as f:
            json.dump(_test_outcomes, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save test results: {e}")
    
    # Print execution order summary
    print("\\n" + "="*70)
    print("TEST EXECUTION ORDER SUMMARY")
    print("="*70)
    
    # Check if order file exists to show what was enforced
    order_file = Path(__file__).parent / '.pytest-order.txt'
    if order_file.exists():
        try:
            with open(order_file, 'r') as f:
                # Read first few lines to show order was enforced
                lines = f.readlines()[:3]
                print("\\n✓ Test execution order from .pytest-order.txt was enforced:")
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split(':')
                        if len(parts) == 2:
                            print(f"  {parts[0]:>3}. {parts[1]}")
                print(f"  ... and {len([l for l in lines if ':' in l and not l.startswith('#')])-3} more tests\\n")
        except:
            pass
    
    print("📊 HTML Report: reports/test_report.html")
    print("   Note: HTML report displays by outcome (passed/failed)")
    print("   Execution order is enforced in console output above\\n")
    print("="*70)


@pytest.fixture
def logger(request):
    """
    Logger fixture for test cases
    Provides a logger instance with test-specific context
    
    Usage in tests:
        def test_example(testbed, logger):
            logger.info("Starting test execution")
            logger.debug("Device configuration: %s", config)
            logger.warning("Unexpected behavior detected")
            logger.error("Test failed due to exception")
    """
    # Get test name from request
    test_name = request.node.name
    test_file = request.node.fspath.basename
    
    # Create logger with test-specific name
    log = logging.getLogger(f"{test_file}::{test_name}")
    
    # Add test metadata to logger
    log.test_name = test_name
    log.test_file = test_file
    log.start_time = datetime.now()
    
    # Log test start
    log.info("="*60)
    log.info("Test started: %s", test_name)
    log.info("="*60)
    
    yield log
    
    # Log test end
    duration = (datetime.now() - log.start_time).total_seconds()
    log.info("="*60)
    log.info("Test completed: %s (%.2fs)", test_name, duration)
    log.info("="*60)


# ===== Auto-generated fixtures from include files =====
'''
        
        return header
    
    def generate_test_header(self, qaid: str, original_file: Path, helper_names: List[str] = None) -> str:
        """Generate test file header with helper imports"""
        header = f'''"""
Auto-generated pytest test for QAID {qaid}

Original DSL: {original_file}
Generated by: DSL Transpiler
"""

import pytest
from pathlib import Path
import sys

# Add fluent API to path (go up to prototype directory)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'fluent_api'))

from fluent import TestBed
'''
        
        # Import helper functions from helpers package if any
        if helper_names:
            # Import from testcases/helpers
            header += f"\n# Import helper functions from helpers\n"
            header += f"sys.path.insert(0, str(Path(__file__).parent))\n"
            for helper_name in helper_names:
                module_name = helper_name
                header += f"from helpers.{module_name} import {helper_name}\n"
        
        header += "\n\n# ===== Test Function =====\n"
        return header
    
    def transpile(self, test_file: Path, output_dir: Path, env_file: Optional[Path] = None) -> dict:
        """
        Main transpilation workflow
        
        Args:
            test_file: DSL test file to convert
            output_dir: Output directory for generated files
            env_file: Optional environment configuration file
        
        Returns:
            dict with conversion results
        """
        print("\n" + "="*60)
        print(f"TRANSPILING: {test_file.name}")
        print("="*60)
        
        # 1. Parse DSL test
        print("\n[1/5] Parsing DSL test...")
        parsed = self.parse_test_file(test_file)
        print(f"  ✓ QAID: {parsed['qaid']}")
        print(f"  ✓ Title: {parsed['title']}")
        print(f"  ✓ Sections: {len(parsed['sections'])}")
        print(f"  ✓ Includes: {len(parsed['includes'])}")
        
        # 2. Initialize conftest.py
        print("\n[2/5] Initializing conftest.py...")
        output_dir.mkdir(parents=True, exist_ok=True)
        conftest_file = output_dir / 'conftest.py'
        conftest_needs_header = (not conftest_file.exists()) or conftest_file.stat().st_size == 0

        if conftest_needs_header:
            conftest_file.write_text(self.generate_conftest_header(env_file))
            print(f"  ✓ Created: {conftest_file}")
            if env_file:
                print(f"    Using env config: {env_file}")
        else:
            print(f"  ✓ Using existing: {conftest_file}")
        
        # 3. Convert dependencies (includes → helpers)
        print("\n[3/5] Converting include dependencies...")
        self.convert_dependencies(parsed['includes'], output_dir, force=conftest_needs_header)
        print(f"  ✓ Helpers generated: {len(parsed['includes'])} includes converted")
        
        # Collect unique helper names for imports
        helper_names = []
        for include in parsed['includes']:
            include_path = include['path']
            filename = Path(include_path).stem
            helper_name = f"helper_{self.sanitize_identifier(filename)}"
            if helper_name not in helper_names:
                helper_names.append(helper_name)
        
        # 4. Mark usage in registry
        print("\n[4/5] Updating registry...")
        for include in parsed['includes']:
            sanitized_used_by = self.sanitize_identifier(f"test_{parsed['qaid']}")
            self.registry.mark_usage(include['path'], sanitized_used_by)
        
        # 5. Generate test file
        print("\n[5/5] Generating test file...")
        test_code = self.generate_test_header(parsed['qaid'], test_file, helper_names)
        test_code += self.generate_test_function(parsed)
        
        # Sanitize QAID for filename
        sanitized_qaid = self.sanitize_identifier(parsed['qaid'])
        
        # Output test to testcases/ subdirectory
        testcases_dir = output_dir / 'testcases'
        testcases_dir.mkdir(exist_ok=True)
        test_output = testcases_dir / f"test_{sanitized_qaid}.py"
        test_output.write_text(test_code)
        print(f"  ✓ Created: {test_output}")
        
        # Summary
        result = {
            'qaid': parsed['qaid'],
            'test_file': str(test_output),
            'helpers': len(parsed['includes']),
            'sections': len(parsed['sections']),
            'includes': len(parsed['includes'])
        }
        
        print("\n" + "="*60)
        print("TRANSPILATION COMPLETE")
        print("="*60)
        print(f"Test file: {test_output}")
        print(f"Helpers: {len(parsed['includes'])} includes converted to callable helpers")
        print("="*60 + "\n")
        
        return result


def main():
    """CLI entry point"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Transpile DSL test to pytest')
    parser.add_argument('test_file', help='DSL test file to convert')
    parser.add_argument('--output-dir', default='prototype/output', help='Output directory')
    parser.add_argument('--env', help='Environment configuration file')
    
    args = parser.parse_args()
    
    test_file = Path(args.test_file)
    output_dir = Path(args.output_dir)
    env_file = Path(args.env) if args.env else None
    
    if not test_file.exists():
        print(f"Error: Test file not found: {test_file}")
        sys.exit(1)
    
    if env_file and not env_file.exists():
        print(f"Error: Environment file not found: {env_file}")
        sys.exit(1)
    
    # Initialize registry and transpiler
    registry = ConversionRegistry()
    transpiler = DSLTranspiler(registry)
    
    # Transpile
    result = transpiler.transpile(test_file, output_dir, env_file)
    
    # Show registry stats
    registry.print_stats()


if __name__ == '__main__':
    main()
