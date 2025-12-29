#!/usr/bin/env python3
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("82.158.88.34", username="root", password="Qq159741", look_for_keys=False, allow_agent=False)

# 检查文件
stdin, stdout, stderr = ssh.exec_command("ls -la /root/valuescan/signal_monitor/start_polling.py")
print(stdout.read().decode())

# 检查Python
stdin, stdout, stderr = ssh.exec_command("which python3.9 && python3.9 --version")
print(stdout.read().decode())

# 重新加载systemd
stdin, stdout, stderr = ssh.exec_command("systemctl daemon-reload && systemctl start valuescan-signal")
stdout.channel.recv_exit_status()
print("Service restarted")

ssh.close()
