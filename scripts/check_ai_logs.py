#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查 AI 功能实时日志
"""
import os
import sys
import getpass
import paramiko
import time

# 设置 Windows 控制台编码
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

DEFAULT_HOST = "82.158.88.34"
DEFAULT_USER = "root"

def _get_password():
    password = os.environ.get("VALUESCAN_VPS_PASSWORD", "")
    if password:
        return password
    if sys.stdin.isatty():
        try:
            pw = getpass.getpass(f"Enter SSH password for {DEFAULT_USER}@{DEFAULT_HOST}: ")
            return (pw or "").strip() or None
        except Exception:
            pass
    return None

def _exec(ssh, cmd, timeout=60):
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="ignore")
        err = stderr.read().decode("utf-8", errors="ignore")
        return (out + ("\n" + err if err else "")).strip()
    except Exception as exc:
        return f"[exec error] {cmd}: {exc}"

def main():
    password = _get_password()
    if not password:
        print("❌ 需要设置 VALUESCAN_VPS_PASSWORD 环境变量")
        return

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"连接到 {DEFAULT_USER}@{DEFAULT_HOST}...")
        ssh.connect(DEFAULT_HOST, username=DEFAULT_USER, password=password, timeout=30)
        print("✅ SSH 连接成功\n")
    except Exception as e:
        print(f"❌ SSH 连接失败: {e}")
        return

    print("=" * 80)
    print("实时监控 AI 功能日志 (最近 200 行)")
    print("=" * 80)

    # 1. AI 市场总结日志
    print("\n[1] AI 市场总结日志")
    print("-" * 80)
    result = _exec(ssh, "journalctl -u valuescan-signal -n 200 --no-pager | grep -A 5 -B 2 'AI\\|market\\|宏观\\|分析' | tail -100")
    print(result)

    # 2. 图表生成日志
    print("\n[2] 图表生成日志")
    print("-" * 80)
    result = _exec(ssh, "journalctl -u valuescan-signal -n 200 --no-pager | grep -A 3 -B 2 'chart\\|图表\\|生成' | tail -50")
    print(result)

    # 3. 检查最近的错误
    print("\n[3] 最近的错误日志")
    print("-" * 80)
    result = _exec(ssh, "journalctl -u valuescan-signal -n 200 --no-pager | grep -i 'error\\|exception\\|traceback\\|failed' | tail -30")
    print(result)

    # 4. 检查图表文件
    print("\n[4] 最近生成的图表文件")
    print("-" * 80)
    result = _exec(ssh, "find /root/valuescan -name '*.png' -mmin -60 -ls 2>/dev/null | head -20")
    if result.strip():
        print(result)
    else:
        print("未找到最近 60 分钟内生成的图表文件")

    # 5. 检查 Telegram 发送日志
    print("\n[5] Telegram 发送日志")
    print("-" * 80)
    result = _exec(ssh, "journalctl -u valuescan-signal -n 200 --no-pager | grep -i 'telegram\\|发送\\|send' | tail -30")
    print(result)

    # 6. 检查配置状态
    print("\n[6] 当前配置状态")
    print("-" * 80)
    result = _exec(ssh, "cat /root/valuescan/signal_monitor/config.py | grep -E 'ENABLE_PRO_CHART|ENABLE_AI|ENABLE_TRADINGVIEW'")
    print(result)

    print("\n" + "=" * 80)
    print("监控完成")
    print("=" * 80)

    ssh.close()

if __name__ == "__main__":
    main()
