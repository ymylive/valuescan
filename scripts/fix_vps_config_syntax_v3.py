#!/usr/bin/env python3
"""
Fix syntax error in VPS binance_trader/config.py - complete rebuild of corrupted section
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

# Find the corrupted section and fix it
# The problem is around line 73-83 where there's garbage data
# We need to:
# 1. Find SHORT_PYRAMIDING_EXIT_LEVELS = [ and its closing ]
# 2. Remove any garbage after it until the next valid config line

import re

# First, let's find all the config blocks
print("\nAnalyzing config structure...")

# Find the SHORT_PYRAMIDING_EXIT_LEVELS block
short_pyr_match = re.search(r'SHORT_PYRAMIDING_EXIT_LEVELS\s*=\s*\[', content)
if short_pyr_match:
    start = short_pyr_match.start()
    # Find the matching closing bracket
    bracket_count = 0
    end = start
    in_block = False
    for i, char in enumerate(content[start:], start=start):
        if char == '[':
            bracket_count += 1
            in_block = True
        elif char == ']':
            bracket_count -= 1
            if in_block and bracket_count == 0:
                end = i + 1
                break
    
    block = content[start:end]
    print(f"Found SHORT_PYRAMIDING_EXIT_LEVELS block at {start}-{end}:")
    print(repr(block[:200]))
    
    # Check what comes after
    after_block = content[end:end+200]
    print(f"\nAfter block: {repr(after_block[:100])}")

# The fix: Remove everything from after the first ] of SHORT_PYRAMIDING_EXIT_LEVELS
# until we hit a valid config line (starts with a capital letter and has =)

# Split into lines and rebuild
new_lines = []
skip_mode = False
found_short_pyr = False
bracket_depth = 0

for i, line in enumerate(lines):
    stripped = line.strip()
    
    # Track if we're in SHORT_PYRAMIDING_EXIT_LEVELS
    if 'SHORT_PYRAMIDING_EXIT_LEVELS' in line and '=' in line:
        found_short_pyr = True
        bracket_depth = line.count('[') - line.count(']')
        new_lines.append(line)
        if bracket_depth == 0:
            skip_mode = True  # Start skipping garbage after this
        continue
    
    if found_short_pyr and bracket_depth > 0:
        # We're inside the SHORT_PYRAMIDING_EXIT_LEVELS list
        bracket_depth += line.count('[') - line.count(']')
        new_lines.append(line)
        if bracket_depth <= 0:
            skip_mode = True  # Start skipping garbage after the list closes
            found_short_pyr = False
        continue
    
    if skip_mode:
        # Skip garbage lines until we hit a valid config line
        # Valid config lines start with a capital letter or # comment
        if stripped.startswith('#') or (stripped and stripped[0].isupper() and '=' in stripped):
            skip_mode = False
            new_lines.append(line)
        elif stripped == '':
            # Keep empty lines
            pass
        else:
            print(f"Skipping garbage line {i+1}: {repr(stripped[:50])}")
        continue
    
    new_lines.append(line)

fixed_content = '\n'.join(new_lines)

# Verify syntax
import ast
try:
    ast.parse(fixed_content)
    print("\nSyntax check: OK")
except SyntaxError as e:
    print(f"\nSyntax check: FAILED - {e}")
    print(f"Line {e.lineno}: {repr(new_lines[e.lineno-1] if e.lineno <= len(new_lines) else 'N/A')}")
    
    # Show context
    print("\nContext around error:")
    for i in range(max(0, e.lineno-5), min(len(new_lines), e.lineno+5)):
        marker = ">>>" if i+1 == e.lineno else "   "
        print(f"{marker} {i+1}: {repr(new_lines[i][:80])}")
    
    # Last resort: manually fix the specific issue
    print("\nAttempting manual fix...")
    
    # The issue is likely stray content after SHORT_PYRAMIDING_EXIT_LEVELS
    # Let's find and remove it more aggressively
    
    # Find the line with SHORT_PYRAMIDING_EXIT_LEVELS
    for i, line in enumerate(new_lines):
        if 'SHORT_PYRAMIDING_EXIT_LEVELS' in line:
            print(f"Found at line {i+1}: {repr(line)}")
            # Find the closing bracket
            j = i
            depth = line.count('[') - line.count(']')
            while depth > 0 and j < len(new_lines) - 1:
                j += 1
                depth += new_lines[j].count('[') - new_lines[j].count(']')
            print(f"Block ends at line {j+1}: {repr(new_lines[j])}")
            
            # Remove any garbage between this and the next valid config
            k = j + 1
            while k < len(new_lines):
                stripped = new_lines[k].strip()
                if stripped == '' or stripped.startswith('#') or (stripped and stripped[0].isupper() and '=' in stripped):
                    break
                print(f"Removing garbage line {k+1}: {repr(stripped[:50])}")
                new_lines[k] = ''
                k += 1
            break
    
    fixed_content = '\n'.join(line for line in new_lines if line is not None)
    fixed_content = re.sub(r'\n{3,}', '\n\n', fixed_content)
    
    try:
        ast.parse(fixed_content)
        print("Manual fix: Syntax check OK")
    except SyntaxError as e2:
        print(f"Manual fix: Still failing - {e2}")

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
