from pathlib import Path
import paramiko

HOST = '82.158.88.34'
USER = 'root'
PASSWORD = 'Qq159741'

REMOTE_CONFIG = '/var/www/valuescan/clash/config.js'
BACKEND_URL = 'https://cornna.qzz.io/clash-api'

content = f"window.__METACUBEXD_CONFIG__ = {{\n  defaultBackendURL: '{BACKEND_URL}',\n}}\n"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)

sftp = ssh.open_sftp()
with sftp.open(REMOTE_CONFIG, 'w') as f:
    f.write(content)

sftp.close()
ssh.close()
print(f'Updated {REMOTE_CONFIG}')
