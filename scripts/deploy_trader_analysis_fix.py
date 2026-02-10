#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署带单员分析模块修复
- 5分钟限时模块（管理员豁免）
- 图表优化（修复乱码）
- AI提示词增强
- Chrome MCP数据获取
"""
import os
import sys
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("错误: 未安装 paramiko 库")
    print("请运行: pip install paramiko")
    sys.exit(1)

# VPS 配置
VPS_HOST = "43.133.12.98"
VPS_USER = "root"
VPS_PORT = 22
VPS_PATH = "/root/valuescan"
VPS_PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "Qq159741")

LOCAL_ROOT = Path(__file__).resolve().parent.parent

# 需要上传的文件
FILES_TO_UPLOAD = [
    "signal_monitor/bot_config.json",
    "signal_monitor/telegram_bot.py",
    "signal_monitor/trader_chart_generator.py",
    "signal_monitor/trader_evaluation_prompt.py",
    "signal_monitor/binance_copytrade_mcp.py",
    "signal_monitor/binance_copytrade_api.py",
]


def run_ssh_command(ssh, command, show_output=True):
    """执行 SSH 命令"""
    try:
        stdin, stdout, stderr = ssh.exec_command(command, timeout=120)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode("utf-8", errors="ignore")
        error = stderr.read().decode("utf-8", errors="ignore")
        if show_output:
            if output:
                print(output)
            if error and "WARNING" not in error:
                print(error, file=sys.stderr)
        return exit_status == 0
    except Exception as e:
        print(f"执行失败: {e}")
        return False


def upload_file(sftp, local_path, remote_path):
    """上传单个文件"""
    try:
        # 确保远程目录存在
        remote_dir = os.path.dirname(remote_path)
        try:
            sftp.stat(remote_dir)
        except FileNotFoundError:
            sftp.mkdir(remote_dir)

        sftp.put(str(local_path), remote_path)
        return True
    except Exception as e:
        print(f"上传失败 {local_path}: {e}")
        return False


def main():
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

    print("=" * 50)
    print("  部署带单员分析模块修复")
    print("=" * 50)
    print(f"\nVPS: {VPS_USER}@{VPS_HOST}:{VPS_PORT}")
    print(f"路径: {VPS_PATH}\n")

    # 连接 SSH
    print("正在连接 VPS...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            print(f"尝试连接 ({attempt}/{max_retries})...")
            ssh.connect(
                hostname=VPS_HOST,
                port=VPS_PORT,
                username=VPS_USER,
                password=VPS_PASSWORD,
                timeout=60,
                banner_timeout=60
            )
            print("SSH 连接成功\n")
            break
        except Exception as e:
            print(f"连接失败: {e}")
            if attempt == max_retries:
                print("已达最大重试次数，退出")
                sys.exit(1)
            print("等待5秒后重试...")
            import time
            time.sleep(5)

    # 上传文件
    print("正在上传文件...")
    sftp = ssh.open_sftp()

    for file_path in FILES_TO_UPLOAD:
        local_path = LOCAL_ROOT / file_path
        remote_path = f"{VPS_PATH}/{file_path}"

        if not local_path.exists():
            print(f"  跳过 (不存在): {file_path}")
            continue

        print(f"  上传: {file_path}")
        if upload_file(sftp, local_path, remote_path):
            print(f"    完成")
        else:
            print(f"    失败")

    sftp.close()
    print("\n文件上传完成\n")

    # 安装中文字体（如果不存在）
    print("检查并安装中文字体...")
    run_ssh_command(ssh, "apt-get update -qq && apt-get install -y -qq fonts-wqy-microhei fonts-wqy-zenhei >/dev/null 2>&1 && fc-cache -f", show_output=False)
    print("  中文字体检查完成")

    # 清除 matplotlib 字体缓存
    print("清除 matplotlib 字体缓存...")
    run_ssh_command(ssh, "rm -rf ~/.cache/matplotlib", show_output=False)
    print("  缓存清除完成")

    # 重启服务
    print("正在重启服务...")

    # 重启 monitor 服务
    if run_ssh_command(ssh, "systemctl restart valuescan-monitor", show_output=False):
        print("  valuescan-monitor 重启成功")
    else:
        print("  valuescan-monitor 重启失败")

    ssh.close()

    print("\n" + "=" * 50)
    print("  部署完成!")
    print("=" * 50)
    print("\n修改内容:")
    print("  - 5分钟查询限时（管理员豁免）")
    print("  - 图表中文乱码修复")
    print("  - AI提示词增强（多维度分析）")
    print("  - Chrome MCP数据获取模块")
    print("\n配置管理员:")
    print(f"  编辑 {VPS_PATH}/signal_monitor/bot_config.json")
    print("  在 admin_users 数组中添加 Telegram 用户 ID")


if __name__ == "__main__":
    main()
