#!/usr/bin/env python3
"""Deploy updated signal_monitor files to VPS and send a test Telegram message."""
from __future__ import annotations

import argparse
import os
import time
import sys
from pathlib import Path
from typing import List, Optional


def _ensure_paramiko():
    try:
        import paramiko  # type: ignore
    except Exception:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko"])
        import paramiko  # type: ignore
    return paramiko


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deploy updates and test Telegram push.")
    parser.add_argument("--host", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--port", type=int, default=22)
    parser.add_argument("--remote-path", default="", help="Remote project root (auto-detect if empty)")
    parser.add_argument("--skip-test", action="store_true", help="Skip Telegram test message")
    return parser.parse_args()


def _exec(ssh, command: str) -> int:
    stdin, stdout, stderr = ssh.exec_command(command)
    return stdout.channel.recv_exit_status()


def _exec_output(ssh, command: str) -> str:
    stdin, stdout, stderr = ssh.exec_command(command)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return out or err


def _resolve_compose_cmd(ssh) -> str:
    if _exec(ssh, "docker compose version") == 0:
        return "docker compose"
    if _exec(ssh, "docker-compose --version") == 0:
        return "docker-compose"
    return "docker compose"


def _detect_remote_path(ssh) -> Optional[str]:
    candidates = [
        "/root/valuescan",
        "/root/nofx",
        "/opt/valuescan",
        "/srv/valuescan",
        "/opt/nofx",
        "/srv/nofx",
    ]
    for path in candidates:
        if _exec(ssh, f"test -f {path}/docker-compose.yml") == 0:
            return path
    # fallback: search common roots
    find_cmd = "find /root /opt /srv -maxdepth 3 -name docker-compose.yml 2>/dev/null"
    output = _exec_output(ssh, find_cmd)
    paths = [line.strip() for line in output.splitlines() if line.strip()]
    if not paths:
        return None
    # prefer path containing valuescan/nofx
    for line in paths:
        if "valuescan" in line or "nofx" in line:
            return os.path.dirname(line)
    return os.path.dirname(paths[0])


def _list_compose_files(ssh) -> List[str]:
    output = _exec_output(ssh, "find /root /opt /srv -maxdepth 4 -name docker-compose.yml 2>/dev/null")
    return [line.strip() for line in output.splitlines() if line.strip()]


def _detect_running_compose_file(ssh) -> Optional[str]:
    names = _exec_output(ssh, "docker ps -a --format '{{.Names}}'")
    containers = [line.strip() for line in names.splitlines() if line.strip()]
    # Focus on containers likely related to this project
    targets = [c for c in containers if ("nofx" in c or "valuescan" in c)]
    for name in targets:
        label = _exec_output(
            ssh,
            (
                "docker inspect -f "
                "'{{ index .Config.Labels \"com.docker.compose.project.config_files\" }}' "
                f"{name} 2>/dev/null"
            ),
        ).strip()
        if label and label != "<no value>":
            # config_files can be a comma-separated list
            return label.split(",")[0].strip()
    return None


def _compose_services(ssh, compose_cmd: str, compose_file: Optional[str]) -> List[str]:
    if not compose_file:
        return []
    project_dir = os.path.dirname(compose_file)
    cmd = (
        f"bash -lc '{compose_cmd} -f {compose_file} "
        f"--project-directory {project_dir} config --services'"
    )
    output = _exec_output(ssh, cmd)
    return [line.strip() for line in output.splitlines() if line.strip()]


def _sftp_mkdir_p(sftp, path: str) -> None:
    parts = [p for p in path.strip("/").split("/") if p]
    current = ""
    for part in parts:
        current = f"{current}/{part}" if current else f"/{part}"
        try:
            sftp.stat(current)
        except Exception:
            sftp.mkdir(current)


def _upload_file(sftp, local_path: Path, remote_path: str) -> None:
    _sftp_mkdir_p(sftp, os.path.dirname(remote_path))
    sftp.put(str(local_path), remote_path)


def _upload_updates(sftp, repo_root: Path, remote_root: str) -> None:
    files = [
        "api/server.py",
        "signal_monitor/ai_signal_analysis.py",
        "signal_monitor/ai_market_summary.py",
        "signal_monitor/ai_market_summary_config.json",
        "signal_monitor/ai_key_levels_config.py",
        "signal_monitor/ai_key_levels_config.json",
        "signal_monitor/ai_signal_scheduler.py",
        "signal_monitor/ai_signal_scheduler_vps.py",
        "signal_monitor/anomaly_config.json",
        "signal_monitor/anomaly_detector/config.py",
        "signal_monitor/config.py",
        "signal_monitor/config.example.py",
        "signal_monitor/fundamentals_sources.py",
        "signal_monitor/market_alert.py",
        "signal_monitor/market_alert_config.json",
        "signal_monitor/market_data_sources.py",
        "signal_monitor/metals_chart_generator.py",
        "signal_monitor/metals_data_sources.py",
        "signal_monitor/metals_supply_demand.json",
        "signal_monitor/anomaly_detector/detector.py",
        "signal_monitor/telegram.py",
        "signal_monitor/requirements.txt",
    ]
    for rel in files:
        local_path = repo_root / rel
        if not local_path.exists():
            continue
        remote_path = f"{remote_root}/{rel}"
        _upload_file(sftp, local_path, remote_path)


def _update_env(ssh, remote_root: str) -> None:
    cmd = (
        "bash -lc 'cd {root} && "
        "if [ -f .env ]; then "
        "grep -q \"^NOFX_METALS_KLINE_PROVIDERS=\" .env && "
        "sed -i \"s/^NOFX_METALS_KLINE_PROVIDERS=.*/NOFX_METALS_KLINE_PROVIDERS=binance/\" .env "
        "|| echo \"NOFX_METALS_KLINE_PROVIDERS=binance\" >> .env; "
        "else echo \"NOFX_METALS_KLINE_PROVIDERS=binance\" > .env; fi'"
    ).format(root=remote_root)
    _exec(ssh, cmd)


def _restart_stack(ssh, remote_root: str) -> None:
    compose_cmd = _resolve_compose_cmd(ssh)
    running_compose = _detect_running_compose_file(ssh)
    compose_file = running_compose or (
        f"{remote_root}/docker-compose.yml" if _exec(ssh, f"test -f {remote_root}/docker-compose.yml") == 0 else None
    )

    services = _compose_services(ssh, compose_cmd, compose_file) if compose_file else []
    if services:
        preferred = []
        for name in ("nofx-monitor", "nofx-api", "nofx"):
            if name in services:
                preferred.append(name)
        if not preferred:
            preferred = services
        project_dir = os.path.dirname(compose_file)
        service_args = " ".join(preferred)
        _exec(ssh, f"bash -lc '{compose_cmd} -f {compose_file} --project-directory {project_dir} build {service_args}'")
        _exec(ssh, f"bash -lc '{compose_cmd} -f {compose_file} --project-directory {project_dir} up -d --force-recreate {service_args}'")
        return

    # fallback: try project root
    _exec(ssh, f"bash -lc 'cd {remote_root} && {compose_cmd} build'")
    _exec(ssh, f"bash -lc 'cd {remote_root} && {compose_cmd} up -d --force-recreate'")


def _test_telegram_docker(ssh, remote_root: str) -> str:
    compose_cmd = _resolve_compose_cmd(ssh)
    compose_file = _detect_running_compose_file(ssh) or (
        f"{remote_root}/docker-compose.yml" if _exec(ssh, f"test -f {remote_root}/docker-compose.yml") == 0 else None
    )
    services = _compose_services(ssh, compose_cmd, compose_file) if compose_file else []
    target = "nofx-monitor" if "nofx-monitor" in services else ("nofx" if "nofx" in services else None)
    if not target:
        return "No suitable docker service found for Telegram test."
    project_dir = os.path.dirname(compose_file) if compose_file else remote_root
    cmd = (
        "bash -lc 'cd {root} && "
        "{compose} -f {compose_file} --project-directory {project_dir} "
        "exec -T {service} "
        "python - <<\"PY\"\n"
        "from signal_monitor.telegram import send_telegram_message\n"
        "send_telegram_message(\"✅ VPS deploy test: metals+news+rawK\", parse_mode=\"HTML\")\n"
        "PY'"
    ).format(
        root=remote_root,
        compose=compose_cmd,
        compose_file=compose_file or f"{remote_root}/docker-compose.yml",
        project_dir=project_dir,
        service=target,
    )
    return _exec_output(ssh, cmd)


def _test_telegram_host(ssh, remote_root: str) -> str:
    cmd = (
        "bash -lc 'cd {root} && set -a && "
        "[ -f .env ] && . ./.env || true; set +a; "
        "python - <<""PY""\n"
        "from signal_monitor.telegram import send_telegram_message\n"
        "send_telegram_message(\"✅ VPS deploy test: metals+news+rawK\", parse_mode=\"HTML\")\n"
        "PY'"
    ).format(root=remote_root)
    return _exec_output(ssh, cmd)


def main() -> int:
    args = _parse_args()
    paramiko = _ensure_paramiko()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    last_error = None
    for attempt in range(1, 4):
        try:
            client.connect(
                args.host,
                username=args.user,
                password=args.password,
                port=args.port,
                timeout=20,
                banner_timeout=30,
                auth_timeout=30,
            )
            last_error = None
            break
        except Exception as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(2 * attempt)
    if last_error:
        raise last_error

    remote_root = args.remote_path or _detect_remote_path(client)
    if not remote_root:
        print("[deploy] Remote project path not found.")
        return 2

    sftp = client.open_sftp()
    repo_root = Path(__file__).resolve().parent
    _upload_updates(sftp, repo_root, remote_root)
    sftp.close()
    _update_env(client, remote_root)

    # restart stack (prefer docker)
    docker_ok = _exec(client, "docker --version") == 0
    if docker_ok and _exec(client, f"test -f {remote_root}/docker-compose.yml") == 0:
        _restart_stack(client, remote_root)
    else:
        # fallback: try systemd restart
        _exec(client, "systemctl restart signal-monitor || true")
        _exec(client, "systemctl restart valuescan-monitor || true")

    if not args.skip_test:
        if docker_ok and _exec(client, f"test -f {remote_root}/docker-compose.yml") == 0:
            output = _test_telegram_docker(client, remote_root)
        else:
            output = _test_telegram_host(client, remote_root)
        print("[deploy] Test output:")
        print(output)

    client.close()
    print(f"[deploy] Done. Remote path: {remote_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
