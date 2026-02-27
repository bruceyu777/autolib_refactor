#!/usr/bin/env python3
"""
Test script to verify mock device factory creates correct types
"""

import sys
from pathlib import Path

# Add fluent_api to path
fluent_api_path = Path(__file__).parent / 'fluent_api'
sys.path.insert(0, str(fluent_api_path))

from mock_device import create_mock_device, MockFortiGate, MockPC


def test_factory():
    """Test that factory creates correct device types"""
    
    print("\n" + "="*70)
    print("Testing Mock Device Factory")
    print("="*70)
    
    # Test FortiGate creation
    fgt_devices = [
        "FGT_A",
        "FGT_PRIMARY",
        "FGTA",
        "FGTB_Node1"
    ]
    
    for name in fgt_devices:
        device = create_mock_device(name)
        is_fgt = isinstance(device, MockFortiGate)
        status = "✓" if is_fgt else "✗"
        print(f"{status} {name:<20} → {device.__class__.__name__}")
        assert is_fgt, f"Expected MockFortiGate for {name}"
    
    print()
    
    # Test PC creation
    pc_devices = [
        "PC_05",
        "PC_01",
        "PC-Linux-01"
    ]
    
    for name in pc_devices:
        device = create_mock_device(name)
        is_pc = isinstance(device, MockPC)
        status = "✓" if is_pc else "✗"
        print(f"{status} {name:<20} → {device.__class__.__name__}")
        assert is_pc, f"Expected MockPC for {name}"
    
    print("\n" + "="*70)
    print("Test FortiGate-specific functionality")
    print("="*70)
    
    fgt = create_mock_device("FGT_A")
    fgt.connect()
    
    # Test IPS signature storage
    result = fgt.execute('''
    config ips custom
    edit "test_sig"
    set signature "F-SBID(--name test)"
    next
    end
    ''')
    
    show_output = fgt.execute("show ips custom")
    has_sig = "test_sig" in show_output
    status = "✓" if has_sig else "✗"
    print(f"{status} IPS signature storage: {has_sig}")
    assert has_sig, "Signature should be stored"
    
    print("\n" + "="*70)
    print("Test PC-specific functionality")
    print("="*70)
    
    pc = create_mock_device("PC_05")
    pc.connect()
    
    # Test file operations
    pc.files["test.txt"] = "content1"
    pc.files["test2.txt"] = "content1"
    
    # Same content - should return empty
    cmp_result = pc.execute("cmp /root/test.txt /root/test2.txt")
    is_empty = cmp_result == ""
    status = "✓" if is_empty else "✗"
    print(f"{status} File comparison (identical): empty output = {is_empty}")
    assert is_empty, "Identical files should return empty"
    
    # Different content
    pc.files["test3.txt"] = "different"
    cmp_result = pc.execute("cmp /root/test.txt /root/test3.txt")
    has_differ = "differ" in cmp_result
    status = "✓" if has_differ else "✗"
    print(f"{status} File comparison (different): has 'differ' = {has_differ}")
    assert has_differ, "Different files should show differ"
    
    # Test rm command
    pc.execute("rm -f /root/test.txt")
    has_file = "test.txt" in pc.files
    status = "✓" if not has_file else "✗"
    print(f"{status} File deletion: file removed = {not has_file}")
    assert not has_file, "File should be removed"
    
    print("\n" + "="*70)
    print("✅ All tests passed!")
    print("="*70 + "\n")


if __name__ == '__main__':
    test_factory()
