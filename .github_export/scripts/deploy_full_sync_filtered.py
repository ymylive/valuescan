#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Full sync deploy to VPS (filtered, tar-based).
Packages repo files except sensitive/config/runtime artifacts, uploads and extracts.
Also syncs web/dist to VPS web root and restarts services.
"""
from __future__ import annotations

import fnmatch
import os
import sys
import tarfile
import tempfile
from pathlib import Path

import paramiko


DEFAULT_HOST = "82.158.88.34"
DEFAULT_USER = "root"
DEFAULT_PROJECT_ROOT = "/root/valuescan"
DEFAULT_WEB_ROOT = "/var/www/valuescan"

EXCLUDE_PREFIXES = {
    ".git",
    ".claude",
    ".venv",
    "__pycache__",
    "node_modules",
    "web/node_modules",
    "web/.vite",
    "data",
    "logs",
    "output",
    "signal_monitor/output",
    "signal_monitor/chrome-debug-profile",
    "mcp/chrome-profile",
    "config_backup",
}

EXCLUDE_FILES = {
    ".env",
    "config.json",
    "configbak.json",
    "keepalive_config.json",
    "ipc_config.py",
    "valuescan_cookies.json",
    "valuescan_localstorage.json",
    "valuescan_sessionstorage.json",
    "signal_monitor/config.py",
    "signal_monitor/valuescan_credentials.json",
    "binance_trader/config.py",
    "telegram_copytrade/config.py",
    "keepalive/config.py",
    "config/valuescan.env",
    "config_backup.json",
    "nul",
    "NUL",
}

EXCLUDE_GLOBS = [
    "*.log",
    "*_log.txt",
    "*.tmp",
    "*.bak",
    "*.backup",
    "*.tar.gz",
    "*.db",
]


def _norm_rel(path: Path, root: Path) -> str:
    rel = path.relative_to(root).as_posix()
    return rel


def _is_excluded(rel_posix: str) -> bool:
    if rel_posix in EXCLUDE_FILES:
        return True
    for prefix in EXCLUDE_PREFIXES:
        if rel_posix == prefix or rel_posix.startswith(prefix + "/"):
            return True
    for pattern in EXCLUDE_GLOBS:
        if fnmatch.fnmatch(rel_posix, pattern):
            return True
    return False


def _collect_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        rel = _norm_rel(path, root)
        if _is_excluded(rel):
            continue
        files.append(path)
    return files


def _exec(ssh: paramiko.SSHClient, cmd: str, timeout: int = 180) -> str:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")
    return (out + ("\n" + err if err else "")).strip()


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    host = os.getenv("VALUESCAN_VPS_HOST", DEFAULT_HOST)
    user = os.getenv("VALUESCAN_VPS_USER", DEFAULT_USER)
    password = (os.getenv("VALUESCAN_VPS_PASSWORD") or "").strip()
    project_root = os.getenv("VALUESCAN_VPS_PROJECT_ROOT", DEFAULT_PROJECT_ROOT)
    web_root = os.getenv("VALUESCAN_VPS_WEB_ROOT", DEFAULT_WEB_ROOT)

    if not password:
        print("Missing VALUESCAN_VPS_PASSWORD.")
        return 1

    files = _collect_files(root)
    if not files:
        print("No files to package.")
        return 1

    with tempfile.TemporaryDirectory() as tmpdir:
        tar_path = Path(tmpdir) / "valuescan_sync.tar.gz"
        print(f"Packaging {len(files)} files ...")
        with tarfile.open(tar_path, "w:gz") as tar:
            for path in files:
                rel = _norm_rel(path, root)
                tar.add(path, arcname=rel)

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=host,
            port=22,
            username=user,
            password=password,
            look_for_keys=False,
            allow_agent=False,
            timeout=30,
            banner_timeout=30,
            auth_timeout=30,
        )
        sftp = ssh.open_sftp()

        remote_tar = "/tmp/valuescan_sync.tar.gz"
        print(f"Uploading archive to {user}@{host}:{remote_tar} ...")
        sftp.put(str(tar_path), remote_tar)

        print("Extracting archive ...")
        _exec(ssh, f"mkdir -p {project_root} && tar -xzf {remote_tar} -C {project_root}", timeout=300)
        _exec(ssh, f"rm -f {remote_tar}")

        if web_root:
            _exec(
                ssh,
                f"mkdir -p {web_root} && cp -r {project_root}/web/dist/* {web_root}/",
                timeout=120,
            )

        print("Restarting services ...")
        for svc in ("valuescan-api", "valuescan-signal", "valuescan-trader"):
            _exec(ssh, f"systemctl restart {svc}")

        sftp.close()
        ssh.close()
        print("Deployment completed.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
