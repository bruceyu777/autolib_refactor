#!/usr/bin/env python3
"""
Demonstration: Switching between Mock and Real Devices

Shows how the flexible device architecture works with both
mock devices (for testing) and real AutoLib v3 devices.
"""

import sys
import os
from pathlib import Path

# Add fluent_api to path
sys.path.insert(0, str(Path(__file__).parent / 'fluent_api'))

from fluent import TestBed


def demo_mock_devices():
    """Demo: Using mock devices for testing"""
    print("\n" + "="*70)
    print("DEMO 1: Using Mock Devices (for prototyping/testing)")
    print("="*70)
    
    # Create testbed with mock devices
    testbed = TestBed(use_mock=True)
    
    print(f"✓ TestBed created with use_mock={testbed.use_mock}")
    
    # Test FortiGate mock
    with testbed.device('FGT_A') as fgt:
        print(f"✓ Created device: {fgt.device.__class__.__name__}")
        
        fgt.execute('''
        config ips custom
        edit "test_signature"
        set signature "F-SBID(--name test)"
        next
        end
        ''')
        
        output = fgt.execute("show ips custom")
        has_sig = "test_signature" in output.output
        print(f"✓ IPS signature operation: {'PASS' if has_sig else 'FAIL'}")
    
    # Test PC mock
    with testbed.device('PC_05') as pc:
        print(f"✓ Created device: {pc.device.__class__.__name__}")
        
        # Simulate file operation
        pc.device.files["test.txt"] = "content"
        result = pc.execute("ls /root/")
        has_file = "test.txt" in result.output or result.output == "test.txt"
        print(f"✓ PC file operation: {'PASS' if has_file else 'FAIL'}")
    
    print("="*70 + "\n")


def demo_real_devices():
    """Demo: Using real AutoLib v3 devices"""
    print("\n" + "="*70)
    print("DEMO 2: Using Real AutoLib v3 Devices")
    print("="*70)
    
    # Create testbed with real devices
    testbed = TestBed(use_mock=False)
    
    print(f"✓ TestBed created with use_mock={testbed.use_mock}")
    print("⚠️  Note: This would connect to real devices if they are available")
    print("    in the environment configuration.")
    
    # This would work with real devices if they're configured
    # with testbed.device('FGT_A') as fgt:
    #     fgt.execute("get system status")
    #     fgt.expect("FortiGate")
    
    print("="*70 + "\n")


def demo_environment_variable():
    """Demo: Using environment variable to control mock/real"""
    print("\n" + "="*70)
    print("DEMO 3: Using Environment Variable")
    print("="*70)
    
    # Set environment variable
    os.environ['USE_MOCK_DEVICES'] = 'true'
    
    # Create testbed without specifying use_mock
    # It will read from environment variable
    testbed = TestBed()
    
    print(f"✓ Environment variable: USE_MOCK_DEVICES={os.getenv('USE_MOCK_DEVICES')}")
    print(f"✓ TestBed auto-detected: use_mock={testbed.use_mock}")
    
    with testbed.device('FGT_A') as fgt:
        print(f"✓ Created device: {fgt.device.__class__.__name__}")
    
    # Clean up
    del os.environ['USE_MOCK_DEVICES']
    
    print("="*70 + "\n")


def demo_backward_compatibility():
    """Demo: Backward compatibility with FluentFortiGate"""
    print("\n" + "="*70)
    print("DEMO 4: Backward Compatibility")
    print("="*70)
    
    from fluent import FluentFortiGate, FluentDevice
    
    # FluentFortiGate is now an alias to FluentDevice
    print(f"✓ FluentFortiGate is FluentDevice: {FluentFortiGate is FluentDevice}")
    print("✓ Existing code using FluentFortiGate will continue to work")
    
    print("="*70 + "\n")


def show_usage_guide():
    """Show usage guide for switching modes"""
    print("\n" + "="*70)
    print("USAGE GUIDE: Switching Between Mock and Real Devices")
    print("="*70)
    
    print("""
# Method 1: Explicit parameter
testbed = TestBed(use_mock=True)   # Use mock devices
testbed = TestBed(use_mock=False)  # Use real devices

# Method 2: Environment variable
export USE_MOCK_DEVICES=true       # Use mock devices
export USE_MOCK_DEVICES=false      # Use real devices
testbed = TestBed()                # Auto-detects from env var

# Method 3: Default behavior
testbed = TestBed()                # Defaults to real devices (use_mock=False)

# Generated conftest.py controls mode:
@pytest.fixture
def testbed():
    # For prototype testing:
    return TestBed(env_config, use_mock=True)
    
    # For real device testing:
    # return TestBed(env_config, use_mock=False)
    # or simply:
    # return TestBed(env_config)  # Defaults to real

# Supported device types:
# Mock:  MockFortiGate, MockPC
# Real:  FortiGate, Pc, Computer, FortiSwitch, FortiAP, etc.
    """)
    
    print("="*70 + "\n")


def main():
    """Run all demos"""
    print("\n" + "#"*70)
    print("# Flexible Device Architecture Demo")
    print("# Mock Devices ⟷ Real Devices")
    print("#"*70)
    
    # Run demos
    demo_mock_devices()
    demo_real_devices()
    demo_environment_variable()
    demo_backward_compatibility()
    show_usage_guide()
    
    print("\n" + "="*70)
    print("✅ All demos completed successfully!")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
