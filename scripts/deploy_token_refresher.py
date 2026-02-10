#!/usr/bin/env python3
"""
Deploy the Chromium-based token refresher to the VPS using env credentials.

Required env:
  VALUESCAN_VPS_PASSWORD      SSH password (host/user can also be overridden)
  VALUESCAN_EMAIL             ValueScan login email
  VALUESCAN_PASSWORD          ValueScan login password

Optional env:
  VALUESCAN_VPS_HOST (default: 82.158.88.34)
  VALUESCAN_VPS_USER (default: root)
"""

from __future__ import annotations

import os
import subprocess
import sys
import json
from typing import Any


def _require_env(key: str) -> str:
    val = (os.environ.get(key) or "").strip()
    if not val:
        print(f"Error: environment variable {key} is required.")
        sys.exit(1)
    return val


def _get_paramiko():
    try:
        import paramiko  # type: ignore
        return paramiko
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "paramiko"], check=True)
        import paramiko  # type: ignore
        return paramiko


def _exec(ssh, cmd: str, desc: str) -> None:
    print(f"\n[{desc}] {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=180)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out.strip())
    if err:
        print(f"STDERR: {err.strip()}")
    if exit_code != 0:
        print(f"Warning: command exited with {exit_code}")


def main() -> int:
    paramiko = _get_paramiko()

    host = os.environ.get("VALUESCAN_VPS_HOST", "82.158.88.34")
    user = os.environ.get("VALUESCAN_VPS_USER", "root")
    password = _require_env("VALUESCAN_VPS_PASSWORD")

    email = _require_env("VALUESCAN_EMAIL")
    login_password = _require_env("VALUESCAN_PASSWORD")

    print(f"Connecting to {user}@{host} ...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password, timeout=30)
    sftp = ssh.open_sftp()

    files_to_upload = [
        ("token_refresher.py", "/root/valuescan/token_refresher.py"),
        ("signal_monitor/token_refresher.py", "/root/valuescan/signal_monitor/token_refresher.py"),
        ("signal_monitor/cdp_token_refresher.py", "/root/valuescan/signal_monitor/cdp_token_refresher.py"),
        ("signal_monitor/start_with_chrome.py", "/root/valuescan/signal_monitor/start_with_chrome.py"),
        ("valuescan-token-refresher.service", "/etc/systemd/system/valuescan-token-refresher.service"),
        ("api/server.py", "/root/valuescan/api/server.py"),
    ]
    for local_file, remote_file in files_to_upload:
        if not os.path.exists(local_file):
            print(f"Skip missing file: {local_file}")
            continue
        print(f"Uploading {local_file} -> {remote_file}")
        sftp.put(local_file, remote_file)

    cred_path = "/root/valuescan/signal_monitor/valuescan_credentials.json"
    cred_payload = json.dumps({"email": email, "password": login_password})
    print(f"Writing credentials to {cred_path} (chmod 600)")
    with sftp.open(cred_path, "w") as f:
        f.write(cred_payload)
    sftp.chmod(cred_path, 0o600)
    sftp.close()
    _exec(ssh, "pip3.9 install DrissionPage --quiet", "Ensure DrissionPage")
    _exec(ssh, "systemctl daemon-reload", "Reload systemd")
    _exec(ssh, "systemctl enable valuescan-token-refresher", "Enable token refresher")
    _exec(ssh, "systemctl restart valuescan-api", "Restart API")
    _exec(ssh, "systemctl status valuescan-api --no-pager -l | head -15", "API status")

    ssh.close()
    print("\nDone. Start/Restart refresher as needed: systemctl restart valuescan-token-refresher")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
