#!/usr/bin/env python3
"""部署巨鲸数据模块到VPS"""

import paramiko
import os
import time

VPS_HOST = "43.133.12.98"
VPS_USER = "root"
VPS_PORT = 22
VPS_PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "Qq159741")
REMOTE_PATH = "/root/valuescan/signal_monitor"

FILES_TO_UPLOAD = [
    ("signal_monitor/whale_data.py", "whale_data.py"),
    ("signal_monitor/ai_market_analysis.py", "ai_market_analysis.py"),
    ("signal_monitor/ai_market_summary.py", "ai_market_summary.py"),
    ("signal_monitor/ai_signal_analysis.py", "ai_signal_analysis.py"),
    ("signal_monitor/anomaly_detector/detector.py", "anomaly_detector/detector.py"),
    ("signal_monitor/trader_evaluation_prompt.py", "trader_evaluation_prompt.py"),
    ("signal_monitor/binance_copytrade_api.py", "binance_copytrade_api.py"),
    ("signal_monitor/trader_analyzer.py", "trader_analyzer.py"),
    ("signal_monitor/telegram_bot.py", "telegram_bot.py"),
    ("signal_monitor/macro_event_monitor.py", "macro_event_monitor.py"),
    ("signal_monitor/ai_signal_scheduler.py", "ai_signal_scheduler.py"),
    ("signal_monitor/config.py", "config.py"),
    ("signal_monitor/telegram.py", "telegram.py"),
    # AI配置文件
    ("signal_monitor/ai_signal_config.json", "ai_signal_config.json"),
    ("signal_monitor/ai_market_summary_config.json", "ai_market_summary_config.json"),
    ("signal_monitor/ai_summary_config.json", "ai_summary_config.json"),
    ("signal_monitor/ai_overlays_config.json", "ai_overlays_config.json"),
    ("signal_monitor/ai_key_levels_config.json", "ai_key_levels_config.json"),
]

def create_ssh_client(max_retries=3):
    """创建SSH连接，带重试"""
    for attempt in range(max_retries):
        try:
            print(f"[{attempt+1}/{max_retries}] 连接VPS {VPS_HOST}...")
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                VPS_HOST,
                port=VPS_PORT,
                username=VPS_USER,
                password=VPS_PASSWORD,
                timeout=60,
                banner_timeout=60,
                auth_timeout=60
            )
            print("SSH连接成功")
            return client
        except Exception as e:
            print(f"连接失败: {e}")
            if attempt < max_retries - 1:
                print("等待5秒后重试...")
                time.sleep(5)
    return None

def upload_files(sftp, local_base):
    """上传文件"""
    for local_rel, remote_name in FILES_TO_UPLOAD:
        local_path = os.path.join(local_base, local_rel)
        remote_path = f"{REMOTE_PATH}/{remote_name}"

        if not os.path.exists(local_path):
            print(f"[跳过] 本地文件不存在: {local_path}")
            continue

        print(f"上传: {local_rel} -> {remote_path}")
        try:
            sftp.put(local_path, remote_path)
            print(f"  成功")
        except Exception as e:
            print(f"  失败: {e}")

def restart_service(client):
    """重启服务"""
    print("\n重启 valuescan-monitor 服务...")
    stdin, stdout, stderr = client.exec_command("systemctl restart valuescan-monitor")
    exit_code = stdout.channel.recv_exit_status()

    if exit_code == 0:
        print("服务重启成功")
    else:
        print(f"服务重启失败: {stderr.read().decode()}")

    # 检查服务状态
    time.sleep(2)
    stdin, stdout, stderr = client.exec_command("systemctl status valuescan-monitor --no-pager -l | head -20")
    print(stdout.read().decode())

def main():
    print("=" * 50)
    print("部署巨鲸数据模块到VPS")
    print("=" * 50)

    # 获取本地项目路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_base = os.path.dirname(script_dir)
    print(f"本地项目路径: {local_base}")

    # 连接VPS
    client = create_ssh_client()
    if not client:
        print("无法连接VPS，部署失败")
        return

    try:
        sftp = client.open_sftp()

        # 上传文件
        print("\n上传文件...")
        upload_files(sftp, local_base)

        sftp.close()

        # 重启服务
        restart_service(client)

        print("\n" + "=" * 50)
        print("部署完成!")
        print("=" * 50)

    finally:
        client.close()

if __name__ == "__main__":
    main()
