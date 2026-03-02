"""
DSL Parser Module
Handles parsing of DSLtest files and include extraction
"""

import logging
import re
import sys
from pathlib import Path
from typing import List, Dict

# Set up unified logging to prototype/logs/
_PROTOTYPE_DIR = Path(__file__).resolve().parent.parent
if str(_PROTOTYPE_DIR) not in sys.path:
    sys.path.insert(0, str(_PROTOTYPE_DIR))
try:
    from common.common_logging import setup_script_logging
    logger = setup_script_logging(__file__, log_dir=_PROTOTYPE_DIR / 'logs')
except ImportError:
    logger = logging.getLogger(__name__)


class DSLParser:
    """Parse DSL test files into structured format"""
    
    def __init__(self):
        """Initialize DSL parser"""
        pass
    
    def parse_test_file(self, test_file: Path) -> dict:
        """
        Parse DSL test file and extract structure
        
        Args:
            test_file: Path to DSL test file
            
        Returns:
            Dictionary with:
                - qaid: Test QAID
                - title: Test title
                - sections: List of [device, commands] sections  
                - includes: List of include paths
        """
        content = test_file.read_text()
        logger.info("[parse_test_file] Parsing: '%s'", test_file.resolve())
        
        # Extract QAID from filename or content
        qaid = test_file.stem
        
        # Extract title (first comment or filename)
        title_match = re.search(r'#\s*(.+)', content)
        title = title_match.group(1) if title_match else qaid
        
        # Parse sections: [DEVICE_NAME] ... content ...
        sections = self._parse_sections(content)
        
        # Extract include directives
        includes = self.extract_includes(content)
        
        logger.info("[parse_test_file] qaid=%s | title='%s' | sections=%d | includes=%d",
                    qaid, title, len(sections), len(includes))
        for inc in includes:
            logger.debug("[parse_test_file]   include: '%s' device=%s", inc['path'], inc['device'])
        
        return {
            'qaid': qaid,
            'title': title,
            'sections': sections,
            'includes': includes
        }
    
    def _parse_sections(self, content: str) -> List[dict]:
        """
        Parse device sections from DSL content
        
        Args:
            content: DSL file content
            
        Returns:
            List of section dictionaries with device and commands
        """
        sections = []
        current_device = None
        current_commands = []
        
        for line in content.split('\n'):
            line = line.rstrip()
            
            # Device section marker: [DEVICE_NAME]
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
        
        return sections
    
    def extract_includes(self, content: str) -> List[dict]:
        """
        Extract include directives from content
        
        Args:
            content: DSL file content
            
        Returns:
            List of include dictionaries with path and device
        """
        includes = []
        
        # Pattern: include testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt
        # Can be indented with spaces
        include_pattern = r'^\s*include\s+(.+)$'
        
        current_device = None
        for line in content.split('\n'):
            # Track current device section
            device_match = re.match(r'\[(\w+)\]', line)
            if device_match:
                current_device = device_match.group(1)
            
            # Check for include directive
            include_match = re.match(include_pattern, line)
            if include_match:
                include_path = include_match.group(1).strip()
                entry = {
                    'path': include_path,
                    'device': current_device or 'GLOBAL',
                    'line': line.strip()
                }
                includes.append(entry)
                logger.debug("[extract_includes] found include: '%s' (device=%s)",
                             include_path, entry['device'])
        
        logger.info("[extract_includes] Total includes found: %d", len(includes))
        return includes
    
    def resolve_include_path(self, include_path: str, base_path: Path = None) -> Path:
        """
        Resolve include path to actual file path
        
        Args:
            include_path: Include path from DSL (e.g., testcase/GLOBAL:VERSION/...)
            base_path: Base path for resolution
            
        Returns:
            Resolved Path object
        """
        # Handle GLOBAL:VERSION pattern
        # Replace GLOBAL:VERSION with just GLOBAL
        resolved_path = include_path.replace('GLOBAL:VERSION', 'GLOBAL')
        
        # Remove 'testcase/' prefix if present
        if resolved_path.startswith('testcase/'):
            resolved_path = resolved_path[9:]  # len('testcase/') = 9
        
        # Create Path object
        if base_path:
            result = base_path / resolved_path
        else:
            result = Path(resolved_path)
        
        logger.debug("[resolve_include_path] '%s' → '%s' (base=%s)", include_path, result, base_path)
        return result
