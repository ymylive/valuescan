#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断 AI 功能（市场宏观分析、生图、AI简评）为何未触发
"""
import os
import sys
import getpass
import paramiko
from pathlib import Path

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
    print("诊断 AI 功能状态")
    print("=" * 80)

    # 1. 检查 signal_monitor/config.py 配置
    print("\n[1] 检查 signal_monitor/config.py 配置")
    print("-" * 80)
    result = _exec(ssh, "cat /root/valuescan/signal_monitor/config.py 2>&1 | grep -E 'ENABLE_PRO_CHART|ENABLE_AI|COINMARKETCAP|CRYPTOCOMPARE|COINGECKO' || echo '未找到配置'")
    print(result)

    # 2. 检查 AI 市场总结配置
    print("\n[2] 检查 AI 市场总结配置 (ai_summary_config.json)")
    print("-" * 80)
    result = _exec(ssh, "cat /root/valuescan/signal_monitor/ai_summary_config.json 2>&1 || echo '配置文件不存在'")
    print(result)

    # 3. 检查服务日志 - AI 市场总结
    print("\n[3] 检查 AI 市场总结日志")
    print("-" * 80)
    result = _exec(ssh, "journalctl -u valuescan-signal -n 100 --no-pager | grep -i 'ai.*summary\\|market.*analysis\\|macro' || echo '未找到相关日志'")
    print(result)

    # 4. 检查服务日志 - 图表生成
    print("\n[4] 检查图表生成日志")
    print("-" * 80)
    result = _exec(ssh, "journalctl -u valuescan-signal -n 100 --no-pager | grep -i 'chart\\|图表' || echo '未找到相关日志'")
    print(result)

    # 5. 检查服务日志 - AI 简评
    print("\n[5] 检查 AI 简评日志")
    print("-" * 80)
    result = _exec(ssh, "journalctl -u valuescan-signal -n 100 --no-pager | grep -i 'ai.*analysis\\|简评' || echo '未找到相关日志'")
    print(result)

    # 6. 检查最近的信号处理
    print("\n[6] 检查最近的信号处理")
    print("-" * 80)
    result = _exec(ssh, "journalctl -u valuescan-signal -n 50 --no-pager | tail -30")
    print(result)

    # 7. 检查环境变量
    print("\n[7] 检查服务环境变量")
    print("-" * 80)
    result = _exec(ssh, "systemctl show valuescan-signal --property=Environment")
    print(result)

    # 8. 检查 Python 模块是否存在
    print("\n[8] 检查关键 Python 模块")
    print("-" * 80)
    modules = [
        "ai_market_summary.py",
        "chart_pro_v10.py",
    ]
    for module in modules:
        result = _exec(ssh, f"ls -lh /root/valuescan/signal_monitor/{module} 2>&1")
        if "No such file" in result:
            print(f"  ❌ {module} 不存在")
        else:
            print(f"  ✅ {module}")

    # 9. 检查最近生成的图表文件
    print("\n[9] 检查最近生成的图表文件")
    print("-" * 80)
    result = _exec(ssh, "find /root/valuescan/signal_monitor -name '*.png' -mtime -1 -ls 2>/dev/null | head -10 || echo '未找到最近的图表文件'")
    print(result)

    # 10. 检查 AI 市场总结是否启用
    print("\n[10] 测试 AI 市场总结配置")
    print("-" * 80)
    result = _exec(ssh, "cd /root/valuescan && python3 -c \"import os; from signal_monitor import ai_market_summary; print('AI Summary Enabled:', ai_market_summary.AI_SUMMARY_ENABLED); print('API Key:', 'SET' if ai_market_summary.AI_SUMMARY_API_KEY else 'NOT SET')\" 2>&1", timeout=30)
    print(result)

    # 11. 检查最近的错误日志
    print("\n[11] 检查最近的错误日志")
    print("-" * 80)
    result = _exec(ssh, "journalctl -u valuescan-signal -n 100 --no-pager | grep -i 'error\\|exception\\|traceback' | tail -20 || echo '未找到错误日志'")
    print(result)

    print("\n" + "=" * 80)
    print("诊断完成")
    print("=" * 80)

    ssh.close()

if __name__ == "__main__":
    main()
