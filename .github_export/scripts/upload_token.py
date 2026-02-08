#!/usr/bin/env python3
"""上传 token 到 VPS"""
import paramiko
import os
import json
import time

VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PASSWORD = os.environ.get("VALUESCAN_VPS_PASSWORD", "")

# Token 数据
TOKEN_DATA = {
    "account_token": "eyJhbGciOiJIUzUxMiJ9.eyJlbmRwb2ludCI6MSwiY3JlYXRlZCI6MTc2NTk3MTgzNTQ5Nywic2Vzc2lvbklkIjoiNGZiOTVmMjcxZGM3NDdkZWJiNGJjMGNjNDBlNDgwZDUiLCJ0eXBlIjoiYWNjb3VudF90b2tlbiIsImV4cCI6MTc2NTk3NTQzNSwidXNlcklkIjozMzQ1NSwiYWNjb3VudCI6InlteV9saXZlQG91dGxvb2suY29tIn0.DmIfpOIZ4dkYoFtyNB1ewKgu3rsWU16YMr7NUJY6prJy_1uR7jqeoJWfRuYEfqA7sS18cfF-FICsDwRpyuT3iA",
    "refresh_token": "eyJhbGciOiJIUzUxMiJ9.eyJlbmRwb2ludCI6MSwiY3JlYXRlZCI6MTc2NTk3MTgzNTQ5Nywic2Vzc2lvbklkIjoiNGZiOTVmMjcxZGM3NDdkZWJiNGJjMGNjNDBlNDgwZDUiLCJ0eXBlIjoicmVmcmVzaF90b2tlbiIsImV4cCI6MTc2NjIzMTAzNSwidXNlcklkIjozMzQ1NSwiYWNjb3VudCI6InlteV9saXZlQG91dGxvb2suY29tIn0.sZl3aCTPCscjSL--h4C_2fC6Rt-pWfbNMrNe_rio8j0OTyor48mNSkkJV0lorguWabkEUX_hfgY8PlSZFR5OdA",
    "language": "en-US"
}

def main():
    print("连接 VPS...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=30)
    print(f"已连接到 {VPS_HOST}")
    
    # 上传 token 文件
    print("\n上传 token 文件...")
    sftp = client.open_sftp()
    token_path = "/root/valuescan/signal_monitor/valuescan_localstorage.json"
    with sftp.file(token_path, "w") as f:
        f.write(json.dumps(TOKEN_DATA, indent=2, ensure_ascii=False))
    sftp.close()
    print(f"✓ Token 已写入: {token_path}")
    
    # 重启服务
    print("\n重启服务...")
    stdin, stdout, stderr = client.exec_command("systemctl restart valuescan-signal")
    exit_code = stdout.channel.recv_exit_status()
    print(f"✓ valuescan-signal 已重启" if exit_code == 0 else f"✗ 重启失败")
    
    # 等待服务启动
    print("\n等待服务启动...")
    time.sleep(5)
    
    # 检查日志
    print("\n最近日志:")
    stdin, stdout, stderr = client.exec_command("journalctl -u valuescan-signal -n 15 --no-pager")
    print(stdout.read().decode())
    
    client.close()
    print("\n完成!")

if __name__ == "__main__":
    main()
