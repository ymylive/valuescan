from __future__ import annotations

import json
import os
from pathlib import Path

import paramiko

HOST = os.environ.get("VALUESCAN_VPS_HOST", "82.158.88.34")
USER = os.environ.get("VALUESCAN_VPS_USER", "root")
PORT = int(os.environ.get("VALUESCAN_VPS_PORT", "22"))
PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "")
ENV_PATH = os.environ.get("VALUESCAN_VPS_ENV_PATH", "/root/valuescan/config/valuescan.env")

if not PASSWORD:
    raise SystemExit("Missing VALUESCAN_VPS_PASSWORD env var.")

default_erc20_contracts = json.dumps(
    {
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "LINK": "0x514910771AF9Ca656af840dff83E8264EcF986CA",
        "UNI": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
        "AAVE": "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
        "LDO": "0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32",
        "MKR": "0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2",
        "COMP": "0xc00e94Cb662C3520282E6f5717214004A7f26888",
    },
    separators=(",", ":"),
)

updates = {
    "VALUESCAN_ENABLE_TELEGRAM": "1",
    "VALUESCAN_SEND_TG_IN_MODE_1": "0",
    "VALUESCAN_SIGNAL_TG_DISABLED": "1",
    "VALUESCAN_TELEGRAM_BOT_TOKEN": "8574875999:AAGV2QmoHXMVVnsH2MCZL03Pa2V5wpqzGEk",
    "VALUESCAN_TELEGRAM_CHAT_ID": "-1003428496854",
    "VALUESCAN_TELEGRAM_PROXY": "",
    "VALUESCAN_SIGNAL_MAX_AGE_SECONDS": "86400",
    "VALUESCAN_STARTUP_SIGNAL_MAX_AGE_SECONDS": "86400",
    "VALUESCAN_AI_SIGNAL_LOOKBACK_HOURS": "24",
    "VALUESCAN_SIGNAL_LOOKBACK_HOURS": "24",
    "VALUESCAN_SIGNAL_POLL_ENABLED": "1",
    "VALUESCAN_SIGNAL_API_PATHS": "api/account/message/getWarnMessage,api/account/message/aiMessagePage",
    "VALUESCAN_API_VERIFY": "0",
    "VALUESCAN_API_TRUST_ENV": "0",
    "VALUESCAN_API_PROXY": "",
    "VALUESCAN_PROXY": "",
    "HTTP_PROXY": "",
    "HTTPS_PROXY": "",
    "COINGECKO_API_KEY": os.environ.get("COINGECKO_API_KEY", "CG-6itS45epruuSZZpR9Mpp3Ui8"),
    "ETHERSCAN_API_KEY": "HDEJ9NFX5BN63E9CPAZ16QJJJDE5X91W75",
    "FRED_API_KEY": "d704f6499bb9e731fb4e8c5cda0837d3",
    "VALUESCAN_FRED_SERIES": "PAYEMS,CPIAUCSL,UNRATE,FEDFUNDS",
    "VALUESCAN_FRED_RELEASE_IDS": "10,46,50,53,54,101",
    "VALUESCAN_ERC20_CONTRACTS": default_erc20_contracts,
    "VALUESCAN_GDELT_ENABLED": "1",
    "VALUESCAN_GDELT_QUERY": "(crypto OR bitcoin OR ethereum OR regulation OR policy OR fed OR inflation OR cpi OR payroll OR geopolitics OR war OR sanctions)",
    "VALUESCAN_GDELT_MAX_RECORDS": "8",
    "VALUESCAN_GDELT_TIMESPAN": "1d",
}

github_token = os.environ.get("VALUESCAN_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")
if github_token:
    updates["GITHUB_TOKEN"] = github_token

fred_release_ids = os.environ.get("VALUESCAN_FRED_RELEASE_IDS")
if fred_release_ids:
    updates["VALUESCAN_FRED_RELEASE_IDS"] = fred_release_ids

erc20_contracts = os.environ.get("VALUESCAN_ERC20_CONTRACTS")
if erc20_contracts:
    updates["VALUESCAN_ERC20_CONTRACTS"] = erc20_contracts

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, port=PORT)

sftp = ssh.open_sftp()
try:
    # Ensure directory exists
    ssh.exec_command(f"mkdir -p {Path(ENV_PATH).parent}")

    try:
        with sftp.open(ENV_PATH, "r") as f:
            raw = f.read().decode("utf-8", errors="ignore")
    except FileNotFoundError:
        raw = ""

    lines = raw.splitlines()
    new_lines = []
    seen = set()

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            new_lines.append(line)
            continue
        key, _ = line.split("=", 1)
        key = key.strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            new_lines.append(line)

    for key, val in updates.items():
        if key not in seen:
            new_lines.append(f"{key}={val}")

    content = "\n".join(new_lines) + "\n"
    with sftp.open(ENV_PATH, "w") as f:
        f.write(content.encode("utf-8"))

    ssh.exec_command(f"chmod 600 {ENV_PATH}")
    print(f"Updated {ENV_PATH}")

    for cmd in (
        "systemctl daemon-reload",
        "systemctl stop valuescan-signal 2>/dev/null || true",
        "systemctl disable valuescan-signal 2>/dev/null || true",
        "systemctl restart valuescan-monitor",
        "systemctl restart valuescan-api",
        "systemctl restart valuescan-token-refresher",
    ):
        ssh.exec_command(cmd)
    print("Restarted services: valuescan-monitor, valuescan-api, valuescan-token-refresher (valuescan-signal disabled)")
finally:
    sftp.close()
    ssh.close()
