#!/usr/bin/env python3
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("82.158.88.34", username="root", password="Qq159741", look_for_keys=False, allow_agent=False)

# 检查drop-in配置
print("检查drop-in配置...")
stdin, stdout, stderr = ssh.exec_command("cat /etc/systemd/system/valuescan-signal.service.d/valuescan-env.conf")
content = stdout.read().decode()
error = stderr.read().decode()
print(content if content else error)

ssh.close()
