#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Remove legacy valuescan-signal systemd service from VPS.
"""
from __future__ import annotations

import os
import sys

import paramiko

DEFAULT_HOST = "82.158.88.34"
DEFAULT_USER = "root"
DEFAULT_PORT = 22
SYSTEMD_SERVICE = "valuescan-signal.service"


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

    print(f"Connecting to {user}@{host}:{port} ...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=host, port=port, username=user, password=password, timeout=30)

    print("Stopping/disabling legacy service...")
    print(_exec(ssh, f"systemctl disable --now {SYSTEMD_SERVICE} || true"))

    print("Removing systemd unit and drop-ins...")
    print(_exec(ssh, f"rm -f /etc/systemd/system/{SYSTEMD_SERVICE}"))
    print(_exec(ssh, "rm -rf /etc/systemd/system/valuescan-signal.service.d"))
    print(_exec(ssh, "systemctl daemon-reload"))

    print("Verifying status...")
    print(_exec(ssh, "systemctl status valuescan-monitor --no-pager | head -20"))
    print(_exec(ssh, "systemctl status valuescan-signal --no-pager | head -20"))

    ssh.close()
    print("Done.")


if __name__ == "__main__":
    main()
