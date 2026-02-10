#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断前端黑屏和AI功能问题
"""
import os
import sys
import getpass
import paramiko

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
    print("诊断报告")
    print("=" * 80)

    # 1. 检查 API 服务日志
    print("\n[1] API 服务日志（最近错误）")
    print("-" * 80)
    result = _exec(ssh, "journalctl -u valuescan-api -n 50 --no-pager | grep -i 'error\\|exception\\|traceback' | tail -20")
    if result.strip():
        print(result)
    else:
        print("  ✅ 无错误")

    # 2. 检查 API 服务状态
    print("\n[2] API 服务状态")
    print("-" * 80)
    result = _exec(ssh, "systemctl status valuescan-api --no-pager | head -20")
    print(result)

    # 3. 检查 AI 简评日志
    print("\n[3] AI 简评日志（最近100行）")
    print("-" * 80)
    result = _exec(ssh, "journalctl -u valuescan-signal -n 200 --no-pager | grep -i 'AI简评\\|ai.*analysis\\|ai.*comment' | tail -20")
    if result.strip():
        print(result)
    else:
        print("  ⚠️  未找到 AI 简评日志")

    # 4. 检查图表生成日志
    print("\n[4] 图表生成日志（最近100行）")
    print("-" * 80)
    result = _exec(ssh, "journalctl -u valuescan-signal -n 200 --no-pager | grep -i '图表\\|chart.*generat\\|generate.*chart' | tail -20")
    if result.strip():
        print(result)
    else:
        print("  ⚠️  未找到图表生成日志")

    # 5. 检查最近的信号处理
    print("\n[5] 最近的信号处理（最近30行）")
    print("-" * 80)
    result = _exec(ssh, "journalctl -u valuescan-signal -n 100 --no-pager | tail -30")
    print(result)

    # 6. 检查配置
    print("\n[6] 当前配置")
    print("-" * 80)
    result = _exec(ssh, "cat /root/valuescan/signal_monitor/config.py | grep -E 'ENABLE_AI_SIGNAL_ANALYSIS|ENABLE_PRO_CHART|ENABLE_TRADINGVIEW'")
    print(result)

    # 7. 检查前端文件
    print("\n[7] 前端文件检查")
    print("-" * 80)
    result = _exec(ssh, "ls -lh /root/valuescan/web/dist/index.html /root/valuescan/web/dist/assets/*.js 2>&1 | head -10")
    print(result)

    print("\n" + "=" * 80)
    print("诊断完成")
    print("=" * 80)

    ssh.close()

if __name__ == "__main__":
    main()
