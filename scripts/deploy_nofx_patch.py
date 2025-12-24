#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patch NOFX files on VPS and rebuild backend container.
Reads SSH credentials from env:
- VALUESCAN_VPS_HOST (default: 82.158.88.34)
- VALUESCAN_VPS_USER (default: root)
- VALUESCAN_VPS_PASSWORD (required)
"""
from __future__ import annotations

import os
import socket
from pathlib import Path

import paramiko


DEFAULT_HOST = "82.158.88.34"
DEFAULT_USER = "root"
NOFX_DIR = "/opt/nofx"


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


def main() -> None:
    host = os.environ.get("VALUESCAN_VPS_HOST", DEFAULT_HOST)
    user = os.environ.get("VALUESCAN_VPS_USER", DEFAULT_USER)
    password = os.environ.get("VALUESCAN_VPS_PASSWORD", "").strip()
    if not password:
        raise SystemExit("VALUESCAN_VPS_PASSWORD not set in environment.")

    print(f"Connecting to {user}@{host}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    port = int(os.environ.get("VALUESCAN_VPS_PORT", "22"))
    ssh.connect(
        hostname=host,
        username=user,
        password=password,
        port=port,
        timeout=30,
        banner_timeout=30,
        auth_timeout=30,
    )
    sftp = ssh.open_sftp()

    try:
        print("Uploading NOFX patches...")
        file_map = {
            Path("api/server.go"): f"{NOFX_DIR}/api/server.go",
            Path("market/api_client.go"): f"{NOFX_DIR}/market/api_client.go",
            Path("trader/binance_futures.go"): f"{NOFX_DIR}/trader/binance_futures.go",
            Path("netutil/proxy.go"): f"{NOFX_DIR}/netutil/proxy.go",
            Path("docker-compose.yml"): f"{NOFX_DIR}/docker-compose.yml",
            Path(".env.example"): f"{NOFX_DIR}/.env.example",
        }
        for local, remote in file_map.items():
            if not local.exists():
                print(f"  SKIP missing: {local}")
                continue
            _sftp_put_mkdir(sftp, local, remote)
            print(f"  OK {local} -> {remote}")

        print("Configuring proxy subscription + env...")
        subscribe_url = (
            os.environ.get("PROXY_SUBSCRIBE_URL")
            or os.environ.get("VALUESCAN_PROXY_SUBSCRIBE_URL")
            or ""
        ).strip()
        if not subscribe_url:
            raise SystemExit("PROXY_SUBSCRIBE_URL not set in environment.")

        escaped = subscribe_url.replace("'", "'\"'\"'")
        cmds = [
            "set -e",
            "mkdir -p /etc/valuescan",
            f"printf '%s' '{escaped}' > /etc/valuescan/proxy_subscribe_url",
            "chmod 600 /etc/valuescan/proxy_subscribe_url",
            f"test -f {NOFX_DIR}/.env || touch {NOFX_DIR}/.env",
            f"grep -q '^BINANCE_SOCKS5_PROXY=' {NOFX_DIR}/.env && "
            f"sed -i 's|^BINANCE_SOCKS5_PROXY=.*|BINANCE_SOCKS5_PROXY=socks5://host.docker.internal:1080|' {NOFX_DIR}/.env || "
            f"echo 'BINANCE_SOCKS5_PROXY=socks5://host.docker.internal:1080' >> {NOFX_DIR}/.env",
            f"grep -q '^PROXY_SUBSCRIBE_URL=' {NOFX_DIR}/.env && "
            f"sed -i 's|^PROXY_SUBSCRIBE_URL=.*|PROXY_SUBSCRIBE_URL={escaped}|' {NOFX_DIR}/.env || "
            f"echo 'PROXY_SUBSCRIBE_URL={escaped}' >> {NOFX_DIR}/.env",
        ]
        print(_exec(ssh, " && ".join(cmds), timeout=60))

        print("Restarting proxy services (best-effort)...")
        print(_exec(ssh, "systemctl restart proxy-checker xray 2>/dev/null || true", timeout=30))

        print("Rebuilding NOFX backend container...")
        build_cmd = f"cd {NOFX_DIR} && docker compose up -d --build nofx"
        print(_exec(ssh, build_cmd, timeout=900))

        print("Done.")
    finally:
        try:
            sftp.close()
        except Exception:
            pass
        ssh.close()


if __name__ == "__main__":
    main()
