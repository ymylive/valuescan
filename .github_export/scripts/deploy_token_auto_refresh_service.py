#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy ValueScan token auto refresh systemd service to VPS.
"""
from __future__ import annotations

import getpass
import os
import socket
import sys
from pathlib import Path
from typing import Optional

import paramiko
from paramiko.ssh_exception import AuthenticationException, BadAuthenticationType


DEFAULT_HOST = "82.158.88.34"
DEFAULT_USER = "root"
DEFAULT_SERVICE_NAME = "valuescan-token-auto-refresh.service"


def _get_password() -> Optional[str]:
    password = (os.environ.get("VALUESCAN_VPS_PASSWORD") or "").strip()
    if password:
        return password
    print("VALUESCAN_VPS_PASSWORD not set.")
    return None


def _prompt_password(host: str, user: str) -> Optional[str]:
    if not sys.stdin.isatty():
        return None
    try:
        pw = getpass.getpass(f"Enter SSH password for {user}@{host}: ")
    except Exception:
        return None
    return (pw or "").strip() or None


def _connect_ssh(ssh: paramiko.SSHClient, connect_kwargs: dict, host: str, user: str) -> None:
    try:
        ssh.connect(**connect_kwargs)
        return
    except BadAuthenticationType as exc:
        allowed = getattr(exc, "allowed_types", None) or []
        if "password" in allowed and not connect_kwargs.get("password"):
            pw = _prompt_password(host, user)
            if pw:
                connect_kwargs["password"] = pw
                ssh.connect(**connect_kwargs)
                return
        raise
    except AuthenticationException:
        if not connect_kwargs.get("password"):
            pw = _prompt_password(host, user)
            if pw:
                connect_kwargs["password"] = pw
                ssh.connect(**connect_kwargs)
                return
        raise


def _exec(ssh: paramiko.SSHClient, cmd: str, timeout: int = 120) -> str:
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="ignore")
        err = stderr.read().decode("utf-8", errors="ignore")
        return (out + ("\n" + err if err else "")).strip()
    except (socket.timeout, TimeoutError):
        return f"[timeout after {timeout}s] {cmd}"
    except Exception as exc:
        return f"[exec error] {cmd}: {exc}"


def main() -> None:
    host = os.environ.get("VALUESCAN_VPS_HOST", DEFAULT_HOST)
    user = os.environ.get("VALUESCAN_VPS_USER", DEFAULT_USER)
    service_name = os.environ.get("VALUESCAN_VPS_SERVICE", DEFAULT_SERVICE_NAME)
    password = _get_password()

    service_path = Path(service_name)
    if not service_path.exists():
        print(f"[ERROR] Missing service file: {service_path}")
        sys.exit(1)

    if not password:
        print("[ERROR] Missing password (VALUESCAN_VPS_PASSWORD).")
        sys.exit(1)

    print("=" * 50)
    print("ValueScan auto refresh service deploy")
    print("=" * 50)
    print(f"Target: {user}@{host}")
    print(f"Service: {service_name}")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs = {
        "hostname": host,
        "port": 22,
        "username": user,
        "password": password,
        "timeout": 30,
        "banner_timeout": 30,
        "auth_timeout": 30,
    }

    print("\nConnecting...")
    _connect_ssh(ssh, connect_kwargs, host, user)
    sftp = ssh.open_sftp()

    remote_service = f"/etc/systemd/system/{service_path.name}"
    print("\nUploading service file...")
    sftp.put(str(service_path), remote_service)
    print(f"[OK] {service_path} -> {remote_service}")

    print("\nDisabling legacy refresher service...")
    legacy_disable = _exec(ssh, "systemctl disable --now valuescan-token-refresher.service")
    if legacy_disable:
        print(legacy_disable)
    legacy_remove = _exec(ssh, "rm -f /etc/systemd/system/valuescan-token-refresher.service")
    if legacy_remove:
        print(legacy_remove)

    print("\nReloading systemd...")
    result = _exec(ssh, "systemctl daemon-reload")
    print(result if result else "[OK] systemd reloaded")

    print("\nEnabling and starting service...")
    result = _exec(ssh, f"systemctl enable --now {service_path.stem}")
    print(result if result else f"[OK] {service_path.stem} enabled")

    print("\nRestarting service...")
    result = _exec(ssh, f"systemctl restart {service_path.stem}")
    print(result if result else f"[OK] {service_path.stem} restarted")

    print("\nStatus:")
    status = _exec(ssh, f"systemctl status {service_path.stem} --no-pager | head -40")
    status = status.encode("ascii", errors="ignore").decode("ascii")
    print(status)

    sftp.close()
    ssh.close()
    print("\n[SUCCESS] Service deployed.")


if __name__ == "__main__":
    main()
