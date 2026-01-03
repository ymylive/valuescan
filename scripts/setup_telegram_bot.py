#!/usr/bin/env python3
"""配置 Telegram Bot 到 VPS"""
import paramiko
import os

VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "")

# Telegram 配置
TELEGRAM_BOT_TOKEN = "8574875999:AAGV2QmoHXMVVnsH2MCZL03Pa2V5wpqzGEk"
TELEGRAM_CHAT_ID = "-1003428496854"

def main():
    if not VPS_PASSWORD:
        print("❌ 请设置环境变量 VALUESCAN_VPS_PASSWORD")
        return
    
    print("连接 VPS...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=30)
    print(f"✓ 已连接到 {VPS_HOST}")
    
    config_path = "/root/valuescan/signal_monitor/config.py"
    
    # 读取现有配置
    print("\n读取现有配置...")
    stdin, stdout, stderr = client.exec_command(f"cat {config_path}")
    config_content = stdout.read().decode()
    
    if not config_content:
        print("❌ 配置文件不存在或为空")
        client.close()
        return
    
    # 更新 TELEGRAM_BOT_TOKEN
    lines = config_content.split('\n')
    new_lines = []
    for line in lines:
        if line.strip().startswith('TELEGRAM_BOT_TOKEN'):
            new_lines.append(f'TELEGRAM_BOT_TOKEN = "{TELEGRAM_BOT_TOKEN}"')
            print(f"✓ 更新 TELEGRAM_BOT_TOKEN")
        elif line.strip().startswith('TELEGRAM_CHAT_ID'):
            new_lines.append(f'TELEGRAM_CHAT_ID = "{TELEGRAM_CHAT_ID}"')
            print(f"✓ 更新 TELEGRAM_CHAT_ID")
        else:
            new_lines.append(line)
    
    new_config = '\n'.join(new_lines)
    
    # 写回配置
    print("\n写入配置...")
    sftp = client.open_sftp()
    with sftp.file(config_path, 'w') as f:
        f.write(new_config)
    sftp.close()
    print(f"✓ 配置已写入: {config_path}")
    
    # 重启服务
    print("\n重启服务...")
    stdin, stdout, stderr = client.exec_command("systemctl restart valuescan-signal")
    exit_code = stdout.channel.recv_exit_status()
    print("✓ valuescan-signal 已重启" if exit_code == 0 else "✗ 重启失败")
    
    # 检查服务状态
    print("\n检查服务状态...")
    stdin, stdout, stderr = client.exec_command("systemctl status valuescan-signal --no-pager -l | head -20")
    print(stdout.read().decode())
    
    # 查看最近日志
    print("\n最近日志:")
    stdin, stdout, stderr = client.exec_command("journalctl -u valuescan-signal -n 10 --no-pager")
    print(stdout.read().decode())
    
    client.close()
    print("\n✅ Telegram Bot 配置完成!")
    print(f"   Bot: @Valuescancornnabot")
    print(f"   频道: https://t.me/valuescan_cornna")

if __name__ == "__main__":
    main()
