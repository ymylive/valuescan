#!/usr/bin/env python3
import os
import sys
import paramiko


HOST = os.getenv("VPS_HOST", "82.158.88.34")
USER = os.getenv("VPS_USER", "root")
PASSWORD = os.getenv("VPS_PASSWORD") or os.getenv("VALUESCAN_VPS_PASSWORD", "")
RUN_MACRO = os.getenv("VALUESCAN_TRIGGER_MACRO_SUMMARY", "0").lower() in ("1", "true", "yes", "on")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def _exec(ssh: paramiko.SSHClient, cmd: str, timeout: int = 600) -> str:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")
    return (out + ("\n" + err if err else "")).strip()


def main() -> None:
    if not PASSWORD:
        raise SystemExit("Missing VPS_PASSWORD/VALUESCAN_VPS_PASSWORD.")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)

    try:
        print("[1/2] Trigger signal scheduler (run once)...")
        cmd = (
            "cd /root/valuescan && "
            "VALUESCAN_AI_SIGNAL_RUN_ONCE=1 "
            "VALUESCAN_AI_SIGNAL_DRY_RUN=0 "
            "python3.9 signal_monitor/ai_signal_scheduler.py 2>&1"
        )
        print(_exec(ssh, cmd, timeout=1200))

        if RUN_MACRO:
            print("\n[2/2] Trigger market summary (force)...")
            cmd = (
                "cd /root/valuescan/signal_monitor && "
                "python3.9 -c \"from ai_market_summary import generate_market_summary; "
                "generate_market_summary(force=True)\" 2>&1"
            )
            print(_exec(ssh, cmd, timeout=300))
        else:
            print("\n[2/2] Skip macro summary (set VALUESCAN_TRIGGER_MACRO_SUMMARY=1 to enable).")
    finally:
        ssh.close()


if __name__ == "__main__":
    main()
