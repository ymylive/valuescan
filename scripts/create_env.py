#!/usr/bin/env python3
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("82.158.88.34", username="root", password="Qq159741", look_for_keys=False, allow_agent=False)

# 创建config目录和环境文件
print("创建环境文件...")
commands = [
    "mkdir -p /root/valuescan/config",
    "touch /root/valuescan/config/valuescan.env",
    "systemctl daemon-reload",
    "systemctl restart valuescan-signal"
]

for cmd in commands:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    stdout.channel.recv_exit_status()
    print(f"执行: {cmd}")

print("\n完成！")
ssh.close()
