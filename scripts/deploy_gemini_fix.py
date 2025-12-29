#!/usr/bin/env python3
"""Deploy Gemini fix to VPS using paramiko."""
import os
import paramiko

HOST = "82.158.88.34"
USER = "root"
PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "Qq159741")
NOFX_DIR = "/opt/nofx"

def run_ssh(ssh, cmd, desc, timeout=300):
    print(f"\n[{desc}] {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")
    if out: print(out)
    if err: print(f"STDERR: {err}")
    return exit_code == 0

def main():
    print(f"Connecting to {USER}@{HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    print("Connected!")

    sftp = ssh.open_sftp()
    
    # Upload the fixed engine.go file
    local_file = os.path.join(os.path.dirname(__file__), "..", "nofx", "decision", "engine.go")
    remote_file = f"{NOFX_DIR}/decision/engine.go"
    print(f"\nUploading {local_file} -> {remote_file}")
    sftp.put(local_file, remote_file)
    print("Upload complete!")
    
    sftp.close()

    # Rebuild and restart
    commands = [
        (f"cd {NOFX_DIR} && /usr/local/go/bin/go build -o nofx .", "Build NOFX"),
        ("systemctl restart nofx", "Restart NOFX service"),
        ("systemctl status nofx --no-pager", "Check status"),
    ]
    
    for cmd, desc in commands:
        run_ssh(ssh, cmd, desc)
    
    ssh.close()
    print("\n✅ Deployment complete!")

if __name__ == "__main__":
    main()
