#!/usr/bin/env python3
"""Setup swap and test browser login on VPS"""
import os
import paramiko

def main():
    password = os.environ.get('VALUESCAN_VPS_PASSWORD')
    if not password:
        print("Missing VALUESCAN_VPS_PASSWORD env var")
        return
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('82.158.88.34', username='root', password=password, timeout=30)
    
    # Check current swap and swappiness
    print("=== Current swap status ===")
    stdin, stdout, stderr = ssh.exec_command('free -h; echo "---"; cat /proc/sys/vm/swappiness')
    print(stdout.read().decode())
    
    # Increase swappiness to use swap more aggressively
    print("=== Setting swappiness to 60 ===")
    stdin, stdout, stderr = ssh.exec_command('sysctl vm.swappiness=60; echo "vm.swappiness = 60" >> /etc/sysctl.conf 2>/dev/null || true')
    print(stdout.read().decode())
    
    # Check if swap file exists, if not create one
    print("=== Checking swap ===")
    stdin, stdout, stderr = ssh.exec_command('swapon --show')
    swap_output = stdout.read().decode()
    print(swap_output)
    
    if not swap_output.strip():
        print("No swap found, creating 4GB swap file...")
        commands = [
            "fallocate -l 4G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=4096",
            "chmod 600 /swapfile",
            "mkswap /swapfile",
            "swapon /swapfile",
            "echo '/swapfile none swap sw 0 0' >> /etc/fstab",
        ]
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
            print(f"$ {cmd}")
            print(stdout.read().decode())
            err = stderr.read().decode()
            if err:
                print(f"STDERR: {err}")
    
    # Final check
    print("=== Final swap status ===")
    stdin, stdout, stderr = ssh.exec_command('free -h')
    print(stdout.read().decode())
    
    ssh.close()

if __name__ == "__main__":
    main()
