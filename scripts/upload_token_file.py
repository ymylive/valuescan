#!/usr/bin/env python3
"""
Upload a local ValueScan token file to a VPS and restart services.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path


def _ascii(text: str) -> str:
    return (text or "").encode("ascii", errors="ignore").decode("ascii")


def _connect(host: str, user: str, password: str | None, key_file: str | None):
    try:
        import paramiko
    except ImportError as exc:
        raise RuntimeError("paramiko is required. Install with: pip install paramiko") from exc

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs = {
        "hostname": host,
        "username": user,
        "timeout": 30,
        "banner_timeout": 30,
        "auth_timeout": 30,
        "look_for_keys": False,
        "allow_agent": False,
    }
    if password:
        connect_kwargs["password"] = password
    elif key_file:
        connect_kwargs["key_filename"] = key_file
    else:
        raise RuntimeError("Missing password or key file")
    ssh.connect(**connect_kwargs)
    return ssh


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload ValueScan token file to VPS.")
    parser.add_argument(
        "--file",
        required=True,
        help="Path to local token json file",
    )
    parser.add_argument("--host", default=os.getenv("VALUESCAN_VPS_HOST", ""), help="VPS host")
    parser.add_argument("--user", default=os.getenv("VALUESCAN_VPS_USER", "root"), help="VPS user")
    parser.add_argument("--password", default=os.getenv("VALUESCAN_VPS_PASSWORD", ""), help="VPS password")
    parser.add_argument("--key-file", default=os.getenv("VALUESCAN_VPS_KEY_FILE", ""), help="SSH key file")
    parser.add_argument(
        "--remote-base",
        default=os.getenv("VALUESCAN_VPS_PATH", "/root/valuescan"),
        help="Remote base path",
    )
    parser.add_argument(
        "--services",
        default=os.getenv("VALUESCAN_TOKEN_SERVICES", "valuescan-monitor valuescan-token-refresher"),
        help="Services to restart (space separated)",
    )
    parser.add_argument("--skip-restart", action="store_true", help="Skip service restart")
    args = parser.parse_args()

    if not args.host:
        print("Missing --host or VALUESCAN_VPS_HOST")
        return 1

    local_path = Path(args.file)
    if not local_path.exists():
        print(f"Token file not found: {local_path}")
        return 1

    password = (args.password or "").strip() or None
    key_file = (args.key_file or "").strip() or None

    ssh = None
    try:
        print(f"Connecting to {args.user}@{args.host}...")
        ssh = _connect(args.host, args.user, password, key_file)
        sftp = ssh.open_sftp()

        remote_dir = f"{args.remote_base}/signal_monitor"
        remote_file = f"{remote_dir}/valuescan_localstorage.json"

        try:
            sftp.stat(remote_dir)
        except Exception:
            ssh.exec_command(f"mkdir -p {remote_dir}").channel.recv_exit_status()

        print(f"Uploading {local_path} -> {remote_file}")
        sftp.put(str(local_path), remote_file)
        sftp.close()

        if args.skip_restart:
            print("Upload complete. Restart skipped.")
            return 0

        services = [s for s in args.services.split() if s.strip()]
        if services:
            cmd = "systemctl restart " + " ".join(services)
            print(f"Restarting services: {' '.join(services)}")
            stdin, stdout, stderr = ssh.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            out = _ascii(stdout.read().decode("utf-8", errors="ignore"))
            err = _ascii(stderr.read().decode("utf-8", errors="ignore"))
            if out:
                print(out)
            if err:
                print(err)
            print(f"Restart exit status: {exit_status}")
            time.sleep(2)
        else:
            print("No services configured to restart.")

        return 0
    except Exception as exc:
        print(f"Upload failed: {exc}")
        return 1
    finally:
        if ssh:
            ssh.close()


if __name__ == "__main__":
    sys.exit(main())
