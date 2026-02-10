#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy the entire repo to VPS after wiping the remote project directory.
"""
from __future__ import annotations

import os
import shutil
import tarfile
import tempfile
import time
from pathlib import Path
from typing import Iterable

import paramiko


DEFAULT_HOST = "43.128.227.29"
DEFAULT_USER = "root"
DEFAULT_PORT = 22
DEFAULT_REMOTE_PATH = "/root/valuescan"
DEFAULT_FRONTEND_ROOT = "/var/www/valuescan"
DEFAULT_DOMAIN = "cornna.abrdns.com"
DEFAULT_SSL_DIR = "/etc/nginx/ssl"

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
}


def should_skip(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return True
    for part in rel.parts:
        if part in EXCLUDE_DIRS:
            return True
    return False


def iter_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for filename in filenames:
            path = Path(dirpath) / filename
            if should_skip(path, root):
                continue
            yield path


def exec_ssh(ssh: paramiko.SSHClient, cmd: str) -> None:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    stdout.channel.recv_exit_status()
    out = stdout.read().decode(errors="ignore").strip()
    err = stderr.read().decode(errors="ignore").strip()
    if out:
        print(out)
    if err:
        print(err)


def build_tarball(local_root: Path) -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="valuescan-deploy-"))
    tar_path = temp_dir / "valuescan_deploy.tar.gz"
    with tarfile.open(tar_path, "w:gz", compresslevel=6) as tar:
        for local_file in iter_files(local_root):
            rel = local_file.relative_to(local_root).as_posix()
            tar.add(local_file, arcname=rel)
    return tar_path


def build_nginx_conf(domain: str, frontend_root: str, ssl_dir: str) -> str:
    cert_path = f"{ssl_dir}/{domain}/cert.pem"
    key_path = f"{ssl_dir}/{domain}/key.pem"
    return f"""server {{
    listen 80;
    server_name {domain};
    return 301 https://$server_name$request_uri;
}}

server {{
    listen 443 ssl http2;
    server_name {domain};

    root {frontend_root};
    index index.html;

    ssl_certificate {cert_path};
    ssl_certificate_key {key_path};
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/javascript application/json;

    location / {{
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }}

    location /assets/ {{
        expires 1y;
        add_header Cache-Control "public, immutable";
    }}

    location /api/ {{
        proxy_pass http://127.0.0.1:5000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }}

    location /clash-api/ {{
        if ($request_method = OPTIONS) {{
            add_header Access-Control-Allow-Origin "*" always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, PATCH, DELETE, OPTIONS" always;
            add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;
            add_header Access-Control-Max-Age 86400 always;
            return 204;
        }}

        proxy_pass http://127.0.0.1:9090/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header Authorization $http_authorization;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, PATCH, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;

        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }}

    location /health {{
        return 200 "OK\\n";
        add_header Content-Type text/plain;
        access_log off;
    }}
}}
"""


def main() -> None:
    host = os.getenv("VALUESCAN_VPS_HOST", DEFAULT_HOST)
    user = os.getenv("VALUESCAN_VPS_USER", DEFAULT_USER)
    port = int(os.getenv("VALUESCAN_VPS_PORT", str(DEFAULT_PORT)))
    remote_path = os.getenv("VALUESCAN_VPS_PATH", DEFAULT_REMOTE_PATH).rstrip("/")
    frontend_root = os.getenv("VALUESCAN_VPS_FRONTEND_ROOT", DEFAULT_FRONTEND_ROOT).rstrip("/")
    domain = os.getenv("VALUESCAN_VPS_DOMAIN", DEFAULT_DOMAIN).strip()
    ssl_dir = os.getenv("VALUESCAN_VPS_SSL_DIR", DEFAULT_SSL_DIR).rstrip("/")
    install_deps = os.getenv("VALUESCAN_VPS_INSTALL_DEPS", "1").strip() == "1"
    password = os.getenv("VALUESCAN_VPS_PASSWORD", "").strip()

    if not password:
        raise SystemExit("Missing VALUESCAN_VPS_PASSWORD env var.")

    if not remote_path or remote_path in {"/", "/root"}:
        raise SystemExit(f"Unsafe remote path: {remote_path}")
    if not frontend_root or frontend_root in {"/", "/var", "/var/www"}:
        raise SystemExit(f"Unsafe frontend path: {frontend_root}")

    local_root = Path(__file__).resolve().parents[1]
    print(f"Deploying from: {local_root}")
    print(f"Target: {user}@{host}:{port}{remote_path}")
    print(f"Domain: {domain}")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname=host,
        port=port,
        username=user,
        password=password,
        timeout=60,
        banner_timeout=60,
        auth_timeout=60,
    )
    transport = ssh.get_transport()
    if transport:
        transport.set_keepalive(30)

    print("Stopping services...")
    exec_ssh(
        ssh,
        "systemctl stop valuescan-api valuescan-monitor valuescan-token-refresher "
        "valuescan-keepalive valuescan-signal 2>/dev/null || true",
    )

    print("Building deploy archive...")
    tar_path = build_tarball(local_root)
    remote_tar = f"/tmp/valuescan_deploy_{int(time.time())}.tar.gz"

    print(f"Uploading archive to {remote_tar}...")
    sftp = ssh.open_sftp()
    sftp.put(str(tar_path), remote_tar)
    sftp.close()
    shutil.rmtree(tar_path.parent, ignore_errors=True)

    print(f"Removing remote path: {remote_path}")
    exec_ssh(ssh, f"rm -rf {remote_path} && mkdir -p {remote_path}")
    exec_ssh(ssh, f"tar -xzf {remote_tar} -C {remote_path}")
    exec_ssh(ssh, f"rm -f {remote_tar}")

    if install_deps:
        print("Installing Python dependencies...")
        exec_ssh(ssh, "python3 -m pip install --upgrade pip --break-system-packages")
        exec_ssh(ssh, f"python3 -m pip install --break-system-packages -r {remote_path}/api/requirements.txt")
        exec_ssh(ssh, f"python3 -m pip install --break-system-packages -r {remote_path}/signal_monitor/requirements.txt")

    print("Installing systemd services...")
    service_files = [
        "valuescan-api.service",
        "valuescan-monitor.service",
        "valuescan-token-refresher.service",
        "valuescan-keepalive.service",
    ]
    for svc in service_files:
        exec_ssh(ssh, f"cp -f {remote_path}/{svc} /etc/systemd/system/{svc}")
    exec_ssh(ssh, "systemctl daemon-reload")
    exec_ssh(ssh, "systemctl enable valuescan-api valuescan-monitor valuescan-token-refresher valuescan-keepalive 2>/dev/null || true")

    print(f"Updating frontend at {frontend_root}...")
    exec_ssh(ssh, f"mkdir -p {frontend_root}")
    exec_ssh(ssh, f"rm -rf {frontend_root}/*")
    exec_ssh(ssh, f"cp -r {remote_path}/web/dist/* {frontend_root}/")

    print("Updating nginx config...")
    nginx_conf = build_nginx_conf(domain, frontend_root, ssl_dir)
    remote_conf = f"/etc/nginx/sites-available/valuescan"
    exec_ssh(ssh, f"cat > {remote_conf} << 'EOF'\n{nginx_conf}\nEOF")
    exec_ssh(ssh, "rm -f /etc/nginx/sites-enabled/frequi-ai 2>/dev/null || true")
    exec_ssh(ssh, "ln -sf /etc/nginx/sites-available/valuescan /etc/nginx/sites-enabled/valuescan")
    exec_ssh(ssh, "nginx -t")
    exec_ssh(ssh, "systemctl restart nginx 2>/dev/null || true")

    print("Restarting services...")
    exec_ssh(
        ssh,
        "systemctl restart valuescan-api valuescan-monitor valuescan-token-refresher "
        "valuescan-keepalive 2>/dev/null || true",
    )

    ssh.close()
    print("Deployment complete.")


if __name__ == "__main__":
    main()
