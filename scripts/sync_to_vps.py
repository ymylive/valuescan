#!/usr/bin/env python3
"""
同步黑屏修复和 AI 简评修复到 VPS
"""

import os
import sys
from pathlib import Path

# VPS 配置
VPS_HOST = os.getenv("VPS_HOST", "root@valuescan.io")
VPS_PATH = "/root/valuescan"

# 需要同步的文件
FILES_TO_SYNC = [
    # API 服务器
    "api/server.py",

    # Signal Monitor
    "signal_monitor/ai_market_summary.py",

    # Web 前端
    "web/vite.config.ts",
    "web/src/App.tsx",

    # 测试脚本
    "scripts/test_ai_summary.py",
    "scripts/test_config_page_chrome.py",
    "scripts/quick_test_config.py",

    # 文档
    "AI_SUMMARY_FIX_REPORT.md",
    "AI_SUMMARY_QUICK_GUIDE.md",
    "BLACK_SCREEN_FIX_REPORT.md",
    "BLACK_SCREEN_FIX_GUIDE.md",
]

def run_command(cmd):
    """执行命令"""
    print(f"[CMD] {cmd}")
    result = os.system(cmd)
    if result != 0:
        print(f"[ERROR] Command failed with code {result}")
        return False
    return True

def sync_files():
    """同步文件到 VPS"""
    print("=" * 80)
    print("同步文件到 VPS")
    print("=" * 80)

    # 1. 同步修改的文件
    print("\n[1/5] 同步修改的文件...")
    for file in FILES_TO_SYNC:
        if not Path(file).exists():
            print(f"  [SKIP] {file} (不存在)")
            continue

        # 创建远程目录
        remote_dir = str(Path(file).parent)
        if remote_dir and remote_dir != ".":
            cmd = f'ssh {VPS_HOST} "mkdir -p {VPS_PATH}/{remote_dir}"'
            if not run_command(cmd):
                return False

        # 同步文件
        cmd = f'scp {file} {VPS_HOST}:{VPS_PATH}/{file}'
        if not run_command(cmd):
            return False
        print(f"  [OK] {file}")

    # 2. 重新构建前端
    print("\n[2/5] 重新构建前端...")
    cmd = f'ssh {VPS_HOST} "cd {VPS_PATH}/web && npm run build"'
    if not run_command(cmd):
        print("  [WARN] 前端构建失败，但继续...")

    # 3. 重启 API 服务器
    print("\n[3/5] 重启 API 服务器...")
    cmd = f'ssh {VPS_HOST} "systemctl restart valuescan-api"'
    if not run_command(cmd):
        print("  [WARN] API 服务器重启失败")

    # 4. 重启 Signal Monitor
    print("\n[4/5] 重启 Signal Monitor...")
    cmd = f'ssh {VPS_HOST} "systemctl restart valuescan-signal"'
    if not run_command(cmd):
        print("  [WARN] Signal Monitor 重启失败")

    # 5. 检查服务状态
    print("\n[5/5] 检查服务状态...")
    cmd = f'ssh {VPS_HOST} "systemctl status valuescan-api valuescan-signal --no-pager"'
    run_command(cmd)

    print("\n" + "=" * 80)
    print("✅ 同步完成！")
    print("=" * 80)
    print("\n请验证:")
    print("1. 访问 Web 界面，检查配置页面是否正常")
    print("2. 触发 AI 简评，检查是否异步执行")
    print("3. 查看日志: ssh {} 'journalctl -u valuescan-signal -f'".format(VPS_HOST))

    return True

def main():
    """主函数"""
    print("VPS 同步工具")
    print(f"目标: {VPS_HOST}:{VPS_PATH}")
    print()

    # 检查 SSH 连接
    print("检查 SSH 连接...")
    if not run_command(f'ssh {VPS_HOST} "echo OK"'):
        print("❌ SSH 连接失败")
        print("请检查:")
        print("1. VPS_HOST 环境变量是否正确")
        print("2. SSH 密钥是否配置")
        print("3. VPS 是否可访问")
        return 1

    print("✅ SSH 连接正常\n")

    # 同步文件
    if not sync_files():
        print("❌ 同步失败")
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
