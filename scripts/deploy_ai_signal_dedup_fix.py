#!/usr/bin/env python3
"""Deploy AI signal dedup fix to VPS."""

import os
import sys
import paramiko


def _get_env(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    if value:
        return value
    return default


def main() -> int:
    host = _get_env("VALUESCAN_VPS_HOST", "82.158.88.34")
    user = _get_env("VALUESCAN_VPS_USER", "root")
    password = _get_env("VALUESCAN_VPS_PASSWORD", "")

    if not password:
        print("Error: VALUESCAN_VPS_PASSWORD not set")
        return 1

    files = [
        ("signal_monitor/ai_signal_scheduler.py", "/root/valuescan/signal_monitor/ai_signal_scheduler.py"),
        ("signal_monitor/message_handler.py", "/root/valuescan/signal_monitor/message_handler.py"),
    ]

    print(f"[*] Connecting to {user}@{host}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(host, username=user, password=password, timeout=30)
        print("[+] Connected")
    except Exception as exc:
        print(f"[ERROR] Connection failed: {exc}")
        return 1

    sftp = ssh.open_sftp()
    try:
        for local_path, remote_path in files:
            print(f"[*] Uploading {local_path} -> {remote_path}")
            sftp.put(local_path, remote_path)
            print("[+] Uploaded")
    except Exception as exc:
        print(f"[ERROR] Upload failed: {exc}")
        sftp.close()
        ssh.close()
        return 1
    finally:
        try:
            sftp.close()
        except Exception:
            pass

    restart_cmds = [
        "systemctl restart valuescan-signal",
        "systemctl restart valuescan-monitor",
    ]
    for cmd in restart_cmds:
        print(f"[*] {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
        stdout.channel.recv_exit_status()

    print("\n[*] Service status:")
    stdin, stdout, stderr = ssh.exec_command(
        "systemctl status valuescan-signal --no-pager -l | head -10", timeout=30
    )
    print(stdout.read().decode("utf-8", errors="replace"))
    stdin, stdout, stderr = ssh.exec_command(
        "systemctl status valuescan-monitor --no-pager -l | head -10", timeout=30
    )
    print(stdout.read().decode("utf-8", errors="replace"))

    ssh.close()
    print("[+] Done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
