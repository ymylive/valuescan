#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Full deploy to VPS (preserve runtime config).

Usage:
  Set environment variables before running:
    VALUESCAN_VPS_HOST
    VALUESCAN_VPS_USER (optional, default: root)
    VALUESCAN_VPS_PASSWORD or VALUESCAN_VPS_KEY_FILE
    VALUESCAN_VPS_PATH (optional, default: /root/valuescan)
"""

import os
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import paramiko

PROJECT_ROOT = Path(__file__).resolve().parents[1]

EXCLUDE_DIR_NAMES = {
    ".git",
    ".github",
    ".claude",
    "__pycache__",
    "node_modules",
    "logs",
    "output",
    "data",
    "config_backup",
    "mcp",
    "metacubexd",
    "screenshots",
}

EXCLUDE_PATH_PREFIXES = (
    "signal_monitor/output/",
    "signal_monitor/chrome-debug-profile/",
    "signal_monitor/chrome_profile/",
    "web/node_modules/",
    "web/dist/",
)

EXCLUDE_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    "config_backup.json",
    "valuescan_cookies.json",
    "valuescan_localstorage.json",
    "valuescan_sessionstorage.json",
    "valuescan_localstorage.example.json",
    "valuescan_sessionstorage.example.json",
    "valuescan_cookies.example.json",
}

EXCLUDE_FILE_SUFFIXES = (
    ".log",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".tar.gz",
)

SERVICE_NAMES = [
    "valuescan-api",
    "valuescan-signal",
    "valuescan-monitor",
    "valuescan-trader",
    "valuescan-keepalive",
    "proxy-checker",
    "nginx",
]


def should_exclude(rel_path: Path) -> bool:
    path_str = rel_path.as_posix()
    if any(part in EXCLUDE_DIR_NAMES for part in rel_path.parts):
        return True

    for prefix in EXCLUDE_PATH_PREFIXES:
        if path_str.startswith(prefix):
            return True

    name = rel_path.name
    if name in EXCLUDE_FILE_NAMES:
        return True

    for suffix in EXCLUDE_FILE_SUFFIXES:
        if name.endswith(suffix):
            return True

    if path_str.startswith("signal_monitor/") and name.endswith("_config.json"):
        return True

    if path_str in ("signal_monitor/config.py", "binance_trader/config.py", "binance_trader/config.json"):
        return True

    return False


def build_tarball(tar_path: Path) -> int:
    files_added = 0
    with tarfile.open(tar_path, "w:gz") as tar:
        for path in PROJECT_ROOT.rglob("*"):
            if not path.is_file():
                continue
            rel_path = path.relative_to(PROJECT_ROOT)
            if should_exclude(rel_path):
                continue
            tar.add(path, arcname=rel_path.as_posix())
            files_added += 1
    return files_added


def connect_ssh(host: str, user: str, password: str, key_file: str) -> paramiko.SSHClient:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs = {"hostname": host, "username": user, "timeout": 30}
    if key_file:
        connect_kwargs["key_filename"] = key_file
    else:
        connect_kwargs["password"] = password

    ssh.connect(**connect_kwargs)
    return ssh


def safe_print(text: str) -> None:
    encoding = sys.stdout.encoding or "utf-8"
    print(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))


def run_ssh(ssh: paramiko.SSHClient, cmd: str, timeout: int = 300) -> int:
    print(f">>> {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode(errors="replace").strip()
    err = stderr.read().decode(errors="replace").strip()
    if out:
        safe_print(out)
    if err:
        safe_print(f"STDERR: {err}")
    return exit_code


def main() -> int:
    host = (os.environ.get("VALUESCAN_VPS_HOST") or "").strip()
    user = (os.environ.get("VALUESCAN_VPS_USER") or "root").strip()
    password = (os.environ.get("VALUESCAN_VPS_PASSWORD") or "").strip()
    key_file = (os.environ.get("VALUESCAN_VPS_KEY_FILE") or "").strip()
    vps_path = (os.environ.get("VALUESCAN_VPS_PATH") or "/root/valuescan").strip()

    if not host:
        print("Missing VALUESCAN_VPS_HOST")
        return 1
    if not password and not key_file:
        print("Missing VALUESCAN_VPS_PASSWORD or VALUESCAN_VPS_KEY_FILE")
        return 1

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    remote_tar = f"/tmp/valuescan_deploy_{timestamp}.tar.gz"

    print("=" * 80)
    print("ValueScan full deploy (preserve runtime config)")
    print("=" * 80)
    print(f"Target: {user}@{host}:{vps_path}")

    with tempfile.TemporaryDirectory() as temp_dir:
        tar_path = Path(temp_dir) / f"valuescan_deploy_{timestamp}.tar.gz"
        print("\n[1/5] Building tarball...")
        files_added = build_tarball(tar_path)
        print(f"Packed files: {files_added}")

        print("\n[2/5] Connecting to VPS...")
        ssh = connect_ssh(host, user, password, key_file)
        sftp = ssh.open_sftp()

        print("\n[3/5] Uploading tarball...")
        sftp.put(str(tar_path), remote_tar)
        sftp.close()

        print("\n[4/5] Extracting and rebuilding...")
        run_ssh(ssh, f"mkdir -p {vps_path}")
        run_ssh(ssh, f"tar -xzf {remote_tar} -C {vps_path}", timeout=600)
        run_ssh(ssh, f"rm -f {remote_tar}")
        run_ssh(ssh, f"cd {vps_path}/web && npm install --no-audit --no-fund", timeout=1200)
        run_ssh(ssh, f"cd {vps_path}/web && npm run build", timeout=1200)
        run_ssh(ssh, "mkdir -p /var/www/valuescan")
        run_ssh(ssh, f"cp -r {vps_path}/web/dist/* /var/www/valuescan/")
        run_ssh(ssh, "systemctl daemon-reload")

        print("\n[5/5] Restarting services...")
        for service in SERVICE_NAMES:
            exit_code = run_ssh(ssh, f"systemctl restart {service}")
            if exit_code != 0:
                print(f"[WARN] Restart failed or service missing: {service}")

        # Disable legacy token refresher if present (manual token only).
        run_ssh(ssh, "systemctl stop valuescan-token-refresher || true")
        run_ssh(ssh, "systemctl disable valuescan-token-refresher || true")

        print("\nService status:")
        for service in SERVICE_NAMES:
            run_ssh(ssh, f"systemctl is-active {service} || true")

        ssh.close()

    print("\nDeploy complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
