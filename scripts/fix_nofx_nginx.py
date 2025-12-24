#!/usr/bin/env python3
"""修复 NOFX Nginx 配置为静态文件服务"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

print("修复 NOFX Nginx 配置...")

# 更新 cornna.abrdns.com.conf 中的 NOFX 配置
fix_cmd = '''
# 备份配置
cp /etc/nginx/conf.d/cornna.abrdns.com.conf /etc/nginx/conf.d/cornna.abrdns.com.conf.bak.$(date +%Y%m%d%H%M%S)

# 创建新的 NOFX 配置块
cat > /tmp/nofx_location.conf << 'NOFX_EOF'
    # NOFX 静态文件服务
    location = /nofx {
        return 301 /nofx/;
    }

    location /nofx/ {
        alias /opt/nofx/web/dist/;
        try_files $uri $uri/ /nofx/index.html;
    }
NOFX_EOF

# 检查并替换现有的 nofx 配置
# 先删除旧的 nofx location 块
sed -i '/location = \\/nofx {/,/^    }/d' /etc/nginx/conf.d/cornna.abrdns.com.conf
sed -i '/location \\^~ \\/nofx\\/ {/,/^    }/d' /etc/nginx/conf.d/cornna.abrdns.com.conf

# 在 server 块中添加新配置（在 location / 之前）
# 找到 HTTPS server 块并添加
python3 << 'PYEOF'
import re

with open('/etc/nginx/conf.d/cornna.abrdns.com.conf', 'r') as f:
    content = f.read()

# 读取新配置
with open('/tmp/nofx_location.conf', 'r') as f:
    nofx_config = f.read()

# 检查是否已有 nofx 配置
if 'location /nofx/' not in content or 'alias /opt/nofx' not in content:
    # 在 listen 443 的 server 块中，在 location / 之前插入
    # 找到 HTTPS server 块
    pattern = r'(server\\s*\\{[^}]*listen\\s+443[^}]*)(location\\s+/\\s*\\{)'
    
    def replacer(match):
        return match.group(1) + nofx_config + '\\n\\n    ' + match.group(2)
    
    # 简单方法：在第一个 "location / {" 之前插入
    if 'location / {' in content:
        content = content.replace('location / {', nofx_config + '\\n\\n    location / {', 1)
    
    with open('/etc/nginx/conf.d/cornna.abrdns.com.conf', 'w') as f:
        f.write(content)
    print("已添加 NOFX 静态文件配置")
else:
    print("NOFX 配置已存在")
PYEOF

# 测试配置
nginx -t

# 重载
systemctl reload nginx

echo "完成"
'''

stdin, stdout, stderr = ssh.exec_command(fix_cmd, timeout=120)
print(stdout.read().decode())
print(stderr.read().decode())

# 验证
print("\n验证 NOFX 访问:")
stdin, stdout, stderr = ssh.exec_command('curl -s --max-time 5 -I http://127.0.0.1/nofx/ | head -10')
print(stdout.read().decode())

stdin, stdout, stderr = ssh.exec_command('curl -s --max-time 5 http://127.0.0.1/nofx/ | head -20')
print(stdout.read().decode())

ssh.close()
