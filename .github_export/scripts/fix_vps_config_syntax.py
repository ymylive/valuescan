#!/usr/bin/env python3
"""
Fix syntax error in VPS binance_trader/config.py
The config file has a corrupted line around line 74 with a stray comma.
"""
import subprocess
import os

VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "")

if not VPS_PASSWORD:
    print("Error: VALUESCAN_VPS_PASSWORD environment variable not set")
    exit(1)

# First, read the config file to see what's wrong
read_cmd = f"""
sshpass -p '{VPS_PASSWORD}' ssh -o StrictHostKeyChecking=no {VPS_USER}@{VPS_HOST} "cat /root/valuescan/binance_trader/config.py | head -100"
"""

print("Reading config file from VPS...")
result = subprocess.run(read_cmd, shell=True, capture_output=True, text=True)
print("=== Config file (first 100 lines) ===")
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

# Fix the config file - remove any stray commas and fix the SHORT_PYRAMIDING_EXIT_LEVELS block
fix_cmd = f"""
sshpass -p '{VPS_PASSWORD}' ssh -o StrictHostKeyChecking=no {VPS_USER}@{VPS_HOST} "python3 << 'PYEOF'
import re

config_path = '/root/valuescan/binance_trader/config.py'

with open(config_path, 'r') as f:
    content = f.read()

# Show lines around 74
lines = content.split('\\n')
print('Lines 70-80:')
for i, line in enumerate(lines[69:80], start=70):
    print(f'{{i}}: {{repr(line)}}')

# Find and fix the problematic pattern - stray comma on its own line
# This usually happens when the config generator creates malformed output
fixed_content = re.sub(r'^\\s*,\\s*$', '', content, flags=re.MULTILINE)

# Also fix any duplicate SHORT_PYRAMIDING_EXIT_LEVELS blocks
# Keep only the last one
pattern = r'SHORT_PYRAMIDING_EXIT_LEVELS\\s*=\\s*\\[[\\s\\S]*?\\]'
matches = list(re.finditer(pattern, fixed_content))
if len(matches) > 1:
    print(f'Found {{len(matches)}} SHORT_PYRAMIDING_EXIT_LEVELS blocks, keeping last one')
    # Remove all but the last match
    for match in reversed(matches[:-1]):
        fixed_content = fixed_content[:match.start()] + fixed_content[match.end():]

# Clean up multiple blank lines
fixed_content = re.sub(r'\\n{3,}', '\\n\\n', fixed_content)

with open(config_path, 'w') as f:
    f.write(fixed_content)

print('\\nConfig file fixed!')

# Verify syntax
import ast
try:
    ast.parse(fixed_content)
    print('Syntax check: OK')
except SyntaxError as e:
    print(f'Syntax check: FAILED - {{e}}')
PYEOF"
"""

print("\n\nFixing config file...")
result = subprocess.run(fix_cmd, shell=True, capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

# Restart the trader service
restart_cmd = f"""
sshpass -p '{VPS_PASSWORD}' ssh -o StrictHostKeyChecking=no {VPS_USER}@{VPS_HOST} "systemctl restart valuescan-trader && sleep 2 && systemctl status valuescan-trader"
"""

print("\n\nRestarting trader service...")
result = subprocess.run(restart_cmd, shell=True, capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

print("\nDone!")
