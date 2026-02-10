#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnose duplicate macro summary sends on VPS.
"""
from __future__ import annotations

import getpass
import os
import sys
from typing import List, Tuple

import paramiko

DEFAULT_HOST = "82.158.88.34"
DEFAULT_USER = "root"


def _get_password() -> str | None:
    password = os.environ.get("VALUESCAN_VPS_PASSWORD", "").strip()
    if password:
        return password
    if sys.stdin.isatty():
        try:
            pw = getpass.getpass(f"Enter SSH password for {DEFAULT_USER}@{DEFAULT_HOST}: ")
            return (pw or "").strip() or None
        except Exception:
            return None
    return None


def _exec(ssh: paramiko.SSHClient, cmd: str, timeout: int = 60) -> str:
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="ignore")
        err = stderr.read().decode("utf-8", errors="ignore")
        return (out + ("\n" + err if err else "")).strip()
    except Exception as exc:
        return f"[exec error] {cmd}: {exc}"


def _print_block(title: str, output: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    print(output or "(no output)")


def main() -> None:
    password = _get_password()
    if not password:
        print("Missing VALUESCAN_VPS_PASSWORD environment variable.")
        return

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"Connecting to {DEFAULT_USER}@{DEFAULT_HOST}...")
        ssh.connect(DEFAULT_HOST, username=DEFAULT_USER, password=password, timeout=30)
        print("SSH connected.")
    except Exception as exc:
        print(f"SSH connection failed: {exc}")
        return

    commands: List[Tuple[str, str]] = [
        ("systemd units (running)", "systemctl list-units --type=service --all | grep -i valuescan || true"),
        ("systemd unit files", "systemctl list-unit-files | grep -i valuescan || true"),
        ("systemd timers", "systemctl list-timers --all | grep -i valuescan || true"),
        ("systemd unit grep (ai_signal_scheduler)", "grep -R \"ai_signal_scheduler\" /etc/systemd/system -n 2>/dev/null || true"),
        ("processes (ai_signal_scheduler / ai_market_summary)", "pgrep -af \"ai_signal_scheduler|ai_market_summary\" || true"),
        ("processes (valuescan)", "pgrep -af valuescan || true"),
        ("lock file", "ls -l /tmp/valuescan_ai_signal.lock 2>/dev/null && cat /tmp/valuescan_ai_signal.lock 2>/dev/null || true"),
        ("valuescan dirs", "ls -ld /root/valuescan* 2>/dev/null || true"),
        ("valuescan-monitor status", "systemctl status valuescan-monitor --no-pager || true"),
        ("valuescan-signal status", "systemctl status valuescan-signal --no-pager || true"),
        ("crontab", "crontab -l 2>/dev/null || true"),
        ("cron directories", "ls -l /etc/cron* 2>/dev/null || true"),
    ]

    for title, cmd in commands:
        _print_block(title, _exec(ssh, cmd))

    ssh.close()


if __name__ == "__main__":
    main()
