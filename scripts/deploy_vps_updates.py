#!/usr/bin/env python3
"""
Deploy selected files to VPS using SFTP and restart services.

Required env:
  VPS_HOST, VPS_USER, VPS_PASSWORD
Optional env:
  VPS_PORT (default: 22)
  VPS_REMOTE_ROOT (default: /root/valuescan)
  VPS_RESTART_SERVICES (default: valuescan-signal.service,valuescan-monitor.service)
"""

from __future__ import annotations

import os
import posixpath
from pathlib import Path
from typing import Iterable

import paramiko


FILES = [
    "sitecustomize.py",
    "signal_monitor/sitecustomize.py",
    "api/sitecustomize.py",
    "signal_monitor/valuescan_api.py",
    "signal_monitor/chart_pro_v10.py",
    "signal_monitor/ai_signal_analysis.py",
    "signal_monitor/ai_market_analysis.py",
    "signal_monitor/ai_market_summary.py",
    "signal_monitor/macro_data.py",
    "signal_monitor/ai_signal_scheduler.py",
    "signal_monitor/telegram.py",
    "signal_monitor/data_cleaner.py",
    "signal_monitor/ai_key_levels_config.py",
    "signal_monitor/ai_key_levels_config.json",
    "signal_monitor/ai_signal_config.json",
    "signal_monitor/ai_overlays_config.json",
    "signal_monitor/ai_summary_config.json",
    "signal_monitor/ai_market_summary_config.json",
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


def _restart_services(client: paramiko.SSHClient, services: Iterable[str]) -> None:
    for service in services:
        cmd = f"systemctl restart {service}"
        client.exec_command(cmd)


def main() -> None:
    host = _require_env("VPS_HOST")
    user = _require_env("VPS_USER")
    password = _require_env("VPS_PASSWORD")
    port = int(os.getenv("VPS_PORT", "22"))
    remote_root = os.getenv("VPS_REMOTE_ROOT", "/root/valuescan").strip() or "/root/valuescan"
    services = os.getenv(
        "VPS_RESTART_SERVICES",
        "valuescan-signal.service,valuescan-monitor.service",
    )
    service_list = [s.strip() for s in services.split(",") if s.strip()]

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

        if service_list:
            _restart_services(client, service_list)
    finally:
        client.close()


if __name__ == "__main__":
    main()
