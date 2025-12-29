#!/usr/bin/env python3
"""
Fix syntax error in VPS binance_trader/config.py using paramiko
"""
import os
import sys

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

lines = content.split('\n')
print(f"Total lines: {len(lines)}")
print("\n=== Lines 70-85 ===")
for i, line in enumerate(lines[69:85], start=70):
    print(f"{i}: {repr(line)}")

# Fix the content
import re

# Remove stray commas on their own line
fixed_content = re.sub(r'^\s*,\s*$', '', content, flags=re.MULTILINE)

# Fix duplicate SHORT_PYRAMIDING_EXIT_LEVELS blocks
pattern = r'SHORT_PYRAMIDING_EXIT_LEVELS\s*=\s*\[[\s\S]*?\]'
matches = list(re.finditer(pattern, fixed_content))
if len(matches) > 1:
    print(f"\nFound {len(matches)} SHORT_PYRAMIDING_EXIT_LEVELS blocks, keeping last one")
    for match in reversed(matches[:-1]):
        fixed_content = fixed_content[:match.start()] + fixed_content[match.end():]

# Fix duplicate PYRAMIDING_EXIT_LEVELS blocks (non-short)
pattern = r'(?<!SHORT_)PYRAMIDING_EXIT_LEVELS\s*=\s*\[[\s\S]*?\]'
matches = list(re.finditer(pattern, fixed_content))
if len(matches) > 1:
    print(f"Found {len(matches)} PYRAMIDING_EXIT_LEVELS blocks, keeping last one")
    for match in reversed(matches[:-1]):
        fixed_content = fixed_content[:match.start()] + fixed_content[match.end():]

# Clean up multiple blank lines
fixed_content = re.sub(r'\n{3,}', '\n\n', fixed_content)

# Verify syntax before writing
import ast
try:
    ast.parse(fixed_content)
    print("\nSyntax check: OK")
except SyntaxError as e:
    print(f"\nSyntax check: FAILED - {e}")
    print("Attempting more aggressive fix...")
    
    # More aggressive fix - rebuild the config from scratch
    # Find all the key=value pairs and rebuild
    lines = fixed_content.split('\n')
    new_lines = []
    skip_until_bracket = False
    bracket_count = 0
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip empty lines at the start
        if not new_lines and not stripped:
            continue
            
        # Skip stray commas
        if stripped == ',':
            continue
            
        # Track brackets for multi-line values
        if skip_until_bracket:
            bracket_count += line.count('[') - line.count(']')
            new_lines.append(line)
            if bracket_count <= 0:
                skip_until_bracket = False
            continue
        
        # Check if this starts a multi-line list
        if '= [' in line and ']' not in line:
            skip_until_bracket = True
            bracket_count = line.count('[') - line.count(']')
        
        new_lines.append(line)
    
    fixed_content = '\n'.join(new_lines)
    
    try:
        ast.parse(fixed_content)
        print("Aggressive fix: Syntax check OK")
    except SyntaxError as e:
        print(f"Aggressive fix: Still failing - {e}")
        print("\nShowing problematic area:")
        lines = fixed_content.split('\n')
        for i, line in enumerate(lines[max(0, e.lineno-5):e.lineno+5], start=max(1, e.lineno-4)):
            marker = ">>>" if i == e.lineno else "   "
            print(f"{marker} {i}: {repr(line)}")

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
