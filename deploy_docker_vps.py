#!/usr/bin/env python3
"""
Deploy the Docker stack to a VPS.

Usage:
  python deploy_docker_vps.py --host 43.133.12.98 --user root --password "..." --domain cornna.abrdns.com
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Iterable


def _ensure_paramiko():
    try:
        import paramiko  # type: ignore
    except Exception:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko"])
        import paramiko  # type: ignore
    return paramiko


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deploy the Docker stack via Docker Compose.")
    parser.add_argument("--host", required=True, help="VPS IP or hostname")
    parser.add_argument("--user", required=True, help="SSH username")
    parser.add_argument("--password", required=True, help="SSH password")
    parser.add_argument("--port", type=int, default=22, help="SSH port")
    parser.add_argument("--remote-path", default="/root/nofx", help="Remote project root")
    parser.add_argument("--domain", default="", help="Optional domain to update Nginx proxy")
    parser.add_argument("--skip-nginx", action="store_true", help="Skip Nginx config update")
    parser.add_argument("--telegram-token", default="", help="Telegram bot token")
    parser.add_argument("--telegram-chat-id", default="", help="Telegram chat id")
    parser.add_argument("--enable-telegram", default="", help="Set NOFX_ENABLE_TELEGRAM (true/false)")
    return parser.parse_args()


def _remote_exists(sftp, path: str) -> bool:
    try:
        sftp.stat(path)
        return True
    except Exception:
        return False


def _sftp_mkdir_p(sftp, path: str) -> None:
    parts = [p for p in path.strip("/").split("/") if p]
    current = ""
    for part in parts:
        current = f"{current}/{part}" if current else f"/{part}"
        if not _remote_exists(sftp, current):
            sftp.mkdir(current)


def _iter_upload_paths(local_dir: Path, exclude_dirs: Iterable[str], exclude_files: Iterable[str]) -> Iterable[Path]:
    for root, dirs, files in os.walk(local_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for name in files:
            if name in exclude_files:
                continue
            if name.endswith(".pyc"):
                continue
            yield Path(root) / name


def _upload_dir(sftp, local_dir: Path, remote_dir: str) -> None:
    exclude_dirs = {".git", "__pycache__", "node_modules", "web/dist"}
    exclude_files = {".DS_Store"}
    for file_path in _iter_upload_paths(local_dir, exclude_dirs, exclude_files):
        rel = file_path.relative_to(local_dir)
        remote_path = f"{remote_dir}/{str(rel).replace(os.sep, '/')}"
        remote_parent = os.path.dirname(remote_path)
        _sftp_mkdir_p(sftp, remote_parent)
        sftp.put(str(file_path), remote_path)


def _exec(ssh, command: str) -> int:
    stdin, stdout, stderr = ssh.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()
    return exit_status


def _exec_output(ssh, command: str) -> str:
    stdin, stdout, stderr = ssh.exec_command(command)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return out or err


def _ensure_docker(ssh) -> None:
    if _exec(ssh, "docker --version") == 0 and _exec(ssh, "docker compose version") == 0:
        return
    _exec(ssh, "apt-get update")
    _exec(ssh, "apt-get install -y docker.io docker-compose-plugin")
    _exec(ssh, "systemctl enable --now docker")
    if _exec(ssh, "docker compose version") != 0:
        _exec(ssh, "apt-get install -y docker-compose")


def _resolve_compose_cmd(ssh) -> str:
    if _exec(ssh, "docker compose version") == 0:
        return "docker compose"
    if _exec(ssh, "docker-compose --version") == 0:
        return "DOCKER_HOST=unix:///var/run/docker.sock docker-compose"
    return "DOCKER_HOST=unix:///var/run/docker.sock docker-compose"


def _stop_legacy_services(ssh) -> None:
    _exec(ssh, "systemctl stop signal-api signal-monitor || true")
    _exec(ssh, "systemctl disable signal-api signal-monitor || true")
    _exec(ssh, "rm -f /etc/systemd/system/signal-api.service /etc/systemd/system/signal-monitor.service")
    _exec(ssh, "systemctl daemon-reload")


def _read_remote_env(ssh, env_path: str) -> dict:
    raw = _exec_output(ssh, f"cat {env_path} 2>/dev/null || true")
    data = {}
    for line in raw.splitlines():
        if not line or line.strip().startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        data[key.strip()] = value.strip()
    return data


def _ensure_remote_env_keys(ssh, env_path: str, values: dict) -> dict:
    current = _read_remote_env(ssh, env_path)
    missing = {k: v for k, v in values.items() if not current.get(k)}
    if not missing:
        return current
    lines = "\n".join(f"{k}={v}" for k, v in missing.items())
    _exec(ssh, f"bash -lc 'cat >> {env_path} <<\"EOF\"\n{lines}\nEOF'")
    current.update(missing)
    return current


def _set_remote_env_values(ssh, env_path: str, values: dict) -> None:
    for key, value in values.items():
        safe_value = str(value).replace('"', '\\"')
        cmd = (
            f"bash -lc 'if grep -q \"^{key}=\" {env_path}; then "
            f"sed -i \"s|^{key}=.*|{key}={safe_value}|\" {env_path}; "
            f"else echo \"{key}={safe_value}\" >> {env_path}; fi'"
        )
        _exec(ssh, cmd)


def _update_nginx(ssh, domain: str, backend_port: str, frontend_port: str) -> None:
    if not domain:
        return
    ssl_cert = f"/etc/nginx/ssl/{domain}.crt"
    ssl_key = f"/etc/nginx/ssl/{domain}.key"
    config_lines = [
        "server {",
        "    listen 80;",
        f"    server_name {domain};",
        "    return 301 https://$server_name$request_uri;",
        "}",
        "",
        "server {",
        "    listen 443 ssl http2;",
        f"    server_name {domain};",
        "",
        f"    ssl_certificate {ssl_cert};",
        f"    ssl_certificate_key {ssl_key};",
        "    ssl_protocols TLSv1.2 TLSv1.3;",
        "",
        "    charset utf-8;",
        "",
        "    location /api/ {",
        f"        proxy_pass http://127.0.0.1:{backend_port};",
        "        proxy_set_header Host $host;",
        "        proxy_set_header X-Real-IP $remote_addr;",
        "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
        "        proxy_set_header X-Forwarded-Proto $scheme;",
        "    }",
        "",
        "    location / {",
        f"        proxy_pass http://127.0.0.1:{frontend_port};",
        "        proxy_set_header Host $host;",
        "        proxy_set_header X-Real-IP $remote_addr;",
        "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
        "        proxy_set_header X-Forwarded-Proto $scheme;",
        "    }",
        "}",
        "",
    ]
    config = "\n".join(config_lines)
    _exec(ssh, f"bash -lc 'cat > /etc/nginx/sites-available/nofx <<\"EOF\"\n{config}\nEOF'")
    _exec(ssh, "ln -sf /etc/nginx/sites-available/nofx /etc/nginx/sites-enabled/nofx")
    _exec(ssh, "nginx -t")
    _exec(ssh, "systemctl reload nginx")


def main() -> int:
    args = _parse_args()
    paramiko = _ensure_paramiko()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        args.host,
        username=args.user,
        password=args.password,
        port=args.port,
        timeout=20,
    )

    _ensure_docker(client)

    sftp = client.open_sftp()
    _sftp_mkdir_p(sftp, args.remote_path)

    repo_root = Path(__file__).resolve().parent
    _upload_dir(sftp, repo_root / "api", f"{args.remote_path}/api")
    _upload_dir(sftp, repo_root / "signal_monitor", f"{args.remote_path}/signal_monitor")
    _upload_dir(sftp, repo_root / "web", f"{args.remote_path}/web")
    _upload_dir(sftp, repo_root / "docker", f"{args.remote_path}/docker")

    for name in ("docker-compose.yml", ".env.example", "logger.py", "sitecustomize.py"):
        local_path = repo_root / name
        if local_path.exists():
            remote_path = f"{args.remote_path}/{name}"
            _sftp_mkdir_p(sftp, os.path.dirname(remote_path))
            sftp.put(str(local_path), remote_path)

    sftp.close()

    _stop_legacy_services(client)

    env_path = f"{args.remote_path}/.env"
    env = _read_remote_env(client, env_path)
    if not env:
        _exec(client, f"cp {args.remote_path}/.env.example {env_path}")
        env = _read_remote_env(client, env_path)

    env_updates = {
        "NOFX_LOG_FILE": "data/signal_monitor.log",
        "NOFX_API_LOG_FILE": "data/api.log",
    }
    if args.telegram_token:
        env_updates["NOFX_TELEGRAM_BOT_TOKEN"] = args.telegram_token
    if args.telegram_chat_id:
        env_updates["NOFX_TELEGRAM_CHAT_ID"] = args.telegram_chat_id
    if args.enable_telegram:
        env_updates["NOFX_ENABLE_TELEGRAM"] = args.enable_telegram

    env = _ensure_remote_env_keys(client, env_path, env_updates)
    if env_updates:
        _set_remote_env_values(client, env_path, env_updates)
    _set_remote_env_values(
        client,
        env_path,
        {
            "NOFX_REALTIME_MARKET_ENABLED": "true",
            "NOFX_ENABLE_AI_KEY_LEVELS": "true",
            "NOFX_AI_LEVELS_ENABLED": "1",
            "NOFX_AI_LEVELS_MODEL": "valuescan",
        },
    )

    backend_port = env.get("NOFX_BACKEND_PORT", "8080")
    frontend_port = env.get("NOFX_FRONTEND_PORT", "3000")

    if not args.skip_nginx:
        _update_nginx(client, args.domain, backend_port, frontend_port)

    compose_cmd = _resolve_compose_cmd(client)
    _exec(client, f"bash -lc 'cd {args.remote_path} && {compose_cmd} build'")
    _exec(client, f"bash -lc 'cd {args.remote_path} && {compose_cmd} up -d --force-recreate'")

    client.close()
    print("[deploy] Docker stack deployed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
