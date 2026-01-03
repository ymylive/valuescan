#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy the current patch set to the VPS.

Uploads:
- selected backend files
- selected signal monitor files
- web/dist (built frontend)

Restarts:
- valuescan-api
- valuescan-signal
- valuescan-trader
"""
from __future__ import annotations

import getpass
import os
import socket
import sys
from pathlib import Path

import paramiko
from paramiko.ssh_exception import AuthenticationException, BadAuthenticationType


DEFAULT_HOST = "82.158.88.34"
DEFAULT_USER = "root"
DEFAULT_PROJECT_ROOT = "/root/valuescan"
DEFAULT_WEB_ROOT = "/var/www/valuescan"


def _get_password() -> str | None:
    password = (os.environ.get("VALUESCAN_VPS_PASSWORD") or "").strip()
    if password:
        return password
    print("VALUESCAN_VPS_PASSWORD not set.")
    return None


def _prompt_password(host: str, user: str) -> str | None:
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


def _exec(ssh: paramiko.SSHClient, cmd: str, timeout: int = 180) -> str:
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="ignore")
        err = stderr.read().decode("utf-8", errors="ignore")
        return (out + ("\n" + err if err else "")).strip()
    except (socket.timeout, TimeoutError):
        return f"[timeout after {timeout}s] {cmd}"
    except Exception as exc:
        return f"[exec error] {cmd}: {exc}"


def _sftp_put_mkdir(sftp: paramiko.SFTPClient, local: Path, remote: str) -> None:
    remote_dir = remote.rsplit("/", 1)[0]
    parts = remote_dir.split("/")
    cur = ""
    for part in parts:
        if not part:
            continue
        cur += f"/{part}"
        try:
            sftp.stat(cur)
        except Exception:
            try:
                sftp.mkdir(cur)
            except Exception:
                pass
    sftp.put(str(local), remote)


def _sync_dist(ssh: paramiko.SSHClient, sftp: paramiko.SFTPClient, local_dist: Path, remote_dist: str) -> None:
    if not local_dist.exists():
        print(f"[WARN] Missing dist: {local_dist}")
        return
    _exec(ssh, f"mkdir -p {remote_dist} && rm -rf {remote_dist}/*", timeout=120)
    for path in local_dist.rglob("*"):
        if path.is_dir():
            continue
        rel = path.relative_to(local_dist).as_posix()
        remote_path = f"{remote_dist}/{rel}"
        _sftp_put_mkdir(sftp, path, remote_path)


def main() -> None:
    host = os.environ.get("VALUESCAN_VPS_HOST", DEFAULT_HOST)
    user = os.environ.get("VALUESCAN_VPS_USER", DEFAULT_USER)
    project_root = os.environ.get("VALUESCAN_VPS_PROJECT_ROOT", DEFAULT_PROJECT_ROOT)
    web_root = os.environ.get("VALUESCAN_VPS_WEB_ROOT", DEFAULT_WEB_ROOT)
    password = _get_password()

    print("=" * 50)
    print("ValueScan targeted deploy")
    print("=" * 50)
    print(f"Target: {user}@{host}")
    print(f"Project root: {project_root}")
    print(f"Web root: {web_root}")

    if not password:
        print("[ERROR] Missing password (VALUESCAN_VPS_PASSWORD).")
        sys.exit(1)

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

    uploads = [
        ("api/server.py", f"{project_root}/api/server.py"),
        ("token_refresher.py", f"{project_root}/token_refresher.py"),
        ("signal_monitor/telegram.py", f"{project_root}/signal_monitor/telegram.py"),
        ("signal_monitor/ai_signal_queue.py", f"{project_root}/signal_monitor/ai_signal_queue.py"),
        ("signal_monitor/ai_signal_analysis.py", f"{project_root}/signal_monitor/ai_signal_analysis.py"),
        ("signal_monitor/ai_market_summary.py", f"{project_root}/signal_monitor/ai_market_summary.py"),
        ("signal_monitor/ai_market_analysis.py", f"{project_root}/signal_monitor/ai_market_analysis.py"),
        ("signal_monitor/chart_pro_v10.py", f"{project_root}/signal_monitor/chart_pro_v10.py"),
        ("signal_monitor/config.example.py", f"{project_root}/signal_monitor/config.example.py"),
        ("scripts/auto_refresh_access_token.py", f"{project_root}/scripts/auto_refresh_access_token.py"),
    ]

    print("\nUploading files...")
    for local_rel, remote in uploads:
        local_path = Path(local_rel)
        if not local_path.exists():
            print(f"[SKIP] {local_rel} (missing)")
            continue
        _sftp_put_mkdir(sftp, local_path, remote)
        print(f"[OK] {local_rel} -> {remote}")

    print("\nSyncing web/dist...")
    _sync_dist(ssh, sftp, Path("web/dist"), f"{project_root}/web/dist")
    if web_root:
        result = _exec(
            ssh,
            f"mkdir -p {web_root} && cp -r {project_root}/web/dist/* {web_root}/",
            timeout=120,
        )
        if result:
            print(result)
        print(f"[OK] web/dist -> {web_root}")

    print("\nRestarting services...")
    for svc in ("valuescan-api", "valuescan-signal", "valuescan-trader"):
        result = _exec(ssh, f"systemctl restart {svc}")
        print(result if result else f"[OK] {svc} restarted")

    print("\nStatus:")
    status = _exec(ssh, "systemctl status valuescan-api valuescan-signal valuescan-trader --no-pager | head -40")
    status = status.encode("ascii", errors="ignore").decode("ascii")
    print(status)

    sftp.close()
    ssh.close()
    print("\n[SUCCESS] Deployment completed.")


if __name__ == "__main__":
    main()
