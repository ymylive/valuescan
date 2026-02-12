# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import paramiko

HOST = os.environ.get("VALUESCAN_VPS_HOST", "82.158.88.34")
USER = os.environ.get("VALUESCAN_VPS_USER", "root")
PORT = int(os.environ.get("VALUESCAN_VPS_PORT", "22"))
PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "")

if not PASSWORD:
    raise SystemExit("Missing VALUESCAN_VPS_PASSWORD env var.")


def _exec(ssh: paramiko.SSHClient, cmd: str, timeout: int = 600) -> str:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")
    return (out + ("\n" + err if err else "")).strip()


def _pick_python(ssh: paramiko.SSHClient) -> str:
    cmd = (
        "command -v python3.9 || "
        "command -v python3.11 || "
        "command -v python3.10 || "
        "command -v python3 || "
        "command -v python"
    )
    out = _exec(ssh, cmd, timeout=30)
    for line in out.splitlines():
        candidate = line.strip()
        if candidate:
            return candidate
    return "python3"


ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, port=PORT, timeout=30)

try:
    py = _pick_python(ssh)
    print("[1/4] Check ValueScan API responses...")
    api_cmd = (
        "cd /root/valuescan/signal_monitor && " + py + " - << 'PY'\n"
        "import requests\n"
        "from valuescan_api import build_valuescan_headers, get_valuescan_base_url\n"
        "headers = build_valuescan_headers()\n"
        "base = get_valuescan_base_url()\n"
        "\n"
        "def call(path, method=\"get\"):\n"
        "    url = base + \"/\" + path\n"
        "    if method == \"post\":\n"
        "        resp = requests.post(url, headers=headers, json={\"page\": 1, \"pageSize\": 20}, timeout=15)\n"
        "    else:\n"
        "        resp = requests.get(url, headers=headers, timeout=15)\n"
        "    print(f\"{path} status={resp.status_code}\")\n"
        "    try:\n"
        "        data = resp.json()\n"
        "        print(str(data)[:400])\n"
        "    except Exception:\n"
        "        print(resp.text[:400])\n"
        "\n"
        "call(\"api/account/message/getWarnMessage\", \"get\")\n"
        "call(\"api/account/message/aiMessagePage\", \"post\")\n"
        "PY"
    )
    print(_exec(ssh, api_cmd, timeout=120))

    print("\n[2/4] Trigger one scheduler cycle (ETH)...")
    scheduler_cmd = (
        "cd /root/valuescan && "
        "VALUESCAN_AI_SIGNAL_SYMBOLS=ETH "
        "VALUESCAN_AI_SIGNAL_RUN_ONCE=1 "
        "VALUESCAN_AI_SIGNAL_DRY_RUN=0 "
        f"{py} signal_monitor/ai_signal_scheduler.py 2>&1"
    )
    print(_exec(ssh, scheduler_cmd, timeout=1200))

    print("\n[3/4] Generate macro summary and print text...")
    macro_cmd = (
        "cd /root/valuescan/signal_monitor && "
        f"{py} -c \"from ai_market_summary import generate_market_summary; print(generate_market_summary(force=True) or '')\" 2>&1"
    )
    macro_output = _exec(ssh, macro_cmd, timeout=600)
    print(macro_output)

    print("\n[4/4] Generate ETH AI brief and print text...")
    brief_cmd = (
        "cd /root/valuescan/signal_monitor && "
        f"{py} -c \"from ai_signal_analysis import analyze_signal; r = analyze_signal('ETH'); print(r.get('analysis') if isinstance(r, dict) else r)\" 2>&1"
    )
    brief_output = _exec(ssh, brief_cmd, timeout=600)
    print(brief_output)

    with open("output/vps_macro_summary.txt", "w", encoding="utf-8") as f:
        f.write(macro_output)
    with open("output/vps_eth_brief.txt", "w", encoding="utf-8") as f:
        f.write(brief_output)
finally:
    ssh.close()
