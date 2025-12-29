#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署 AI 交易系统到 VPS
Deploy AI Trading System to VPS

包含:
- AI 信号转发器 (AI Signal Forwarder)
- AI 模式处理器 (AI Mode Handler)
- AI 仓位代理 (AI Position Agent)
- AI 性能追踪器 (AI Performance Tracker)
- AI 进化引擎 (AI Evolution Engine)
- AI 进化策略配置 (AI Evolution Profiles)
- 前端配置界面 (Frontend Config UI)
"""

import paramiko
import os
import sys
from pathlib import Path

# VPS 配置
VPS_HOST = "valuescan.io"
VPS_USER = "root"
VPS_PASSWORD = "Qq159741"
VPS_PROJECT_PATH = "/root/valuescan"

# 需要上传的文件
FILES_TO_UPLOAD = [
    # ============ Backend - Signal Monitor ============
    ("signal_monitor/ai_signal_forwarder.py", "signal_monitor/ai_signal_forwarder.py"),

    # ============ Backend - Binance Trader ============
    ("binance_trader/ai_mode_handler.py", "binance_trader/ai_mode_handler.py"),
    ("binance_trader/ai_position_agent.py", "binance_trader/ai_position_agent.py"),
    ("binance_trader/ai_performance_tracker.py", "binance_trader/ai_performance_tracker.py"),
    ("binance_trader/ai_evolution_engine.py", "binance_trader/ai_evolution_engine.py"),
    ("binance_trader/ai_evolution_profiles.py", "binance_trader/ai_evolution_profiles.py"),
    ("binance_trader/futures_main.py", "binance_trader/futures_main.py"),
    ("binance_trader/config.example.py", "binance_trader/config.example.py"),

    # ============ Backend - Scripts ============
    ("scripts/valuescan_futures_bridge.py", "scripts/valuescan_futures_bridge.py"),

    # ============ Frontend - Types ============
    ("web/src/types/config.ts", "web/src/types/config.ts"),

    # ============ Frontend - Components ============
    ("web/src/components/valuescan/AITradingConfigSection.tsx", "web/src/components/valuescan/AITradingConfigSection.tsx"),
    ("web/src/pages/SettingsPage.tsx", "web/src/pages/SettingsPage.tsx"),

    # ============ Documentation ============
    ("AI_TRADING_SYSTEM.md", "AI_TRADING_SYSTEM.md"),
    ("AI_EVOLUTION_SYSTEM.md", "AI_EVOLUTION_SYSTEM.md"),
    ("AI_EVOLUTION_STRATEGIES.md", "AI_EVOLUTION_STRATEGIES.md"),
]


def deploy_files():
    """上传文件并重启服务"""
    print("=" * 80)
    print("部署 AI 交易系统到 VPS")
    print("Deploy AI Trading System to VPS")
    print("=" * 80 + "\n")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"连接到 {VPS_HOST}...")
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD,
                   look_for_keys=False, allow_agent=False)
        sftp = ssh.open_sftp()

        print(f"✅ 已连接到 {VPS_HOST}\n")

        # 上传文件
        print("=" * 80)
        print("上传文件...")
        print("=" * 80 + "\n")

        uploaded_count = 0
        skipped_count = 0

        for local_path, remote_path in FILES_TO_UPLOAD:
            local_file = Path(local_path)
            remote_file = f"{VPS_PROJECT_PATH}/{remote_path}"

            if not local_file.exists():
                print(f"⚠️  文件不存在: {local_path}")
                skipped_count += 1
                continue

            # 确保远程目录存在
            remote_dir = os.path.dirname(remote_file)
            try:
                sftp.stat(remote_dir)
            except:
                stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_dir}")
                stdout.channel.recv_exit_status()

            print(f"📤 上传: {local_path}")
            print(f"   -> {remote_file}")
            sftp.put(str(local_file), remote_file)
            print(f"   ✅ 完成\n")
            uploaded_count += 1

        sftp.close()

        print(f"📊 上传统计: {uploaded_count} 个文件上传成功, {skipped_count} 个文件跳过\n")

        # 创建数据目录
        print("=" * 80)
        print("创建数据目录...")
        print("=" * 80 + "\n")

        data_dirs = [
            f"{VPS_PROJECT_PATH}/data",
            f"{VPS_PROJECT_PATH}/binance_trader/data",
        ]

        for data_dir in data_dirs:
            print(f"📁 创建目录: {data_dir}")
            stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {data_dir}")
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0:
                print(f"   ✅ 完成\n")
            else:
                print(f"   ⚠️  返回状态: {exit_status}\n")

        # 重新构建前端
        print("=" * 80)
        print("重新构建前端...")
        print("=" * 80 + "\n")

        print("🔨 执行: cd web && npm run build")
        stdin, stdout, stderr = ssh.exec_command(f"cd {VPS_PROJECT_PATH}/web && npm run build")
        exit_status = stdout.channel.recv_exit_status()

        if exit_status == 0:
            print("✅ 前端构建成功\n")
        else:
            print(f"⚠️  前端构建返回状态: {exit_status}")
            error_output = stderr.read().decode('utf-8')
            if error_output:
                print(f"错误输出:\n{error_output}\n")

        # 重启服务
        print("=" * 80)
        print("重启服务...")
        print("=" * 80 + "\n")

        services = [
            ("valuescan-signal", "Signal Monitor"),
            ("valuescan-trader", "Binance Trader"),
            ("valuescan-api", "API Server"),
        ]

        for service_name, service_desc in services:
            print(f"🔄 重启 {service_desc} ({service_name})...")
            stdin, stdout, stderr = ssh.exec_command(f"systemctl restart {service_name}")
            exit_status = stdout.channel.recv_exit_status()

            if exit_status == 0:
                print(f"   ✅ 重启成功\n")
            else:
                print(f"   ⚠️  重启返回状态: {exit_status}\n")

        # 检查服务状态
        print("=" * 80)
        print("检查服务状态...")
        print("=" * 80 + "\n")

        for service_name, service_desc in services:
            print(f"📊 {service_desc} ({service_name}):")
            stdin, stdout, stderr = ssh.exec_command(
                f"systemctl is-active {service_name} && echo 'ACTIVE' || echo 'INACTIVE'"
            )
            status = stdout.read().decode('utf-8').strip()

            if "ACTIVE" in status:
                print(f"   ✅ 运行中\n")
            else:
                print(f"   ❌ 未运行\n")

        ssh.close()

        print("\n" + "=" * 80)
        print("✅ 部署完成！")
        print("=" * 80 + "\n")

        print("📝 后续步骤:")
        print("1. 更新配置文件:")
        print(f"   ssh {VPS_USER}@{VPS_HOST}")
        print(f"   cd {VPS_PROJECT_PATH}/binance_trader")
        print("   cp config.example.py config.py")
        print("   nano config.py  # 配置 AI 相关参数")
        print()
        print("2. 配置 AI 模式 (在 config.py 中):")
        print("   ENABLE_AI_MODE = True")
        print("   ENABLE_AI_POSITION_AGENT = True")
        print("   ENABLE_AI_EVOLUTION = True")
        print("   AI_EVOLUTION_PROFILE = 'balanced_day'  # 或其他策略")
        print()
        print("3. 重启交易服务:")
        print("   systemctl restart valuescan-trader")
        print()
        print("4. 查看日志:")
        print("   journalctl -u valuescan-trader -f")
        print()
        print("5. 访问 Web 界面:")
        print(f"   https://{VPS_HOST}")
        print("   进入 Settings → AI 交易 配置所有选项")
        print()
        print("📚 文档:")
        print("   - AI_TRADING_SYSTEM.md - AI 交易系统总览")
        print("   - AI_EVOLUTION_SYSTEM.md - AI 进化系统详解")
        print("   - AI_EVOLUTION_STRATEGIES.md - 策略配置指南")
        print()

        return True

    except Exception as e:
        print(f"❌ 部署失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = deploy_files()
    sys.exit(0 if success else 1)
