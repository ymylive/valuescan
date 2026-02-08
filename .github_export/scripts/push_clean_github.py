#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create a clean export (excluding sensitive/runtime files) and force-push to GitHub.
This replaces the remote repo contents with the filtered local state.
"""
from __future__ import annotations

import fnmatch
import os
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
EXPORT_DIR = REPO_ROOT / ".github_export"
REMOTE_URL = "https://github.com/ymylive/valuescan.git"

EXCLUDE_PREFIXES = {
    ".git",
    ".claude",
    ".venv",
    "__pycache__",
    "node_modules",
    "web/node_modules",
    "web/dist",
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


def _copy_tree() -> None:
    if EXPORT_DIR.exists():
        def _onerror(func, path, _exc_info):
            try:
                os.chmod(path, 0o700)
                func(path)
            except Exception:
                pass
        shutil.rmtree(EXPORT_DIR, onerror=_onerror)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    for path in REPO_ROOT.rglob("*"):
        if path.is_dir():
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel.startswith(".github_export/"):
            continue
        if _is_excluded(rel):
            continue
        dest = EXPORT_DIR / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(path, dest)
        except OSError:
            # Skip Windows-reserved or invalid filenames (e.g., NUL)
            continue


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def main() -> None:
    _copy_tree()

    _run(["git", "init"], EXPORT_DIR)
    _run(["git", "config", "user.name", "valuescan-bot"], EXPORT_DIR)
    _run(["git", "config", "user.email", "valuescan-bot@users.noreply.github.com"], EXPORT_DIR)
    _run(["git", "add", "-A"], EXPORT_DIR)
    _run(["git", "commit", "-m", "sync from local"], EXPORT_DIR)
    _run(["git", "branch", "-M", "master"], EXPORT_DIR)
    _run(["git", "remote", "add", "origin", REMOTE_URL], EXPORT_DIR)
    _run(["git", "push", "--force", "origin", "master"], EXPORT_DIR)


if __name__ == "__main__":
    main()
