#!/usr/bin/env python3
"""
部署前端到 VPS - 使用 rsync
"""
import os
import subprocess

VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "")

if not VPS_PASSWORD:
    print("Error: VALUESCAN_VPS_PASSWORD environment variable not set")
    exit(1)

# 使用 sshpass + scp 上传
print("上传前端文件...")
cmd = f'sshpass -p "{VPS_PASSWORD}" scp -r -o StrictHostKeyChecking=no web/dist/* {VPS_USER}@{VPS_HOST}:/root/valuescan/web/dist/'
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
if result.returncode != 0:
    print(f"Error: {result.stderr}")
else:
    print("上传成功!")

# 重启服务
print("\n重启 API 服务...")
cmd = f'sshpass -p "{VPS_PASSWORD}" ssh -o StrictHostKeyChecking=no {VPS_USER}@{VPS_HOST} "systemctl restart valuescan-api && sleep 2 && systemctl status valuescan-api --no-pager | head -10"'
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print(result.stdout)

print("\nDone!")
