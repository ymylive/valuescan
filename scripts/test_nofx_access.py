#!/usr/bin/env python3
"""测试 NOFX 访问并修复 valuescan.conf"""

import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('82.158.88.34', username='root', password=os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741'))

# 测试 HTTPS 访问
print('测试 HTTPS NOFX 访问:')
stdin, stdout, stderr = ssh.exec_command('curl -sk --max-time 5 https://127.0.0.1/nofx/ | head -30')
print(stdout.read().decode() or '(无响应)')

print('\n测试外部域名访问:')
stdin, stdout, stderr = ssh.exec_command('curl -sk --max-time 5 https://cornna.abrdns.com/nofx/ | head -30')
print(stdout.read().decode() or '(无响应)')

# 修复 valuescan.conf
print('\n修复 valuescan.conf...')
valuescan_conf = '''server {
    listen 80;
    listen [::]:80;
    server_name 82.158.88.34;

    root /opt/valuescan/web/dist;
    index index.html;

    # NOFX 静态文件
    location = /nofx {
        return 301 /nofx/;
    }

    location /nofx/ {
        alias /opt/nofx/web/dist/;
        try_files $uri $uri/ /nofx/index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }

    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 600s;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
'''

sftp = ssh.open_sftp()
with sftp.open('/etc/nginx/conf.d/valuescan.conf', 'w') as f:
    f.write(valuescan_conf)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('nginx -t && systemctl reload nginx')
print(stdout.read().decode())
print(stderr.read().decode())

# 再次测试
print('\n再次测试 HTTP 访问 (IP):')
stdin, stdout, stderr = ssh.exec_command('curl -s --max-time 5 http://82.158.88.34/nofx/ | head -30')
print(stdout.read().decode() or '(无响应)')

ssh.close()
print('\n完成!')
