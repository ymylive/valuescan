#!/usr/bin/env python3
"""
Deploy major coin strategy updates to the ValueScan VPS.

Uploads:
- binance_trader/config.py
- binance_trader/config.example.py
- binance_trader/risk_manager.py
- binance_trader/futures_main.py
- api/server.py
- web/dist (frontend)

Restarts:
- valuescan-api
- valuescan-trader
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import paramiko


DEFAULT_HOST = "82.158.88.34"
DEFAULT_USER = "root"
DEFAULT_PROJECT_ROOT = "/root/valuescan"


def _get_password() -> str | None:
    password = os.environ.get("VALUESCAN_VPS_PASSWORD", "")
    if password:
        return password
    print("VALUESCAN_VPS_PASSWORD not found.")
    return None


def _exec(ssh: paramiko.SSHClient, cmd: str, timeout: int = 120) -> str:
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="ignore")
        err = stderr.read().decode("utf-8", errors="ignore")
        return (out + ("\n" + err if err else "")).strip()
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
        raise SystemExit(f"Local dist not found: {local_dist}")

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

    password = _get_password()
    if not password:
        raise SystemExit("Password required. Set VALUESCAN_VPS_PASSWORD env var.")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {user}@{host} ...")
    
    try:
        ssh.connect(hostname=host, username=user, password=password, timeout=30)
    except Exception as exc:
        raise SystemExit(f"SSH connect failed: {exc}")
    
    sftp = ssh.open_sftp()

    try:
        print("Uploading major coin strategy files...")
        
        # Core files to upload
        file_uploads = [
            # Backend - binance trader
            (Path("binance_trader/config.example.py"), f"{project_root}/binance_trader/config.example.py"),
            (Path("binance_trader/risk_manager.py"), f"{project_root}/binance_trader/risk_manager.py"),
            (Path("binance_trader/futures_main.py"), f"{project_root}/binance_trader/futures_main.py"),
            # API server
            (Path("api/server.py"), f"{project_root}/api/server.py"),
            # Types
            (Path("web/src/types/config.ts"), f"{project_root}/web/src/types/config.ts"),
        ]

        for local, remote in file_uploads:
            if local.exists():
                _sftp_put_mkdir(sftp, local, remote)
                print(f"  OK {local} -> {remote}")
            else:
                print(f"  SKIP missing local file: {local}")

        # Upload web dist
        print("Uploading web dist...")
        local_dist = Path("web/dist")
        if local_dist.exists():
            _sync_dist(ssh, sftp, local_dist, f"{project_root}/web/dist")
            print(f"  OK {local_dist} -> {project_root}/web/dist")
        else:
            print(f"  SKIP web/dist not found")

        # Restart services
        print("Restarting services...")
        print(_exec(ssh, "systemctl daemon-reload 2>/dev/null || true", timeout=30))
        print(_exec(
            ssh,
            "systemctl restart valuescan-api valuescan-trader 2>/dev/null || true",
            timeout=60,
        ))
        time.sleep(2)

        # Verify
        print("Verifying...")
        print(_exec(
            ssh,
            "systemctl is-active valuescan-api valuescan-trader --no-pager 2>/dev/null || true",
            timeout=30,
        ))
        
        print("\nDone! Major coin strategy update deployed.")
        
    finally:
        try:
            sftp.close()
        except Exception:
            pass
        ssh.close()


if __name__ == "__main__":
    main()
