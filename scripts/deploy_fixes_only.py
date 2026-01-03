#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy only ValueScan updates (no NOFX)
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
VALUESCAN_DIR = "/root/valuescan"


def _get_password() -> str | None:
    password = os.environ.get("VALUESCAN_VPS_PASSWORD", "")
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
    except (BadAuthenticationType, AuthenticationException):
        if not connect_kwargs.get("password"):
            pw = _prompt_password(host, user)
            if pw:
                connect_kwargs["password"] = pw
                ssh.connect(**connect_kwargs)
                return
        raise


def _exec(ssh: paramiko.SSHClient, cmd: str, timeout: int = 300) -> str:
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
        print(f"  Local dist not found: {local_dist}")
        return

    _exec(ssh, f"mkdir -p {remote_dist} && rm -rf {remote_dist}/*", timeout=120)

    for path in local_dist.rglob("*"):
        if path.is_dir():
            continue
        rel = path.relative_to(local_dist).as_posix()
        remote_path = f"{remote_dist}/{rel}"
        _sftp_put_mkdir(sftp, path, remote_path)


def deploy_valuescan(ssh: paramiko.SSHClient, sftp: paramiko.SFTPClient) -> None:
    print("\n" + "=" * 50)
    print("Deploy ValueScan updates")
    print("=" * 50)

    file_uploads = [
        (Path("api/server.py"), f"{VALUESCAN_DIR}/api/server.py"),
        (Path("signal_monitor/ai_market_summary.py"), f"{VALUESCAN_DIR}/signal_monitor/ai_market_summary.py"),
        (Path("web/vite.config.ts"), f"{VALUESCAN_DIR}/web/vite.config.ts"),
    ]

    print("\nUploading backend files...")
    for local, remote in file_uploads:
        if local.exists():
            _sftp_put_mkdir(sftp, local, remote)
            print(f"  [OK] {local} -> {remote}")
        else:
            print(f"  [SKIP] {local} (not found)")

    print("\nUploading ValueScan frontend...")
    local_dist = Path("web/dist")
    if local_dist.exists():
        _sync_dist(ssh, sftp, local_dist, f"{VALUESCAN_DIR}/web/dist")
        print(f"  [OK] {local_dist} -> {VALUESCAN_DIR}/web/dist")
    else:
        print("  [WARN] web/dist not found")

    print("\nSyncing frontend to Nginx root (/var/www/valuescan)...")
    result = _exec(
        ssh,
        f"""
mkdir -p /var/www/valuescan
cp -r {VALUESCAN_DIR}/web/dist/* /var/www/valuescan/
ls -la /var/www/valuescan | head -5
""",
        timeout=120,
    )
    print(result)


def restart_services(ssh: paramiko.SSHClient) -> None:
    print("\n" + "=" * 50)
    print("Restart services")
    print("=" * 50)

    print("\nRestarting valuescan-api...")
    result = _exec(ssh, "systemctl restart valuescan-api")
    print(result if result else "  [OK]")

    print("\nRestarting valuescan-signal...")
    result = _exec(ssh, "systemctl restart valuescan-signal")
    print(result if result else "  [OK]")

    print("\nChecking service status...")
    result = _exec(ssh, "systemctl status valuescan-api valuescan-signal --no-pager | head -30")
    # Remove emoji characters to avoid encoding issues
    result = result.encode('ascii', errors='ignore').decode('ascii')
    print(result)


def main() -> None:
    print("=" * 50)
    print("ValueScan deploy script (fixes only)")
    print("=" * 50)

    host = os.environ.get("VALUESCAN_VPS_HOST", DEFAULT_HOST)
    user = os.environ.get("VALUESCAN_VPS_USER", DEFAULT_USER)
    password = _get_password()

    print(f"Target: {user}@{host}")
    print(f"ValueScan dir: {VALUESCAN_DIR}")

    if not password:
        print("\n[ERROR] No password provided")
        print("Set VALUESCAN_VPS_PASSWORD environment variable")
        sys.exit(1)

    print(f"\nConnecting to {user}@{host}...")
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

    try:
        _connect_ssh(ssh, connect_kwargs, host, user)
        sftp = ssh.open_sftp()

        deploy_valuescan(ssh, sftp)
        restart_services(ssh)

        print("\n" + "=" * 50)
        print("[SUCCESS] Deployment completed!")
        print("=" * 50)
        print("\nPlease verify:")
        print("1. Visit web interface and check config page")
        print("2. Trigger AI summary and check async execution")
        print(f"3. Check logs: ssh {user}@{host} 'journalctl -u valuescan-signal -f'")

    except Exception as exc:
        print(f"\n[ERROR] Deployment failed: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        ssh.close()


if __name__ == "__main__":
    main()
