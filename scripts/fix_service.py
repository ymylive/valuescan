#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复VPS服务配置问题
"""
import paramiko

VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PASSWORD = "Qq159741"

def fix_service():
    print("连接VPS...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD,
                   look_for_keys=False, allow_agent=False)

        # 检查systemd服务文件
        print("检查服务配置...")
        stdin, stdout, stderr = ssh.exec_command("cat /etc/systemd/system/valuescan-signal.service")
        service_content = stdout.read().decode()
        print(service_content)

        ssh.close()
        return True

    except Exception as e:
        print(f"失败: {e}")
        return False

if __name__ == '__main__':
    fix_service()
