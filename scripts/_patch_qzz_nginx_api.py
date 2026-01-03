import os
import paramiko

host = os.environ.get('VALUESCAN_VPS_HOST', '82.158.88.34')
user = os.environ.get('VALUESCAN_VPS_USER', 'root')
password = os.environ.get('VALUESCAN_VPS_PASSWORD')
if not password:
    raise SystemExit('VALUESCAN_VPS_PASSWORD not set')

remote_path = '/etc/nginx/conf.d/cornna.qzz.io.conf'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=host, username=user, password=password, timeout=30)

sftp = ssh.open_sftp()
with sftp.open(remote_path, 'r') as f:
    content = f.read().decode('utf-8', errors='ignore')

old = 'proxy_pass http://127.0.0.1:5000;'
new = 'proxy_pass http://127.0.0.1:5000/nofx/api/;'
if old not in content:
    raise SystemExit('proxy_pass line not found or already changed')

updated = content.replace(old, new, 1)

backup_path = remote_path + '.bak.api.' + os.popen('date +%Y%m%d%H%M%S').read().strip()
ssh.exec_command(f'cp {remote_path} {backup_path}')

with sftp.open(remote_path, 'w') as f:
    f.write(updated.encode('utf-8'))

sftp.close()
ssh.close()
print('Updated cornna.qzz.io.conf /api/ proxy_pass to /nofx/api/.')
