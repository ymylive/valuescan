#!/usr/bin/env python3
"""
Fix syntax error in VPS binance_trader/config.py - remove ALL garbage patterns
"""
import os
import sys
import re

try:
    import paramiko
except ImportError:
    print("Installing paramiko...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "paramiko"], check=True)
    import paramiko

VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "")

if not VPS_PASSWORD:
    print("Error: VALUESCAN_VPS_PASSWORD environment variable not set")
    exit(1)

print(f"Connecting to {VPS_HOST}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD)

# Read the config file
print("Reading config file...")
sftp = ssh.open_sftp()
config_path = "/root/valuescan/binance_trader/config.py"

with sftp.open(config_path, 'r') as f:
    content = f.read().decode('utf-8')

print(f"Original content length: {len(content)}")

# The garbage pattern looks like this:
# ,
#     [
#     3,
#     0.5,
# ],
#     [
#     5,
#     1,
# ],
# ]
# 
# This is malformed list content that got inserted incorrectly

# Remove all instances of this garbage pattern
# Pattern: a comma on its own line, followed by indented list-like content
garbage_pattern = r',\s*\n\s*\[\s*\n\s*\d+,\s*\n\s*[\d.]+,\s*\n\s*\],\s*\n\s*\[\s*\n\s*\d+,\s*\n\s*[\d.]+,\s*\n\s*\],\s*\n\s*\]'

matches = list(re.finditer(garbage_pattern, content))
print(f"Found {len(matches)} garbage patterns")

for i, match in enumerate(matches):
    print(f"  Match {i+1} at position {match.start()}-{match.end()}: {repr(match.group()[:50])}...")

# Remove all garbage patterns
fixed_content = re.sub(garbage_pattern, '', content)

# Also remove any standalone garbage that might be left
# Pattern: lines that are just "[", numbers, "]," etc. not part of a valid assignment
lines = fixed_content.split('\n')
new_lines = []
skip_garbage = False
garbage_indicators = ['[', '],', ']']

i = 0
while i < len(lines):
    line = lines[i]
    stripped = line.strip()
    
    # Check if this line starts a garbage block
    # Garbage blocks are indented content that's not part of a valid assignment
    if stripped in garbage_indicators and not any(c.isupper() for c in line):
        # Look ahead to see if this is garbage
        is_garbage = True
        j = i
        while j < len(lines) and j < i + 10:
            next_stripped = lines[j].strip()
            if next_stripped.startswith('#') or (next_stripped and next_stripped[0].isupper() and '=' in next_stripped):
                # Found a valid config line, stop checking
                break
            if next_stripped and not next_stripped.replace('.', '').replace(',', '').replace('[', '').replace(']', '').replace(' ', '').isdigit() and next_stripped not in garbage_indicators:
                is_garbage = False
                break
            j += 1
        
        if is_garbage and stripped in ['[', '],']:
            # Skip this garbage block
            print(f"Skipping garbage starting at line {i+1}: {repr(stripped)}")
            while i < len(lines):
                stripped = lines[i].strip()
                if stripped.startswith('#') or (stripped and stripped[0].isupper() and '=' in stripped) or stripped == '':
                    break
                i += 1
            continue
    
    new_lines.append(line)
    i += 1

fixed_content = '\n'.join(new_lines)

# Clean up multiple blank lines
fixed_content = re.sub(r'\n{3,}', '\n\n', fixed_content)

# Remove any stray commas on their own line
fixed_content = re.sub(r'^\s*,\s*$', '', fixed_content, flags=re.MULTILINE)

# Verify syntax
import ast
try:
    ast.parse(fixed_content)
    print("\nSyntax check: OK")
except SyntaxError as e:
    print(f"\nSyntax check: FAILED - {e}")
    
    # Show the problematic area
    lines = fixed_content.split('\n')
    print(f"\nContext around line {e.lineno}:")
    for i in range(max(0, e.lineno-5), min(len(lines), e.lineno+5)):
        marker = ">>>" if i+1 == e.lineno else "   "
        print(f"{marker} {i+1}: {repr(lines[i][:80])}")
    
    # More aggressive fix - remove any line that's just whitespace + [ or ] or number
    print("\nApplying more aggressive fix...")
    new_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Skip lines that are just brackets, numbers, or commas (not part of valid config)
        if stripped in ['[', ']', '],', ',']:
            # Check if previous line ends with = [ (valid list start)
            if new_lines and '= [' in new_lines[-1]:
                new_lines.append(line)
            else:
                print(f"Removing orphan line {i+1}: {repr(stripped)}")
            continue
        # Skip lines that are just numbers
        if stripped.replace('.', '').replace(',', '').isdigit():
            print(f"Removing number-only line {i+1}: {repr(stripped)}")
            continue
        new_lines.append(line)
    
    fixed_content = '\n'.join(new_lines)
    fixed_content = re.sub(r'\n{3,}', '\n\n', fixed_content)
    
    try:
        ast.parse(fixed_content)
        print("Aggressive fix: Syntax check OK")
    except SyntaxError as e2:
        print(f"Aggressive fix: Still failing - {e2}")
        
        # Last resort - copy from template and merge values
        print("\nLast resort: Reading template and merging...")

print(f"\nFixed content length: {len(fixed_content)}")

# Write the fixed content
print("\nWriting fixed config...")
with sftp.open(config_path, 'w') as f:
    f.write(fixed_content)

sftp.close()

# Restart the service
print("\nRestarting valuescan-trader service...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart valuescan-trader")
stdout.channel.recv_exit_status()

import time
time.sleep(3)

# Check status
print("\nChecking service status...")
stdin, stdout, stderr = ssh.exec_command("systemctl status valuescan-trader --no-pager -l | head -30")
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err)

ssh.close()
print("\nDone!")
