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
from pathlib import Path
from typing import Any, Dict, Optional


def _require_env(key: str) -> str:
    val = (os.environ.get(key) or "").strip()
    if not val:
        print(f"Error: environment variable {key} is required.")
        sys.exit(1)
    return val


def _load_local_credentials() -> Optional[Dict[str, str]]:
    path = Path("signal_monitor") / "valuescan_credentials.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    email = str(payload.get("email") or "").strip()
    password = str(payload.get("password") or "").strip()
    if email and password:
        return {"email": email, "password": password}
    return None


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

    email = (os.environ.get("VALUESCAN_EMAIL") or "").strip()
    login_password = (os.environ.get("VALUESCAN_PASSWORD") or "").strip()
    if not email or not login_password:
        creds = _load_local_credentials()
        if creds:
            email = creds["email"]
            login_password = creds["password"]
    if not email or not login_password:
        print("Error: VALUESCAN_EMAIL/VALUESCAN_PASSWORD missing and no local credentials found.")
        sys.exit(1)

    print(f"Connecting to {user}@{host} ...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password, timeout=30)
    sftp = ssh.open_sftp()

    files_to_upload = [
        ("token_refresher.py", "/root/valuescan/token_refresher.py"),
        ("token_refresher_http.py", "/root/valuescan/token_refresher_http.py"),
        ("signal_monitor/http_api_login.py", "/root/valuescan/signal_monitor/http_api_login.py"),
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
    _exec(ssh, "pip3.9 install pycryptodome --quiet", "Ensure crypto deps")
    _exec(ssh, "systemctl daemon-reload", "Reload systemd")
    _exec(ssh, "systemctl enable valuescan-token-refresher", "Enable token refresher")
    _exec(ssh, "systemctl restart valuescan-token-refresher", "Restart token refresher")
    _exec(
        ssh,
        "systemctl status valuescan-token-refresher --no-pager -l | head -15",
        "Token refresher status",
    )
    _exec(ssh, "systemctl restart valuescan-api", "Restart API")
    _exec(ssh, "systemctl status valuescan-api --no-pager -l | head -15", "API status")

    ssh.close()
    print("\nDone. Start/Restart refresher as needed: systemctl restart valuescan-token-refresher")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
