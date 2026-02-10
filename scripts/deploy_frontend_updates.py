#!/usr/bin/env python3
"""
Deploy frontend UI updates to VPS and rebuild the web bundle.

Required env:
  VPS_HOST, VPS_USER, VPS_PASSWORD
Optional env:
  VPS_PORT (default: 22)
  VPS_REMOTE_ROOT (default: /root/valuescan)
"""

from __future__ import annotations

import os
import posixpath
from pathlib import Path
from typing import Iterable

import paramiko


FILES = [
    "web/src/components/Config/AIServiceConfig.tsx",
    "web/src/components/Config/SignalMonitorConfig.tsx",
    "web/src/types/config.ts",
]


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required env: {name}")
    return value


def _ensure_remote_dir(sftp: paramiko.SFTPClient, remote_dir: str) -> None:
    parts = []
    while remote_dir not in ("/", ""):
        parts.append(remote_dir)
        remote_dir = posixpath.dirname(remote_dir)
    for folder in reversed(parts):
        try:
            sftp.stat(folder)
        except IOError:
            sftp.mkdir(folder)


def _upload_file(sftp: paramiko.SFTPClient, local_path: Path, remote_path: str) -> None:
    remote_dir = posixpath.dirname(remote_path)
    _ensure_remote_dir(sftp, remote_dir)
    tmp_path = remote_path + ".tmp"
    sftp.put(str(local_path), tmp_path)
    try:
        sftp.rename(tmp_path, remote_path)
    except IOError:
        sftp.remove(remote_path)
        sftp.rename(tmp_path, remote_path)


def _run_cmd(client: paramiko.SSHClient, command: str) -> None:
    stdin, stdout, stderr = client.exec_command(command)
    out = stdout.read().decode("utf-8", "ignore").strip()
    err = stderr.read().decode("utf-8", "ignore").strip()
    exit_code = stdout.channel.recv_exit_status()
    if exit_code != 0:
        detail = err or out or f"exit_code={exit_code}"
        raise SystemExit(f"Command failed: {command}\n{detail}")


def main() -> None:
    host = _require_env("VPS_HOST")
    user = _require_env("VPS_USER")
    password = _require_env("VPS_PASSWORD")
    port = int(os.getenv("VPS_PORT", "22"))
    remote_root = os.getenv("VPS_REMOTE_ROOT", "/root/valuescan").strip() or "/root/valuescan"

    local_root = Path(__file__).resolve().parents[1]
    missing = [path for path in FILES if not (local_root / path).exists()]
    if missing:
        raise SystemExit(f"Missing local files: {', '.join(missing)}")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, password=password, port=port, timeout=20)

    try:
        sftp = client.open_sftp()
        for rel_path in FILES:
            local_path = local_root / rel_path
            remote_path = posixpath.join(remote_root, rel_path.replace("\\", "/"))
            _upload_file(sftp, local_path, remote_path)
        sftp.close()

        _run_cmd(client, f"cd {remote_root}/web && npm run build")
    finally:
        client.close()


if __name__ == "__main__":
    main()
