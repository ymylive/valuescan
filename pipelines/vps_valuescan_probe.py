#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from typing import Optional

try:
    import paramiko
except ImportError as exc:
    raise SystemExit("paramiko is required. Run: python -m pip install paramiko") from exc


def _env(name: str, required: bool = True, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise SystemExit(f"Missing required env: {name}")
    return value or ""


def _run_remote(
    client: paramiko.SSHClient, command: str, env: Optional[dict[str, str]] = None
) -> tuple[str, str, int]:
    stdin, stdout, stderr = client.exec_command(command, environment=env)
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")
    exit_status = stdout.channel.recv_exit_status()
    return out, err, exit_status


def main() -> None:
    host = _env("VPS_HOST")
    user = _env("VPS_USER")
    password = _env("VPS_PASSWORD")
    port = int(_env("VPS_PORT", required=False, default="22"))
    auth_token = os.getenv("VALUESCAN_AUTH_TOKEN", "")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, port=port, username=user, password=password, timeout=15)

    detect_py = (
        "bash -lc 'command -v python3.11 || command -v python3.10 || "
        "command -v python3.9 || command -v python3.8 || command -v python3.7 || "
        "command -v python3'"
    )
    py_out, py_err, _ = _run_remote(client, detect_py)
    py_path = py_out.strip().splitlines()[0] if py_out.strip() else ""
    if not py_path:
        print("error=python_not_found_on_vps", file=sys.stderr)
        if py_err:
            print(py_err, file=sys.stderr)
        client.close()
        return

    remote_script = f"{py_path} - <<'PY'\n" + r"""import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

AUTH_TOKEN = os.getenv("VALUESCAN_AUTH_TOKEN", "")
AUTH_HEADER = {"Authorization": f"Bearer {AUTH_TOKEN}"} if AUTH_TOKEN else {}


def _find_repo_root():
    candidates = [
        Path("/root/valuescan"),
        Path("/opt/valuescan"),
        Path("/root/nofx"),
        Path("/opt/nofx"),
    ]
    for base in candidates:
        if (base / "api" / "server.py").exists():
            return base
    try:
        result = subprocess.check_output(
            ["bash", "-lc", "find /root /opt -maxdepth 4 -type f -path '*/api/server.py' 2>/dev/null | head -1"],
            text=True,
        ).strip()
        if result:
            return Path(result).parent.parent
    except Exception:
        return None
    return None


def _parse_routes(server_py):
    text = server_py.read_text(encoding="utf-8", errors="ignore")
    routes = {}
    idx = 0
    while True:
        start = text.find("@app.route(", idx)
        if start == -1:
            break
        paren_start = text.find("(", start)
        if paren_start == -1:
            break
        depth = 0
        end = None
        for i in range(paren_start, len(text)):
            ch = text[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end is None:
            break
        args = text[paren_start + 1 : end]
        match = re.search(r"['\"](?P<url>/api/valuescan[^'\"]*)['\"]", args)
        if match:
            url = match.group("url")
            methods = ["GET"]
            methods_match = re.search(r"methods\s*=\s*\[(?P<methods>[^\]]+)\]", args)
            if methods_match:
                raw = methods_match.group("methods")
                methods = [item.strip().strip("'\"") for item in raw.split(",") if item.strip()]
            routes.setdefault(url, set()).update(methods)
        idx = end + 1
    return routes


def _load_port(repo_root):
    env_path = repo_root / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip().startswith("NOFX_BACKEND_PORT="):
                raw = line.split("=", 1)[-1].strip()
                if raw.isdigit():
                    return int(raw)
    return None


def _probe_base_url(port, path):
    url = f"http://127.0.0.1:{port}{path}"
    req = Request(url, method="GET", headers=AUTH_HEADER)
    try:
        with urlopen(req, timeout=5) as resp:
            return True, resp.status
    except HTTPError as exc:
        return True, exc.code
    except Exception:
        return False, None


def _parse_ports_from_text(text):
    ports = set()
    for match in re.finditer(r":(\\d{2,5})", text):
        port = int(match.group(1))
        if 0 < port < 65536:
            ports.add(port)
    for match in re.finditer(r"port\\s*=\\s*(\\d{2,5})", text):
        port = int(match.group(1))
        if 0 < port < 65536:
            ports.add(port)
    return ports


def _ports_from_docker(repo_root):
    compose = repo_root / "docker-compose.yml"
    if not compose.exists():
        return set()
    return _parse_ports_from_text(compose.read_text(encoding="utf-8", errors="ignore"))


def _ports_from_server(server_py):
    return _parse_ports_from_text(server_py.read_text(encoding="utf-8", errors="ignore"))


def _ports_from_systemd():
    ports = set()
    try:
        unit_files = subprocess.check_output(
            ["bash", "-lc", "ls /etc/systemd/system 2>/dev/null | grep -E '(valuescan|nofx)' || true"],
            text=True,
        ).splitlines()
    except Exception:
        return ports
    for unit in unit_files:
        unit_path = Path("/etc/systemd/system") / unit
        try:
            content = unit_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        ports.update(_parse_ports_from_text(content))
    return ports


def _ports_from_ss():
    ports = set()
    try:
        output = subprocess.check_output(["bash", "-lc", "ss -ltnp || true"], text=True)
    except Exception:
        return ports
    for line in output.splitlines():
        if "LISTEN" not in line:
            continue
        if not any(tag in line for tag in ("python", "gunicorn", "nofx", "flask")):
            continue
        parts = line.split()
        for part in parts:
            if part.count(":") >= 1 and part.rsplit(":", 1)[-1].isdigit():
                port = int(part.rsplit(":", 1)[-1])
                if 0 < port < 65536:
                    ports.add(port)
    return ports


def _resolve_candidate_ports(repo_root, server_py):
    ports = set()
    env_port = _load_port(repo_root)
    if env_port:
        ports.add(env_port)
    ports.update(_ports_from_docker(repo_root))
    ports.update(_ports_from_server(server_py))
    ports.update(_ports_from_systemd())
    ports.update(_ports_from_ss())
    ports.update({8080, 8000, 5000, 5001, 9000, 3000, 7000})
    return sorted(ports)


def _request(url, method):
    data = None
    headers = dict(AUTH_HEADER)
    if method.upper() == "POST":
        data = b"{}"
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=6) as resp:
            return resp.status
    except HTTPError as exc:
        return exc.code
    except URLError:
        return None
    except Exception:
        return None


def _materialize_path(path):
    if "<" not in path:
        return path
    return re.sub(r"<[^>]+>", "probe", path)


def main() -> None:
    repo_root = _find_repo_root()
    if not repo_root:
        print("error=repo_root_not_found")
        return

    server_py = repo_root / "api" / "server.py"
    routes = _parse_routes(server_py)
    if not routes:
        print("error=no_routes_found")
        return

    candidate_ports = _resolve_candidate_ports(repo_root, server_py)
    if not candidate_ports:
        print("error=base_url_not_found")
        return

    base_candidates = []
    for port in candidate_ports:
        ok_status = _probe_base_url(port, "/api/valuescan/status")
        health_status = _probe_base_url(port, "/api/health")
        base_candidates.append(
            {
                "port": port,
                "valuescan_status": ok_status[1],
                "health_status": health_status[1],
            }
        )

    base_urls = [f"http://127.0.0.1:{item['port']}" for item in base_candidates if item["valuescan_status"] is not None or item["health_status"] is not None]
    if not base_urls:
        print(json.dumps({"error": "base_url_not_found", "ports": base_candidates}, ensure_ascii=False, indent=2))
        return

    all_results = []
    for base_url in base_urls:
        ok = 0
        auth = 0
        bad_request = 0
        method_not_allowed = 0
        fail = 0
        error = 0
        details = []

        for path in sorted(routes):
            materialized = _materialize_path(path)
            methods = sorted(routes[path])
            for method in methods:
                status = _request(base_url + materialized, method)
                if status is None:
                    error += 1
                    details.append({"method": method, "path": materialized, "path_template": path, "status": None})
                    continue
                if status in (401, 403):
                    auth += 1
                elif status in (400, 422):
                    bad_request += 1
                elif status == 405:
                    method_not_allowed += 1
                elif 200 <= status < 400:
                    ok += 1
                else:
                    fail += 1
                details.append({"method": method, "path": materialized, "path_template": path, "status": status})

        reachable = ok + auth + bad_request + method_not_allowed
        all_results.append(
            {
                "base_url": base_url,
                "routes": len(routes),
                "checks": len(details),
                "reachable": reachable,
                "ok": ok,
                "auth_required": auth,
                "bad_request": bad_request,
                "method_not_allowed": method_not_allowed,
                "fail": fail,
                "error": error,
                "details": details,
            }
        )

    print(json.dumps({
        "repo_root": str(repo_root),
        "ports": base_candidates,
        "results": all_results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
PY"""

    remote_env = {"VALUESCAN_AUTH_TOKEN": auth_token} if auth_token else None
    out, err, code = _run_remote(client, remote_script, env=remote_env)

    if out:
        print(out)
    if err:
        print(err, file=sys.stderr)

    client.close()


if __name__ == "__main__":
    main()
