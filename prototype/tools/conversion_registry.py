"""
Conversion Registry for DSL to pytest Migration
Tracks include → fixture/helper conversions to enable reuse
"""

import json
import hashlib
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List


class ConversionRegistry:
    """Track converted include files to enable reuse"""
    
    def __init__(self, registry_file: str = 'prototype/output/.conversion_registry.json'):
        self.registry_file = Path(registry_file)
        self.registry = self._load_registry()
    
    def _load_registry(self) -> dict:
        """Load existing conversion registry"""
        if self.registry_file.exists():
            with open(self.registry_file) as f:
                return json.load(f)
        return {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "conversions": {}
        }
    
    def save(self):
        """Save registry to disk"""
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        self.registry['last_updated'] = datetime.now().isoformat()
        
        with open(self.registry_file, 'w') as f:
            json.dump(self.registry, f, indent=2)
        
        print(f"✓ Registry saved: {self.registry_file}")
    
    def get_conversion(self, include_path: str) -> Optional[dict]:
        """Get existing conversion info for include file"""
        return self.registry['conversions'].get(include_path)
    
    def add_conversion(self, include_path: str, conversion_info: dict):
        """Record a new conversion"""
        conversion_info['converted_date'] = datetime.now().isoformat()
        self.registry['conversions'][include_path] = conversion_info
        self.save()
        
        print(f"✓ Registered: {include_path} → {conversion_info.get('fixture_name') or conversion_info.get('helper_name')}")
    
    def is_converted(self, include_path: str) -> bool:
        """Check if include file already converted"""
        return include_path in self.registry['conversions']
    
    def mark_usage(self, include_path: str, used_by: str):
        """Track which test uses this include"""
        if include_path in self.registry['conversions']:
            used_by_list = self.registry['conversions'][include_path].get('used_by', [])
            normalized_list = [self._sanitize_identifier(item) for item in used_by_list]
            normalized_used_by = self._sanitize_identifier(used_by)
            if normalized_used_by not in normalized_list:
                normalized_list.append(normalized_used_by)
                self.registry['conversions'][include_path]['used_by'] = normalized_list
                self.save()
            elif normalized_list != used_by_list:
                self.registry['conversions'][include_path]['used_by'] = normalized_list
                self.save()

    @staticmethod
    def _sanitize_identifier(name: str) -> str:
        """Convert a string to a safe identifier by replacing invalid chars.

        Args:
            name: Raw identifier name.

        Returns:
            Sanitized identifier using underscores for invalid characters.
        """
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        if sanitized and sanitized[0].isdigit():
            sanitized = f"_{sanitized}"
        return sanitized
    
    def get_fixture_params(self, include_paths: List[str]) -> List[str]:
        """Get fixture parameter names for test function"""
        fixture_params = []
        
        for include_path in include_paths:
            conversion = self.get_conversion(include_path)
            if conversion and conversion['type'] == 'fixture':
                fixture_params.append(conversion['fixture_name'])
        
        return fixture_params
    
    def calculate_hash(self, file_path: Path) -> str:
        """Calculate file hash for change detection"""
        if not file_path.exists():
            return ""
        return hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]
    
    def has_changed(self, include_path: str, file_path: Path) -> bool:
        """Check if include file has changed since conversion"""
        conversion = self.get_conversion(include_path)
        if not conversion:
            return False
        
        stored_hash = conversion.get('hash', '')
        current_hash = self.calculate_hash(file_path)
        
        return stored_hash != current_hash
    
    def get_stats(self) -> dict:
        """Get registry statistics"""
        conversions = self.registry['conversions']
        
        total = len(conversions)
        fixtures = sum(1 for c in conversions.values() if c['type'] == 'fixture')
        helpers = sum(1 for c in conversions.values() if c['type'] == 'helper')
        
        # Most used includes
        usage_counts = [(path, len(info.get('used_by', []))) 
                       for path, info in conversions.items()]
        most_used = sorted(usage_counts, key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'total_conversions': total,
            'fixtures': fixtures,
            'helpers': helpers,
            'most_used': most_used
        }
    
    def print_stats(self):
        """Print registry statistics"""
        stats = self.get_stats()
        
        print("\n" + "="*60)
        print("CONVERSION REGISTRY STATISTICS")
        print("="*60)
        print(f"Total conversions: {stats['total_conversions']}")
        print(f"  - Fixtures: {stats['fixtures']}")
        print(f"  - Helpers: {stats['helpers']}")
        
        print("\nMost-used includes:")
        for path, count in stats['most_used']:
            print(f"  {count:2d} tests use: {path}")
        
        print("="*60 + "\n")


if __name__ == '__main__':
    # Demo usage
    registry = ConversionRegistry()
    registry.print_stats()
