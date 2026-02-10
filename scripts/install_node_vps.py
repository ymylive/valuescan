#!/usr/bin/env python3
"""
Install Node.js/npm on the VPS if missing.
Uses paramiko with password or key from environment variables.
"""
from __future__ import annotations

import os
import sys


def _ascii(text: str) -> str:
    return (text or "").encode("ascii", errors="ignore").decode("ascii")


def _connect(host: str, user: str, password: str | None, key_file: str | None):
    try:
        import paramiko
    except ImportError as exc:
        raise RuntimeError("paramiko is required. Install with: pip install paramiko") from exc
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs = {
        "hostname": host,
        "username": user,
        "timeout": 30,
        "banner_timeout": 30,
        "auth_timeout": 30,
        "look_for_keys": False,
        "allow_agent": False,
    }
    if password:
        connect_kwargs["password"] = password
    elif key_file:
        connect_kwargs["key_filename"] = key_file
    else:
        raise RuntimeError("Missing password or key file")
    ssh.connect(**connect_kwargs)
    return ssh


def _run(ssh, command: str, timeout: int = 1200) -> int:
    stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
    exit_status = stdout.channel.recv_exit_status()
    out = _ascii(stdout.read().decode("utf-8", errors="ignore"))
    err = _ascii(stderr.read().decode("utf-8", errors="ignore"))
    if out:
        print(out)
    if err:
        print(err, file=sys.stderr)
    return exit_status


def main() -> int:
    host = os.getenv("VALUESCAN_VPS_HOST", "").strip()
    user = os.getenv("VALUESCAN_VPS_USER", "root").strip() or "root"
    password = os.getenv("VALUESCAN_VPS_PASSWORD", "").strip() or None
    key_file = os.getenv("VALUESCAN_VPS_KEY_FILE", "").strip() or None
    if not host:
        print("Missing VALUESCAN_VPS_HOST")
        return 1

    ssh = None
    try:
        print(f"Connecting to {user}@{host}...")
        ssh = _connect(host, user, password, key_file)
        if _run(ssh, "command -v npm >/dev/null 2>&1") == 0:
            print("npm already installed.")
            return 0
        print("Installing Node.js (NodeSource 18.x)...")
        _run(ssh, "apt-get update -y", timeout=1200)
        _run(ssh, "apt-get install -y curl ca-certificates", timeout=1200)
        _run(ssh, "curl -fsSL https://deb.nodesource.com/setup_18.x | bash -", timeout=1200)
        exit_code = _run(ssh, "apt-get install -y nodejs", timeout=1200)
        if exit_code != 0:
            print("Node.js install failed.", file=sys.stderr)
            return exit_code
        _run(ssh, "node -v && npm -v")
        print("Node.js install completed.")
        return 0
    except Exception as exc:
        print(f"Install failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if ssh:
            ssh.close()


if __name__ == "__main__":
    sys.exit(main())
