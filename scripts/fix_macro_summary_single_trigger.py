#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix duplicate macro summary sends by disabling the legacy scheduler service.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

DEFAULT_HOST = "82.158.88.34"
DEFAULT_USER = "root"
DEFAULT_PORT = 22
VALUESCAN_DIR = "/root/valuescan"
SYSTEMD_DIR = "/etc/systemd/system"


def _exec(ssh: paramiko.SSHClient, cmd: str, timeout: int = 120) -> str:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")
    combined = (out + ("\n" + err if err else "")).strip()
    if not combined:
        return ""
    try:
        combined.encode(sys.stdout.encoding or "utf-8")
        return combined
    except Exception:
        return combined.encode("ascii", errors="ignore").decode("ascii")


def main() -> None:
    host = os.environ.get("VALUESCAN_VPS_HOST", DEFAULT_HOST)
    user = os.environ.get("VALUESCAN_VPS_USER", DEFAULT_USER)
    port = int(os.environ.get("VALUESCAN_VPS_PORT", str(DEFAULT_PORT)))
    password = os.environ.get("VALUESCAN_VPS_PASSWORD", "")
    if not password:
        print("[ERROR] VALUESCAN_VPS_PASSWORD is required.")
        sys.exit(1)

    local_service = Path("valuescan-signal.service")
    if not local_service.exists():
        print("[ERROR] valuescan-signal.service not found in repo.")
        sys.exit(1)

    print(f"Connecting to {user}@{host}:{port} ...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=host, port=port, username=user, password=password, timeout=30)
    sftp = ssh.open_sftp()

    remote_service = f"{SYSTEMD_DIR}/valuescan-signal.service"
    tmp_service = f"{SYSTEMD_DIR}/valuescan-signal.service.tmp"
    sftp.put(str(local_service), tmp_service)
    sftp.close()

    print("Updating systemd unit...")
    print(_exec(ssh, f"mv {tmp_service} {remote_service}"))
    print(_exec(ssh, "systemctl daemon-reload"))

    print("Disabling legacy valuescan-signal service...")
    print(_exec(ssh, "systemctl disable --now valuescan-signal || true"))

    print("Ensuring valuescan-monitor is enabled and running...")
    print(_exec(ssh, "systemctl enable --now valuescan-monitor"))

    print("Service status:")
    print(_exec(ssh, "systemctl status valuescan-monitor valuescan-signal --no-pager | head -40"))

    ssh.close()
    print("Done.")


if __name__ == "__main__":
    main()
