"""
Test script to verify environment variable resolution
"""

import sys
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent / 'tools'))
sys.path.insert(0, str(Path(__file__).parent / 'fluent_api'))

from env_parser import parse_env_file
from fluent import TestBed

# Load environment configuration
env_file = '/home/fosqa/autolibv3/autolib_v3/testcase/ips/env.fortistack.ips.conf'
print(f"Loading environment from: {env_file}")
print("=" * 80)

env_config = parse_env_file(env_file)

# Create testbed with mock devices
testbed = TestBed(env_config, use_mock=True)

print("\n✅ TestBed created with environment configuration")
print(f"   Devices in config: {len([k for k in env_config.keys() if k not in ['GLOBAL', 'ORIOLE']])}")

# Test variable resolution
print("\n" + "=" * 80)
print("Testing Variable Resolution")
print("=" * 80)

test_commands = [
    "exe backup ipsuserdefsig ftp FGT_A:CUSTOMSIG1 PC_05:IP_ETH1 root PC_05:PASSWORD",
    "cmp /root/FGT_A:CUSTOMSIG1 /root/FGT_A:CUSTOMSIG2",
    "Some command with FGT_A:Model and PC_05:SCRIPT",
    "command PC_05:IP_ETH1 PC_05:IP6_ETH1 FGT_A:CUSTOMSIG2",
]

for cmd in test_commands:
    resolved = testbed.resolve_variables(cmd)
    print(f"\nOriginal:  {cmd}")
    print(f"Resolved:  {resolved}")
    
# Verify specific resolutions
print("\n" + "=" * 80)
print("Verification")
print("=" * 80)

expected_resolutions = [
    ("FGT_A:CUSTOMSIG1", "custom1on1801F"),
    ("FGT_A:CUSTOMSIG2", "custom2on1801F"),
    ("PC_05:IP_ETH1", "172.16.200.55"),
    ("PC_05:PASSWORD", "Qa123456!"),
    ("FGT_A:Model", "FGVM"),
    ("PC_05:SCRIPT", "/home/tester/attack_scripts"),
]

all_pass = True
for var, expected in expected_resolutions:
    resolved = testbed.resolve_variables(var)
    status = "✅" if resolved == expected else "❌"
    print(f"{status} {var:20} → {resolved:30} (expected: {expected})")
    if resolved != expected:
        all_pass = False

print("\n" + "=" * 80)
if all_pass:
    print("✅ All variable resolutions PASSED")
else:
    print("❌ Some variable resolutions FAILED")
print("=" * 80)

# Test with actual device execute (mock)
print("\n" + "=" * 80)
print("Testing with Mock Device Execute")
print("=" * 80)

with testbed.device('FGT_A') as fgt:
    # This command should have variables resolved automatically
    cmd_with_vars = "exe backup ipsuserdefsig ftp FGT_A:CUSTOMSIG1 PC_05:IP_ETH1 root PC_05:PASSWORD"
    print(f"\nExecuting: {cmd_with_vars}")
    print("(Variables should be auto-resolved before execution)")
    
    output = fgt.execute(cmd_with_vars)
    print(f"✅ Command executed successfully")

print("\n" + "=" * 80)
print("✅ Variable resolution test complete!")
print("=" * 80)
