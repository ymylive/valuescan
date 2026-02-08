#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Upload frontend source changes to VPS, rebuild, and sync to Nginx.
"""
import os
import sys
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("Error: paramiko is not installed")
    print("Run: pip install paramiko")
    sys.exit(1)

VPS_HOST = os.environ.get("VALUESCAN_VPS_HOST", "82.158.88.34")
VPS_USER = os.environ.get("VALUESCAN_VPS_USER", "root")
VPS_PORT = int(os.environ.get("VALUESCAN_VPS_PORT", "22"))
VPS_PATH = os.environ.get("VALUESCAN_VPS_PATH", "/root/valuescan")
VPS_PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "")

LOCAL_FILE = Path("web/src/pages/ProxyPage.tsx")
REMOTE_FILE = f"{VPS_PATH}/web/src/pages/ProxyPage.tsx"


def _safe_print(text, stream):
    encoding = getattr(stream, "encoding", None) or "utf-8"
    stream.write(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))
    if not text.endswith("\n"):
        stream.write("\n")


def run_ssh_command(ssh, command, desc):
    print(f"\n[{desc}] {command}")
    stdin, stdout, stderr = ssh.exec_command(command, timeout=300)
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")
    if out:
        _safe_print(out, sys.stdout)
    if err:
        _safe_print(err, sys.stderr)
    return exit_status == 0


def main():
    if not VPS_PASSWORD:
        print("Error: VALUESCAN_VPS_PASSWORD is not set")
        sys.exit(1)

    if not LOCAL_FILE.exists():
        print(f"Error: local file not found: {LOCAL_FILE}")
        sys.exit(1)

    print("=" * 60)
    print("Deploy frontend source to VPS")
    print("=" * 60)
    print(f"VPS: {VPS_USER}@{VPS_HOST}:{VPS_PORT}")
    print(f"Path: {VPS_PATH}")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(
            hostname=VPS_HOST,
            port=VPS_PORT,
            username=VPS_USER,
            password=VPS_PASSWORD,
            timeout=30,
        )
    except Exception as exc:
        print(f"Connection failed: {exc}")
        sys.exit(1)

    sftp = ssh.open_sftp()
    remote_dir = str(Path(REMOTE_FILE).parent).replace("\\", "/")
    try:
        sftp.stat(remote_dir)
    except IOError:
        run_ssh_command(ssh, f"mkdir -p {remote_dir}", "Create remote directory")

    print(f"\nUpload: {LOCAL_FILE} -> {REMOTE_FILE}")
    sftp.put(str(LOCAL_FILE), REMOTE_FILE)
    sftp.close()

    steps = [
        (f"cd {VPS_PATH}/web && npm install", "Install frontend deps"),
        (f"cd {VPS_PATH}/web && npm run build", "Build frontend"),
        (f"mkdir -p /var/www/valuescan && cp -r {VPS_PATH}/web/dist/* /var/www/valuescan/", "Sync to Nginx dir"),
        ("systemctl restart nginx", "Restart Nginx"),
    ]

    for cmd, desc in steps:
        if not run_ssh_command(ssh, cmd, desc):
            print(f"Step failed: {desc}")
            ssh.close()
            sys.exit(1)

    ssh.close()
    print("\nDone. Please hard-refresh the page.")


if __name__ == "__main__":
    main()
