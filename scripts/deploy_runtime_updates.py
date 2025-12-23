#!/usr/bin/env python3
"""
Deploy runtime fixes to the ValueScan VPS.

Uploads:
- api/server.py
- api/performance_db.py
- ai_trading/api/routes.py
- ai_trading/engine/market_analyzer.py
- ai_trading/llm/api_routes.py
- ai_trading/llm/client.py
- ai_trading/llm/config.py
- ai_trading/llm/adapters/base.py
- ai_trading/tuning/database.py
- binance_trader/futures_trader.py
- binance_trader/trailing_stop.py
- binance_trader/config.example.py
- simulation/api_routes.py
- signal_monitor/database.py
- web/dist (to /root/valuescan/web/dist and optionally /opt/valuescan/web/dist)
- web/nofx_dist (to /root/valuescan/web/nofx_dist)
- web/nofx_root_dist (to /opt/nofx/web/dist when present)

Restarts:
- valuescan-api
- valuescan-signal
- valuescan-trader

Credentials (recommended via env vars):
- VALUESCAN_VPS_HOST (default: 82.158.88.34)
- VALUESCAN_VPS_USER (default: root)
- VALUESCAN_VPS_PASSWORD (required; fallback attempts to parse local deploy scripts)
"""

from __future__ import annotations

import os
import re
import socket
import sys
import time
import getpass
from pathlib import Path

import paramiko
from paramiko.ssh_exception import AuthenticationException, BadAuthenticationType


DEFAULT_HOST = "82.158.88.34"
DEFAULT_USER = "root"
DEFAULT_PROJECT_ROOT = "/root/valuescan"
DEFAULT_WEB_MIRROR_ROOT = "/opt/valuescan/web/dist"
DEFAULT_OPT_ROOT = "/opt/valuescan"
DEFAULT_NGINX_DOMAIN_CONF = "/etc/nginx/conf.d/cornna.abrdns.com.conf"


def _resolve_key_file() -> str:
    env_path = (os.environ.get("VALUESCAN_VPS_KEY_FILE") or "").strip()
    if env_path:
        return env_path

    default_path = Path.home() / ".ssh" / "valuescan_vps"
    if default_path.exists():
        return str(default_path)

    return ""


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _get_password() -> str | None:
    password = os.environ.get("VALUESCAN_VPS_PASSWORD", "")
    if password:
        return password

    print("VALUESCAN_VPS_PASSWORD not found. Attempting SSH key-based authentication...")
    return None


def _prompt_password(host: str, user: str) -> str | None:
    if not sys.stdin.isatty():
        return None
    try:
        pw = getpass.getpass(f"Enter SSH password for {user}@{host}: ")
    except Exception:
        return None
    pw = (pw or "").strip()
    return pw or None


def _connect_ssh(ssh: paramiko.SSHClient, connect_kwargs: dict, host: str, user: str) -> None:
    try:
        ssh.connect(**connect_kwargs)
        return
    except BadAuthenticationType as exc:
        allowed = getattr(exc, "allowed_types", None) or []
        if "password" in allowed and not connect_kwargs.get("password"):
            pw = _prompt_password(host, user)
            if pw:
                connect_kwargs.pop("key_filename", None)
                connect_kwargs["password"] = pw
                ssh.connect(**connect_kwargs)
                return
        raise
    except AuthenticationException:
        if not connect_kwargs.get("password"):
            pw = _prompt_password(host, user)
            if pw:
                connect_kwargs.pop("key_filename", None)
                connect_kwargs["password"] = pw
                ssh.connect(**connect_kwargs)
                return
        raise


def _exec(ssh: paramiko.SSHClient, cmd: str, timeout: int = 120) -> str:
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

def _sftp_read_text(sftp: paramiko.SFTPClient, remote_path: str) -> str:
    try:
        with sftp.open(remote_path, "rb") as fh:
            data = fh.read()
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _read_remote_auto_trading_enabled(
    sftp: paramiko.SFTPClient,
    project_root: str,
) -> Optional[bool]:
    config_path = f"{project_root}/binance_trader/config.py"
    content = _sftp_read_text(sftp, config_path)
    if not content:
        return None
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("AUTO_TRADING_ENABLED"):
            parts = line.split("=", 1)
            if len(parts) != 2:
                return None
            value = parts[1].strip().split("#", 1)[0].strip()
            if value.lower() == "true":
                return True
            if value.lower() == "false":
                return False
            return None
    return None


def _sftp_write_text(sftp: paramiko.SFTPClient, remote_path: str, content: str) -> None:
    with sftp.open(remote_path, "wb") as fh:
        fh.write(content.encode("utf-8"))


def _split_nginx_server_blocks(conf_text: str) -> list[tuple[int, int, str]]:
    """
    Very small nginx conf parser: returns [(start_idx, end_idx, block_text), ...] for `server { ... }`.
    Assumes braces are balanced within each server block.
    """
    blocks: list[tuple[int, int, str]] = []
    text = conf_text or ""
    idx = 0
    n = len(text)
    while idx < n:
        start = text.find("server", idx)
        if start == -1:
            break
        brace = text.find("{", start)
        if brace == -1:
            break
        # ensure "server" token and "{" are close enough
        header = text[start:brace].strip()
        if not header.startswith("server"):
            idx = brace + 1
            continue
        depth = 0
        i = brace
        while i < n:
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    blocks.append((start, end, text[start:end]))
                    idx = end
                    break
            i += 1
        else:
            break
    return blocks


def _ensure_locations_in_ssl_server(conf_text: str, *, server_name: str) -> tuple[str, bool]:
    """
    Ensure `/nofx` + `/socket.io/` are proxied in the HTTPS server block for `server_name`.
    Returns (new_text, changed).
    """
    if not conf_text.strip():
        return conf_text, False

    blocks = _split_nginx_server_blocks(conf_text)
    if not blocks:
        return conf_text, False

    changed = False
    out = conf_text

    for start, end, block in reversed(blocks):
        if f"server_name {server_name};" not in block:
            continue
        if "listen 443" not in block:
            continue

        nofx_pattern = re.compile(r"\blocation\s+(?:\^~\s+|=\s+)?/nofx/?\s*\{")
        socket_pattern = re.compile(r"\blocation\s+(?:\^~\s+|=\s+)?/socket\.io/\s*\{")
        need_nofx = not nofx_pattern.search(block)
        need_socket = not socket_pattern.search(block)
        if not (need_nofx or need_socket):
            continue

        insert_at = block.rfind("location /")
        if insert_at == -1:
            insert_at = block.rfind("}")
        if insert_at == -1:
            continue

        snippet = ""
        if need_nofx:
            snippet += (
                "\n"
                "    location = /nofx {\n"
                "        proxy_pass http://127.0.0.1:5000;\n"
                "        proxy_set_header Host $host;\n"
                "        proxy_set_header X-Real-IP $remote_addr;\n"
                "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
                "        proxy_set_header X-Forwarded-Proto $scheme;\n"
                "        proxy_connect_timeout 60s;\n"
                "        proxy_send_timeout 600s;\n"
                "        proxy_read_timeout 600s;\n"
                "    }\n"
                "\n"
                "    location ^~ /nofx/ {\n"
                "        proxy_pass http://127.0.0.1:5000;\n"
                "        proxy_set_header Host $host;\n"
                "        proxy_set_header X-Real-IP $remote_addr;\n"
                "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
                "        proxy_set_header X-Forwarded-Proto $scheme;\n"
                "        proxy_connect_timeout 60s;\n"
                "        proxy_send_timeout 600s;\n"
                "        proxy_read_timeout 600s;\n"
                "    }\n"
            )
        if need_socket:
            snippet += (
                "\n"
                "    location /socket.io/ {\n"
                "        proxy_pass http://127.0.0.1:5000;\n"
                "        proxy_http_version 1.1;\n"
                "        proxy_set_header Upgrade $http_upgrade;\n"
                "        proxy_set_header Connection \"upgrade\";\n"
                "        proxy_set_header Host $host;\n"
                "        proxy_read_timeout 600s;\n"
                "    }\n"
            )

        new_block = block[:insert_at] + snippet + block[insert_at:]
        out = out[:start] + new_block + out[end:]
        changed = True

    return out, changed


def _sync_dist(ssh: paramiko.SSHClient, sftp: paramiko.SFTPClient, local_dist: Path, remote_dist: str) -> None:
    if not local_dist.exists():
        raise SystemExit(f"Local dist not found: {local_dist}")

    _exec(ssh, f"mkdir -p {remote_dist} && rm -rf {remote_dist}/*", timeout=120)

    for path in local_dist.rglob("*"):
        if path.is_dir():
            continue
        rel = path.relative_to(local_dist).as_posix()
        remote_path = f"{remote_dist}/{rel}"
        _sftp_put_mkdir(sftp, path, remote_path)


def _maybe_build_web_dist() -> None:
    """
    Best-effort local build of `web/dist` before upload.

    Enabled when:
      - VALUESCAN_BUILD_WEB=1  (explicit)
      - OR `web/src` is newer than `web/dist/index.html`
    """
    web_dir = Path("web")
    dist_index = web_dir / "dist" / "index.html"
    src_dir = web_dir / "src"

    if not web_dir.exists() or not src_dir.exists():
        return

    want = (os.getenv("VALUESCAN_BUILD_WEB") or "").strip() in ("1", "true", "yes", "on")
    if not want and dist_index.exists():
        try:
            latest_src = max((p.stat().st_mtime for p in src_dir.rglob("*") if p.is_file()), default=0)
            if dist_index.stat().st_mtime >= latest_src:
                return
        except Exception:
            return

    print("Building web dist (best-effort)...")
    try:
        import subprocess

        subprocess.run(["npm", "run", "build"], cwd=str(web_dir), check=True, timeout=900)
    except Exception as exc:
        print(f"Web build skipped/failed: {exc}")


def _sync_tree(
    ssh: paramiko.SSHClient,
    sftp: paramiko.SFTPClient,
    local_root: Path,
    remote_root: str,
    *,
    glob_pattern: str = "*",
) -> None:
    if not local_root.exists():
        print(f"SKIP missing local path: {local_root}")
        return
    if local_root.is_file():
        _sftp_put_mkdir(sftp, local_root, remote_root)
        return

    _exec(ssh, f"mkdir -p {remote_root}", timeout=120)
    for path in local_root.rglob(glob_pattern):
        if path.is_dir():
            continue
        rel = path.relative_to(local_root).as_posix()
        remote_path = f"{remote_root}/{rel}"
        _sftp_put_mkdir(sftp, path, remote_path)


def _install_requirements(ssh: paramiko.SSHClient, project_root: str) -> str:
    cmd = (
        f"cd {project_root} && "
        "if [ -f requirements.txt ]; then "
        "if command -v python3 >/dev/null 2>&1; then python3 -m pip install -r requirements.txt; "
        "elif command -v python3.9 >/dev/null 2>&1; then python3.9 -m pip install -r requirements.txt; "
        "elif command -v pip3 >/dev/null 2>&1; then pip3 install -r requirements.txt; "
        "elif command -v pip >/dev/null 2>&1; then pip install -r requirements.txt; "
        "else echo 'pip not found; skip requirements install.'; fi; "
        "else echo 'requirements.txt not found; skip requirements install.'; fi"
    )
    return _exec(ssh, cmd, timeout=900)


def _configure_nginx(ssh: paramiko.SSHClient, web_root: str, server_name: str) -> None:
    """
    Configure nginx to serve the SPA and proxy /api + websocket endpoints.

    Notes:
    - Many VPS images ship nginx "test page" as the default_server.
    - We remove any existing `default_server` keywords to avoid conflicts, then
      install our own default server block.
    """
    nginx_dir = "/etc/nginx"
    conf_dir = f"{nginx_dir}/conf.d"
    remote_conf = f"{conf_dir}/valuescan.conf"

    print("Configuring nginx (best-effort)...")
    print(_exec(ssh, f"test -d {nginx_dir} && echo OK || echo NO", timeout=30))
    print(_exec(ssh, f"test -d {conf_dir} && echo OK || echo NO", timeout=30))

    # Remove default_server flags to avoid "duplicate default_server" errors.
    print(_exec(
        ssh,
        "set -e; "
        "FILES=$(grep -R -l \"default_server\" /etc/nginx "
        "  --exclude='*.bak.valuescan*' --exclude-dir='*.bak.valuescan*' 2>/dev/null || true); "
        "for f in $FILES; do "
        "  cp -n \"$f\" \"$f.bak.valuescan\" 2>/dev/null || true; "
        "  sed -i 's/\\s*default_server\\b//g' \"$f\" 2>/dev/null || true; "
        "done; "
        "echo \"default_server removed where found\"",
        timeout=120,
    ))

    server_name = (server_name or "").strip() or "_"

    nginx_conf = f"""server {{
    listen 80;
    listen [::]:80;
    server_name {server_name};

    root {web_root};
    index index.html;

    # NOFX UI is served by the Flask backend at /nofx (static files from /root/valuescan/web/nofx_dist).
    # Without this block, nginx would serve the main SPA index.html for /nofx and the mount would fail.
    location = /nofx {{
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }}

    location ^~ /nofx/ {{
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }}

    location /api/ {{
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }}

    location /socket.io/ {{
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 600s;
    }}

    location / {{
        try_files $uri $uri/ /index.html;
    }}
}}
"""

    cmd = f"mkdir -p {conf_dir} && cat > {remote_conf} <<'EOF'\n{nginx_conf}\nEOF\nnginx -t"
    print(_exec(ssh, cmd, timeout=120))

    print(_exec(
        ssh,
        "systemctl reload nginx 2>/dev/null || systemctl restart nginx 2>/dev/null || true",
        timeout=60,
    ))


def _patch_domain_nginx_conf(
    ssh: paramiko.SSHClient,
    sftp: paramiko.SFTPClient,
    *,
    conf_path: str,
    server_name: str,
) -> None:
    """
    Patch the HTTPS domain server block to proxy /nofx and /socket.io/ when missing.
    This keeps existing SSL directives intact (no regeneration).
    """
    conf_path = (conf_path or "").strip()
    server_name = (server_name or "").strip()
    if not conf_path or not server_name:
        return

    current = _sftp_read_text(sftp, conf_path)
    if not current.strip():
        return

    patched, changed = _ensure_locations_in_ssl_server(current, server_name=server_name)
    if not changed:
        return

    bak = conf_path + ".bak.valuescan"
    print(_exec(ssh, f"test -f {bak} || cp -n {conf_path} {bak} 2>/dev/null || true", timeout=20))
    _sftp_write_text(sftp, conf_path, patched)
    print(_exec(ssh, "nginx -t", timeout=60))
    print(_exec(ssh, "systemctl reload nginx 2>/dev/null || true", timeout=60))


def main() -> None:
    host = os.environ.get("VALUESCAN_VPS_HOST", DEFAULT_HOST)
    user = os.environ.get("VALUESCAN_VPS_USER", DEFAULT_USER)
    project_root = os.environ.get("VALUESCAN_VPS_PROJECT_ROOT", DEFAULT_PROJECT_ROOT)
    web_mirror_root = os.environ.get("VALUESCAN_VPS_WEB_MIRROR_ROOT", DEFAULT_WEB_MIRROR_ROOT)
    opt_root = os.environ.get("VALUESCAN_VPS_OPT_ROOT", DEFAULT_OPT_ROOT)
    domain_conf = os.environ.get("VALUESCAN_NGINX_DOMAIN_CONF", DEFAULT_NGINX_DOMAIN_CONF)
    domain_name = os.environ.get("VALUESCAN_NGINX_DOMAIN", "cornna.abrdns.com").strip()
    proxy_subscribe_url = (
        os.environ.get("PROXY_SUBSCRIBE_URL")
        or os.environ.get("VALUESCAN_PROXY_SUBSCRIBE_URL")
        or ""
    ).strip()

    password = _get_password()
    key_file = _resolve_key_file()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {user}@{host} ...")
    
    connect_kwargs = {
        "hostname": host,
        "username": user,
        "timeout": 30
    }
    if password:
        connect_kwargs["password"] = password
    elif key_file:
        connect_kwargs["key_filename"] = key_file
        
    try:
        _connect_ssh(ssh, connect_kwargs, host, user)
    except Exception as exc:
        raise SystemExit(
            "SSH connect failed. Set env var VALUESCAN_VPS_PASSWORD or VALUESCAN_VPS_KEY_FILE and retry. "
            f"Underlying error: {exc}"
        )
    sftp = ssh.open_sftp()

    try:
        print("Uploading runtime files...")
        file_uploads = [
            (Path("requirements.txt"), f"{project_root}/requirements.txt"),
            (Path("LICENSE"), f"{project_root}/LICENSE"),
            (Path("THIRD_PARTY_NOTICES.md"), f"{project_root}/THIRD_PARTY_NOTICES.md"),
            # systemd unit templates (installed to /etc/systemd/system below)
            (Path("valuescan-api.service"), f"{project_root}/valuescan-api.service"),
            (Path("valuescan-signal.service"), f"{project_root}/valuescan-signal.service"),
            (Path("valuescan-trader.service"), f"{project_root}/valuescan-trader.service"),
            (Path("proxy-checker.service"), f"{project_root}/proxy-checker.service"),
            (Path("scripts/valuescan-token-refresher.service"), f"{project_root}/valuescan-token-refresher.service"),
            (Path("api/server.py"), f"{project_root}/api/server.py"),
            (Path("api/nofx_compat.py"), f"{project_root}/api/nofx_compat.py"),
            # Binance trader module - core trading files
            (Path("binance_trader/futures_main.py"), f"{project_root}/binance_trader/futures_main.py"),
            (Path("binance_trader/futures_trader.py"), f"{project_root}/binance_trader/futures_trader.py"),
            (Path("binance_trader/trailing_stop.py"), f"{project_root}/binance_trader/trailing_stop.py"),
            (Path("binance_trader/trading_signal_processor.py"), f"{project_root}/binance_trader/trading_signal_processor.py"),
            (Path("binance_trader/signal_aggregator.py"), f"{project_root}/binance_trader/signal_aggregator.py"),
            (Path("binance_trader/risk_manager.py"), f"{project_root}/binance_trader/risk_manager.py"),
            (Path("binance_trader/config.example.py"), f"{project_root}/binance_trader/config.example.py"),
            (Path("binance_trader/__init__.py"), f"{project_root}/binance_trader/__init__.py"),
            # Signal monitor module
            (Path("signal_monitor/movement_list_cache.py"), f"{project_root}/signal_monitor/movement_list_cache.py"),
            (Path("signal_monitor/api_monitor.py"), f"{project_root}/signal_monitor/api_monitor.py"),
            (Path("signal_monitor/http_api_login.py"), f"{project_root}/signal_monitor/http_api_login.py"),
            (Path("signal_monitor/http_login.py"), f"{project_root}/signal_monitor/http_login.py"),
            (Path("signal_monitor/start_polling.py"), f"{project_root}/signal_monitor/start_polling.py"),
            (Path("signal_monitor/polling_monitor.py"), f"{project_root}/signal_monitor/polling_monitor.py"),
            # Scripts
            (Path("scripts/valuescan_futures_bridge.py"), f"{project_root}/scripts/valuescan_futures_bridge.py"),
            (Path("scripts/build_nofx_dev_web.sh"), f"{project_root}/scripts/build_nofx_dev_web.sh"),
            # Sync script
            (Path("sync_to_remote.py"), f"{project_root}/sync_to_remote.py"),
            # IPC config
            (Path("ipc_config.py"), f"{project_root}/ipc_config.py"),
            # Trader compatibility entrypoint
            (Path("binance_trader/ipc_server.py"), f"{project_root}/binance_trader/ipc_server.py"),
            # Proxy manager
            (Path("proxy_manager/node_checker.py"), f"{project_root}/proxy_manager/node_checker.py"),
            (Path("api/performance_db.py"), f"{project_root}/api/performance_db.py"),
            (Path("ai_trading/api/routes.py"), f"{project_root}/ai_trading/api/routes.py"),
            (Path("ai_trading/engine/market_analyzer.py"), f"{project_root}/ai_trading/engine/market_analyzer.py"),
            (Path("ai_trading/llm/api_routes.py"), f"{project_root}/ai_trading/llm/api_routes.py"),
            (Path("ai_trading/llm/client.py"), f"{project_root}/ai_trading/llm/client.py"),
            (Path("ai_trading/llm/config.py"), f"{project_root}/ai_trading/llm/config.py"),
            (Path("ai_trading/llm/adapters/base.py"), f"{project_root}/ai_trading/llm/adapters/base.py"),
            (Path("ai_trading/llm/adapters/openai_compatible_adapter.py"), f"{project_root}/ai_trading/llm/adapters/openai_compatible_adapter.py"),
            # Runtime helper scripts live in /opt on the VPS
            (Path("token_refresher.py"), f"{opt_root}/token_refresher.py"),
        ]

        for local, remote in file_uploads:
            if local.exists():
                _sftp_put_mkdir(sftp, local, remote)
                print(f"  OK {local} -> {remote}")
            else:
                print(f"  SKIP missing local file: {local}")

        if proxy_subscribe_url:
            escaped = proxy_subscribe_url.replace("'", "'\"'\"'")
            print(
                _exec(
                    ssh,
                    "set -e; "
                    "mkdir -p /etc/valuescan && "
                    f"printf '%s' '{escaped}' > /etc/valuescan/proxy_subscribe_url && "
                    "chmod 600 /etc/valuescan/proxy_subscribe_url",
                    timeout=20,
                )
            )
        else:
            print("PROXY_SUBSCRIBE_URL not provided; skip proxy subscription update.")

        _sync_tree(
            ssh,
            sftp,
            Path("ai_trading/exchanges"),
            f"{project_root}/ai_trading/exchanges",
            glob_pattern="*.py",
        )
        _sync_tree(
            ssh,
            sftp,
            Path("ai_trading/llm/adapters"),
            f"{project_root}/ai_trading/llm/adapters",
            glob_pattern="*.py",
        )
        print("  OK synced packages: ai_trading/exchanges, ai_trading/llm/adapters")

        print("Uploading web dist...")
        _maybe_build_web_dist()
        local_dist = Path("web/dist")
        _sync_dist(ssh, sftp, local_dist, f"{project_root}/web/dist")
        print(f"  OK {local_dist} -> {project_root}/web/dist")

        local_nofx_dist = Path("web/nofx_dist")
        if local_nofx_dist.exists():
            print("Uploading NOFX dist...")
            _sync_dist(ssh, sftp, local_nofx_dist, f"{project_root}/web/nofx_dist")
            print(f"  OK {local_nofx_dist} -> {project_root}/web/nofx_dist")
        else:
            print("NOFX dist not found (web/nofx_dist). Skip upload.")

        nofx_root_remote = "/opt/nofx/web/dist"
        try:
            nofx_root_exists = _exec(
                ssh, f"test -d {nofx_root_remote} && echo OK || echo NO", timeout=30
            ).strip() == "OK"
        except Exception:
            nofx_root_exists = False

        local_nofx_root_dist = Path("web/nofx_root_dist")
        if nofx_root_exists:
            if local_nofx_root_dist.exists():
                print("Uploading NOFX root dist...")
                _sync_dist(ssh, sftp, local_nofx_root_dist, nofx_root_remote)
                print(f"  OK {local_nofx_root_dist} -> {nofx_root_remote}")
            else:
                print("NOFX root dist not found (web/nofx_root_dist). Skip upload.")

        # Mirror dist to /opt tree if present (some deployments use nginx/static there).
        mirror_exists = True
        try:
            _exec(ssh, f"test -d {web_mirror_root} && echo OK || echo NO", timeout=30)
        except Exception:
            mirror_exists = False

        if mirror_exists:
            _sync_dist(ssh, sftp, local_dist, web_mirror_root)
            print(f"  OK {local_dist} -> {web_mirror_root}")

        _configure_nginx(ssh, web_mirror_root, host)
        _patch_domain_nginx_conf(ssh, sftp, conf_path=domain_conf, server_name=domain_name)

        print("Installing/Updating Python dependencies...")
        print(_install_requirements(ssh, project_root))

        print("Installing systemd unit files (best-effort)...")
        for unit_name in (
            "valuescan-api.service",
            "valuescan-signal.service",
            "valuescan-trader.service",
            "proxy-checker.service",
            "valuescan-token-refresher.service",
        ):
            remote_src = f"{project_root}/{unit_name}"
            remote_dst = f"/etc/systemd/system/{unit_name}"
            print(_exec(
                ssh,
                f"test -f {remote_src} && "
                f"(cp -n {remote_dst} {remote_dst}.bak.valuescan 2>/dev/null || true) && "
                f"cp -f {remote_src} {remote_dst} 2>/dev/null || true",
                timeout=30,
            ))

        print("Restarting services...")
        print(_exec(ssh, "systemctl daemon-reload 2>/dev/null || true", timeout=30))
        # Note: valuescan-monitor is the signal monitor service, valuescan-trader may not exist as separate service
        service_units = [
            "valuescan-api",
            "valuescan-signal",
            "valuescan-monitor",
            "valuescan-token-refresher",
            "valuescan-copytrade",
            "proxy-checker",
        ]
        auto_trading_enabled = _read_remote_auto_trading_enabled(sftp, project_root)
        if auto_trading_enabled is False:
            print("Auto trading disabled in remote config; skip valuescan-trader restart.")
        else:
            service_units.append("valuescan-trader")

        restart_cmd = (
            "systemctl restart " + " ".join(service_units) + " 2>/dev/null || true"
        )
        print(_exec(ssh, restart_cmd, timeout=60))
        time.sleep(2)

        print("Verifying...")
        verify_cmd = (
            "systemctl is-active " + " ".join(service_units) +
            " --no-pager 2>/dev/null || true"
        )
        print(_exec(ssh, verify_cmd, timeout=30))
        print(_exec(ssh, "curl -s --max-time 5 http://127.0.0.1:5000/api/tickers?limit=3 | head -c 300", timeout=30))
        print(_exec(ssh, "curl -s --max-time 5 http://127.0.0.1:5000/api/simulation/traders | head -c 300", timeout=30))
        print(_exec(ssh, "curl -s --max-time 5 http://127.0.0.1:5000/api/db/status | head -c 300", timeout=30))
        print(_exec(ssh, "curl -s --max-time 5 http://127.0.0.1:5000/api/supported-models | head -c 300", timeout=30))
        print("Done.")
    finally:
        try:
            sftp.close()
        except Exception:
            pass
        ssh.close()


if __name__ == "__main__":
    main()
