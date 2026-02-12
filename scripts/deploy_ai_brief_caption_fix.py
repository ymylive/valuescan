import os
import os
from pathlib import Path
import paramiko

HOST = os.getenv("VALUESCAN_VPS_HOST", "82.158.88.34")
USER = os.getenv("VALUESCAN_VPS_USER", "root")
PASSWORD = os.getenv("VALUESCAN_VPS_PASSWORD", "")

LOCAL_ROOT = Path(r"E:\project\valuescan")
LOCAL_FILE = LOCAL_ROOT / "signal_monitor" / "telegram.py"
REMOTE_ROOT = "/root/valuescan"
REMOTE_FILE = f"{REMOTE_ROOT}/signal_monitor/telegram.py"


def run_ssh(ssh, cmd, timeout=60):
    print(f">>> {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    if out:
        print(out)
    if err:
        print(f"STDERR: {err}")
    return exit_code, out, err


def main():
    if not PASSWORD:
        raise SystemExit("Missing VALUESCAN_VPS_PASSWORD.")
    if not LOCAL_FILE.exists():
        raise SystemExit(f"Local file not found: {LOCAL_FILE}")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {HOST} as {USER}...")
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)

    sftp = ssh.open_sftp()
    sftp.put(str(LOCAL_FILE), REMOTE_FILE)
    sftp.close()
    print(f"Uploaded {LOCAL_FILE} -> {REMOTE_FILE}")

    run_ssh(ssh, "systemctl restart valuescan-signal")
    run_ssh(ssh, "systemctl restart valuescan-monitor")
    run_ssh(ssh, "systemctl status valuescan-signal --no-pager | head -n 10")
    run_ssh(ssh, "systemctl status valuescan-monitor --no-pager | head -n 10")

    ssh.close()
    print("Deploy complete.")


if __name__ == "__main__":
    main()
