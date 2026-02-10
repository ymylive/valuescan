#!/usr/bin/env python3
"""
手动触发美股监控警报
"""

import os
import sys
import paramiko

VPS_HOST = "43.133.12.98"
VPS_USER = "root"
VPS_PASS = "Qq159741"

REMOTE_SCRIPT = '''
import sys
sys.path.insert(0, '/root/valuescan/signal_monitor')
from market_alert import fetch_us_market_data, send_alert
from datetime import datetime, timezone, timedelta

NY_TZ = timezone(timedelta(hours=-5))
now = datetime.now(NY_TZ)

symbols = ["SPY", "QQQ"]
results = []

for symbol in symbols:
    data = fetch_us_market_data(symbol)
    print(f"{symbol}: {data}")
    if data and data.get("change_pct") is not None:
        results.append((symbol, data["change_pct"]))

if not results:
    print("No data fetched!")
else:
    avg_change = sum(r[1] for r in results) / len(results)
    emoji = "📈" if avg_change > 0 else "📉"
    direction = "上涨" if avg_change > 0 else "下跌"

    lines = [f"{emoji} <b>美股今日开盘{direction}</b>", ""]
    for symbol, change in results:
        sign = "+" if change > 0 else ""
        lines.append(f"• {symbol}: {sign}{change:.2f}%")

    lines.append("")
    lines.append(f"⏰ {now.strftime('%Y-%m-%d %H:%M')} ET")

    message = "\\n".join(lines)
    print("\\n=== Message ===")
    print(message)
    print("\\n=== Sending... ===")
    send_alert(message)
    print("Done!")
'''

def main():
    print("=" * 50)
    print("Triggering US Market Alert on VPS")
    print("=" * 50)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS, timeout=15)

    # 执行远程脚本
    cmd = f'cd /root/valuescan/signal_monitor && python3 -c "{REMOTE_SCRIPT}"'
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)

    print("\n=== Output ===")
    print(stdout.read().decode())

    err = stderr.read().decode()
    if err:
        print("\n=== Errors ===")
        print(err)

    client.close()
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()
