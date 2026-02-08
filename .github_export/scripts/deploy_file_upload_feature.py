#!/usr/bin/env python3
"""Deploy file upload feature to VPS."""
import os
import paramiko

HOST = "82.158.88.34"
USER = "root"
PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "Qq159741")
NOFX_DIR = "/opt/nofx"
LOCAL_NOFX = os.path.join(os.path.dirname(__file__), "..", "nofx")

def run_ssh(ssh, cmd, desc, timeout=300):
    print(f"\n[{desc}] {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")
    if out: print(out[-2000:])
    if err: print(f"STDERR: {err[-1000:]}")
    return exit_code == 0

def main():
    print(f"Connecting to {USER}@{HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    print("Connected!")

    sftp = ssh.open_sftp()
    
    # Files to upload for file upload feature
    files_to_upload = [
        ("store/ai_model.go", f"{NOFX_DIR}/store/ai_model.go"),
        ("api/server.go", f"{NOFX_DIR}/api/server.go"),
        ("mcp/interface.go", f"{NOFX_DIR}/mcp/interface.go"),
        ("mcp/client.go", f"{NOFX_DIR}/mcp/client.go"),
        ("mcp/config.go", f"{NOFX_DIR}/mcp/config.go"),
        ("mcp/file_upload.go", f"{NOFX_DIR}/mcp/file_upload.go"),
        ("trader/auto_trader.go", f"{NOFX_DIR}/trader/auto_trader.go"),
        ("manager/trader_manager.go", f"{NOFX_DIR}/manager/trader_manager.go"),
        ("decision/engine.go", f"{NOFX_DIR}/decision/engine.go"),
    ]
    
    for local_rel, remote_path in files_to_upload:
        local_path = os.path.join(LOCAL_NOFX, local_rel)
        if os.path.exists(local_path):
            print(f"Uploading {local_rel} -> {remote_path}")
            sftp.put(local_path, remote_path)
        else:
            print(f"⚠️ File not found: {local_path}")
    
    print("\nAll files uploaded!")
    sftp.close()

    # Rebuild and restart - NOTE: service uses nofx-server binary!
    commands = [
        (f"cd {NOFX_DIR} && /usr/local/go/bin/go build -o nofx-server .", "Build NOFX"),
        ("systemctl restart nofx", "Restart NOFX service"),
        ("systemctl status nofx --no-pager", "Check status"),
    ]
    
    for cmd, desc in commands:
        run_ssh(ssh, cmd, desc)
    
    ssh.close()
    print("\n✅ File upload feature deployment complete!")

if __name__ == "__main__":
    main()
