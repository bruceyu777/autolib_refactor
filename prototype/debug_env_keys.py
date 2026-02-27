"""Debug script to check env config keys"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'tools'))

from env_parser import parse_env_file

env_file = '/home/fosqa/autolibv3/autolib_v3/testcase/ips/env.fortistack.ips.conf'
env_config = parse_env_file(env_file)

print("PC_05 configuration keys:")
print("=" * 80)
pc05_config = env_config.get('PC_05', {})
for key, value in pc05_config.items():
    print(f"  '{key}' = '{value}'")

print("\n" + "=" * 80)
print("FGT_A configuration keys (first 20):")
print("=" * 80)
fgt_config = env_config.get('FGT_A', {})
for i, (key, value) in enumerate(list(fgt_config.items())[:20]):
    print(f"  '{key}' = '{value}'")
