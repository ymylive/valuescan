#!/usr/bin/env python3
"""修复 NOFX Nginx 配置"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print("查看当前 Nginx 配置...")

# 查看当前配置
stdin, stdout, stderr = ssh.exec_command('cat /etc/nginx/conf.d/cornna.abrdns.com.conf')
current_config = stdout.read().decode()
print("当前配置长度:", len(current_config))

# 创建正确的 NOFX 配置
# 需要将 proxy_pass 改为 alias 静态文件服务
fix_commands = [
    # 备份
    'cp /etc/nginx/conf.d/cornna.abrdns.com.conf /etc/nginx/conf.d/cornna.abrdns.com.conf.bak2',
    
    # 替换 /nofx/ 的 proxy_pass 为 alias
    "sed -i 's|location \\^~ /nofx/ {|location /nofx/ {|g' /etc/nginx/conf.d/cornna.abrdns.com.conf",
    
    # 在 /nofx/ location 中替换 proxy 配置为 alias
    # 这比较复杂，我们直接重写整个 nofx 部分
]

# 直接用 Python 修改配置
new_nofx_block = '''    # NOFX 静态文件
    location = /nofx {
        return 301 /nofx/;
    }

    location /nofx/ {
        alias /opt/nofx/web/dist/;
        try_files $uri $uri/ /nofx/index.html;
    }'''

# 检查是否需要修改
if 'alias /opt/nofx/web/dist/' in current_config:
    print("NOFX 静态文件配置已存在，无需修改")
else:
    print("需要修改 NOFX 配置...")
    
    # 移除旧的 nofx proxy 配置，添加新的 alias 配置
    # 使用 Python 处理
    import re
    
    # 移除所有 nofx 相关的 location 块
    # 匹配 location = /nofx { ... } 和 location ^~ /nofx/ { ... }
    lines = current_config.split('\n')
    new_lines = []
    skip_until_close = 0
    
    for line in lines:
        if skip_until_close > 0:
            if '{' in line:
                skip_until_close += line.count('{')
            if '}' in line:
                skip_until_close -= line.count('}')
            continue
        
        if 'location' in line and '/nofx' in line:
            skip_until_close = 1
            continue
        
        new_lines.append(line)
    
    # 在第一个 "location / {" 之前插入新配置
    result_lines = []
    inserted = False
    for line in new_lines:
        if not inserted and 'location / {' in line:
            result_lines.append(new_nofx_block)
            result_lines.append('')
            inserted = True
        result_lines.append(line)
    
    new_config = '\n'.join(result_lines)
    
    # 写入新配置
    # 使用 sftp 写入
    sftp = ssh.open_sftp()
    with sftp.open('/etc/nginx/conf.d/cornna.abrdns.com.conf', 'w') as f:
        f.write(new_config)
    sftp.close()
    
    print("配置已更新")

# 测试并重载
print("\n测试 Nginx 配置...")
stdin, stdout, stderr = ssh.exec_command('nginx -t')
print(stdout.read().decode())
print(stderr.read().decode())

print("\n重载 Nginx...")
stdin, stdout, stderr = ssh.exec_command('systemctl reload nginx')
print(stdout.read().decode() or "OK")

# 验证
print("\n验证 NOFX 访问:")
stdin, stdout, stderr = ssh.exec_command('curl -s --max-time 5 http://127.0.0.1/nofx/ | head -30')
result = stdout.read().decode()
print(result if result else "(无响应)")

ssh.close()
