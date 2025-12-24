#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Combined deploy script for ValueScan + NOFX.

Env vars:
- VALUESCAN_VPS_HOST (default: 82.158.88.34)
- VALUESCAN_VPS_USER (default: root)
- VALUESCAN_VPS_PASSWORD (required)
"""
from __future__ import annotations

import getpass
import os
import socket
import sys
from pathlib import Path

import paramiko
from paramiko.ssh_exception import AuthenticationException, BadAuthenticationType

DEFAULT_HOST = "82.158.88.34"
DEFAULT_USER = "root"
VALUESCAN_DIR = "/root/valuescan"
NOFX_DIR = "/opt/nofx"
NOFX_REPO = "https://github.com/NoFxAiOS/nofx.git"
NOFX_BRANCH = "dev"


def _get_password() -> str | None:
    password = os.environ.get("VALUESCAN_VPS_PASSWORD", "")
    if password:
        return password
    print("VALUESCAN_VPS_PASSWORD not set.")
    return None


def _prompt_password(host: str, user: str) -> str | None:
    if not sys.stdin.isatty():
        return None
    try:
        pw = getpass.getpass(f"Enter SSH password for {user}@{host}: ")
    except Exception:
        return None
    return (pw or "").strip() or None


def _connect_ssh(ssh: paramiko.SSHClient, connect_kwargs: dict, host: str, user: str) -> None:
    try:
        ssh.connect(**connect_kwargs)
        return
    except (BadAuthenticationType, AuthenticationException):
        if not connect_kwargs.get("password"):
            pw = _prompt_password(host, user)
            if pw:
                connect_kwargs["password"] = pw
                ssh.connect(**connect_kwargs)
                return
        raise


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


def _sync_dist(ssh: paramiko.SSHClient, sftp: paramiko.SFTPClient, local_dist: Path, remote_dist: str) -> None:
    if not local_dist.exists():
        print(f"  Local dist not found: {local_dist}")
        return

    _exec(ssh, f"mkdir -p {remote_dist} && rm -rf {remote_dist}/*", timeout=120)

    for path in local_dist.rglob("*"):
        if path.is_dir():
            continue
        rel = path.relative_to(local_dist).as_posix()
        remote_path = f"{remote_dist}/{rel}"
        _sftp_put_mkdir(sftp, path, remote_path)


def deploy_valuescan(ssh: paramiko.SSHClient, sftp: paramiko.SFTPClient) -> None:
    print("\n" + "=" * 50)
    print("Step 1: Deploy ValueScan updates")
    print("=" * 50)

    file_uploads = [
        (Path("api/server.py"), f"{VALUESCAN_DIR}/api/server.py"),
        (Path("api/nofx_compat.py"), f"{VALUESCAN_DIR}/api/nofx_compat.py"),
        (Path("signal_monitor/token_refresher.py"), f"{VALUESCAN_DIR}/signal_monitor/token_refresher.py"),
        (Path("signal_monitor/polling_monitor.py"), f"{VALUESCAN_DIR}/signal_monitor/polling_monitor.py"),
    ]

    print("\nUploading backend files...")
    for local, remote in file_uploads:
        if local.exists():
            _sftp_put_mkdir(sftp, local, remote)
            print(f"  OK {local} -> {remote}")
        else:
            print(f"  Skip (missing): {local}")

    print("\nUploading ValueScan frontend...")
    local_dist = Path("web/dist")
    if local_dist.exists():
        _sync_dist(ssh, sftp, local_dist, f"{VALUESCAN_DIR}/web/dist")
        print(f"  OK {local_dist} -> {VALUESCAN_DIR}/web/dist")
    else:
        print("  web/dist not found; building on VPS...")
        result = _exec(
            ssh,
            f"""
cd {VALUESCAN_DIR}
git status -sb
git pull --rebase
cd web
npm ci || npm install
npm run build
""",
            timeout=600,
        )
        print(result)


def deploy_nofx(ssh: paramiko.SSHClient) -> None:
    print("\n" + "=" * 50)
    print("Step 2: Re-deploy NOFX")
    print("=" * 50)

    print("\nStopping NOFX service if present...")
    result = _exec(ssh, "systemctl list-units --type=service | grep -i nofx || echo 'no NOFX service'")
    print(result)
    _exec(ssh, "systemctl stop nofx 2>/dev/null || true")

    print(f"\nRemoving old NOFX dir: {NOFX_DIR}...")
    result = _exec(ssh, f"rm -rf {NOFX_DIR} && echo 'removed'")
    print(result)

    print(f"\nCloning {NOFX_BRANCH} branch...")
    result = _exec(
        ssh,
        f"""
git clone --branch {NOFX_BRANCH} --single-branch {NOFX_REPO} {NOFX_DIR}
""",
        timeout=300,
    )
    print(result)

    print("\nBuilding NOFX frontend (base=/nofx/)...")
    result = _exec(
        ssh,
        f"""
cd {NOFX_DIR}/web
npm ci || npm install
npm run build -- --base /nofx/
""",
        timeout=600,
    )
    print(result)


def configure_nginx(ssh: paramiko.SSHClient) -> None:
    print("\n" + "=" * 50)
    print("Step 3: Configure Nginx")
    print("=" * 50)

    print("\nChecking existing Nginx config...")
    result = _exec(ssh, "grep -l 'nofx' /etc/nginx/conf.d/*.conf 2>/dev/null || echo 'no nofx config'")
    print(result)

    print("\nUpdating Nginx config...")
    check_result = _exec(
        ssh,
        "grep -q 'location.*nofx' /etc/nginx/conf.d/valuescan.conf 2>/dev/null && echo 'EXISTS' || echo 'NOT_EXISTS'",
    )

    if "NOT_EXISTS" in check_result:
        print("  Adding NOFX location to valuescan.conf...")
        result = _exec(
            ssh,
            """
cp /etc/nginx/conf.d/valuescan.conf /etc/nginx/conf.d/valuescan.conf.bak.$(date +%Y%m%d%H%M%S)

if ! grep -q 'location.*nofx' /etc/nginx/conf.d/valuescan.conf; then
    sed -i '/location \\/ {/i\\
    # NOFX static files\\
    location = /nofx {\\
        return 301 /nofx/;\\
    }\\
\\
    # Redirect legacy NOFX strategy path to /nofx\\
    location = /strategy {\\
        return 301 /nofx/strategy$is_args$args;\\
    }\\
\\
    location ^~ /strategy/ {\\
        return 301 /nofx/strategy$is_args$args;\\
    }\\
\\
    location /nofx/ {\\
        alias /opt/nofx/web/dist/;\\
        try_files $uri $uri/ /nofx/index.html;\\
    }\\
' /etc/nginx/conf.d/valuescan.conf
fi
""",
        )
        print(result)
    else:
        print("  NOFX config already present.")

    print("\nTesting Nginx config...")
    result = _exec(ssh, "nginx -t")
    print(result)

    if "successful" in result or "ok" in result.lower():
        print("\nReloading Nginx...")
        result = _exec(ssh, "systemctl reload nginx")
        print(result or "  OK: Nginx reloaded")


def restart_services(ssh: paramiko.SSHClient) -> None:
    print("\n" + "=" * 50)
    print("Step 4: Restart ValueScan services")
    print("=" * 50)

    print("\nCurrent ValueScan services:")
    result = _exec(ssh, "systemctl list-units --type=service | grep -i valuescan")
    print(result)

    print("\nRestarting services...")
    result = _exec(
        ssh,
        """
systemctl restart valuescan-monitor valuescan-signal valuescan-token-refresher valuescan-api 2>/dev/null || true
sleep 2
systemctl status valuescan-monitor valuescan-signal valuescan-token-refresher valuescan-api --no-pager | grep -E '(Active:|\*|o)' || true
""",
    )
    print(result)


def verify_deployment(ssh: paramiko.SSHClient) -> None:
    print("\n" + "=" * 50)
    print("Step 5: Verify deployment")
    print("=" * 50)

    print("\nCheck NOFX dist:")
    result = _exec(ssh, f"ls -la {NOFX_DIR}/web/dist/ 2>/dev/null | head -10 || echo 'NOFX dist missing'")
    print(result)

    print("\nCheck API endpoint:")
    result = _exec(ssh, "curl -s --max-time 5 http://127.0.0.1:5000/api/valuescan/token/status | head -c 200")
    print(result or "  (no response)")

    print("\nCheck NOFX page:")
    result = _exec(ssh, "curl -s --max-time 5 -o /dev/null -w '%{http_code}' http://127.0.0.1:80/nofx/ || echo 'N/A'")
    print(f"  HTTP status: {result}")


def main() -> None:
    host = os.environ.get("VALUESCAN_VPS_HOST", DEFAULT_HOST)
    user = os.environ.get("VALUESCAN_VPS_USER", DEFAULT_USER)
    password = _get_password()

    print("=" * 50)
    print("ValueScan + NOFX deploy script")
    print("=" * 50)
    print(f"Target: {user}@{host}")
    print(f"ValueScan dir: {VALUESCAN_DIR}")
    print(f"NOFX dir: {NOFX_DIR}")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs = {
        "hostname": host,
        "username": user,
        "timeout": 30,
    }
    if password:
        connect_kwargs["password"] = password

    print(f"\nConnecting to {user}@{host}...")
    try:
        _connect_ssh(ssh, connect_kwargs, host, user)
    except Exception as exc:
        raise SystemExit(f"SSH connection failed: {exc}")

    sftp = ssh.open_sftp()

    try:
        deploy_valuescan(ssh, sftp)
        deploy_nofx(ssh)
        configure_nginx(ssh)
        restart_services(ssh)
        verify_deployment(ssh)

        print("\n" + "=" * 50)
        print("Deploy finished")
        print("=" * 50)
        print("ValueScan: https://cornna.abrdns.com/")
        print("NOFX: https://cornna.abrdns.com/nofx/")
        print("\nEnv config:")
        print("  Option A: Use the frontend server-side env save card")
        print("  Option B: Write config/valuescan.env")
        print(f"    printf 'VALUESCAN_EMAIL=...\\nVALUESCAN_PASSWORD=...\\n' | sudo tee -a {VALUESCAN_DIR}/config/valuescan.env")
    finally:
        try:
            sftp.close()
        except Exception:
            pass
        ssh.close()


if __name__ == "__main__":
    main()
