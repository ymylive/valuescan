#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import paramiko
import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("82.158.88.34", username="root", password="Qq159741",
           look_for_keys=False, allow_agent=False)

print("检查VPS上的中文字体...")
stdin, stdout, stderr = ssh.exec_command(
    "fc-list :lang=zh | grep -i 'wenquanyi\\|dejavu' | head -5"
)
fonts = stdout.read().decode('utf-8', errors='ignore')
print(fonts if fonts else "未找到中文字体")

print("\n安装中文字体...")
stdin, stdout, stderr = ssh.exec_command(
    "yum install -y wqy-microhei-fonts 2>&1 || "
    "apt-get install -y fonts-wqy-microhei 2>&1"
)
exit_status = stdout.channel.recv_exit_status()
install_output = stdout.read().decode('utf-8', errors='ignore')
print(install_output[-500:] if len(install_output) > 500 else install_output)

ssh.close()
print("\n完成！")
