#!/usr/bin/env python3
"""
Deploy token refresher fix to VPS.

Usage:
  python scripts/deploy_token_fix.py
"""

import os
import sys
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("Installing paramiko...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "paramiko"], check=True)
    import paramiko

# VPS Configuration
VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PASSWORD = "Qq159741"

# Local paths
LOCAL_DIR = Path(__file__).resolve().parent.parent
FIX_SCRIPT = LOCAL_DIR / "scripts" / "fix_token_refresher_vps.py"
SERVICE_FILE = LOCAL_DIR / "valuescan-token-refresher.service"
CDP_REFRESHER = LOCAL_DIR / "signal_monitor" / "cdp_token_refresher.py"


def log(msg):
    print(f"[deploy] {msg}")


def main():
    log(f"Connecting to {VPS_HOST}...")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=30)
        log("Connected!")
        
        sftp = ssh.open_sftp()
        
        # Upload fix script
        log("Uploading fix script...")
        sftp.put(str(FIX_SCRIPT), "/root/valuescan/scripts/fix_token_refresher_vps.py")
        
        # Upload updated service file
        log("Uploading service file...")
        sftp.put(str(SERVICE_FILE), "/root/valuescan/valuescan-token-refresher.service")
        
        # Upload CDP refresher (in case it's updated)
        log("Uploading CDP refresher...")
        sftp.put(str(CDP_REFRESHER), "/root/valuescan/signal_monitor/cdp_token_refresher.py")
        
        sftp.close()
        
        # Create credentials file directly
        log("Creating credentials file...")
        cmd = '''cat > /root/valuescan/signal_monitor/valuescan_credentials.json << 'EOF'
{
  "email": "ymy_live@outlook.com",
  "password": "Qq159741."
}
EOF
chmod 600 /root/valuescan/signal_monitor/valuescan_credentials.json
'''
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdout.read()
        
        # Update env file
        log("Updating env file...")
        cmd = '''cat > /root/valuescan/config/valuescan.env << 'EOF'
VALUESCAN_LOGIN_METHOD=cdp
VALUESCAN_REFRESH_URL=https://api.valuescan.io/api/account/refreshToken
VALUESCAN_AUTO_RELOGIN=1
VALUESCAN_AUTO_RELOGIN_USE_BROWSER=1
VALUESCAN_AUTO_RELOGIN_COOLDOWN=300
VALUESCAN_PASSWORD=Qq159741.
VALUESCAN_EMAIL=ymy_live@outlook.com
VALUESCAN_CDP_PORT=9222
VALUESCAN_BROWSER_STARTUP_TIMEOUT=60
SOCKS5_PROXY=socks5://127.0.0.1:1080
EOF
'''
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdout.read()
        
        # Install service file
        log("Installing service file...")
        cmd = '''
cp /root/valuescan/valuescan-token-refresher.service /etc/systemd/system/
systemctl daemon-reload
'''
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdout.read()
        
        # Kill stale browsers
        log("Killing stale browsers...")
        cmd = "pkill -9 chromium 2>/dev/null; pkill -9 chrome 2>/dev/null; sleep 2"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdout.read()
        
        # Test CDP login
        log("Testing CDP login (this may take 1-2 minutes)...")
        cmd = '''cd /root/valuescan/signal_monitor && \
DISPLAY=:99 \
VALUESCAN_EMAIL=ymy_live@outlook.com \
VALUESCAN_PASSWORD=Qq159741. \
python3.9 cdp_token_refresher.py --once --force 2>&1'''
        
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=180)
        output = stdout.read().decode()
        errors = stderr.read().decode()
        
        log("CDP login output:")
        for line in output.split("\n")[-20:]:
            if line.strip():
                print(f"  {line}")
        if errors:
            log("Errors:")
            for line in errors.split("\n")[-5:]:
                if line.strip():
                    print(f"  [err] {line}")
        
        # Check token
        log("Checking token...")
        cmd = '''python3.9 -c "
import json
import base64
import time
from pathlib import Path

f = Path('/root/valuescan/signal_monitor/valuescan_localstorage.json')
if not f.exists():
    print('Token file not found')
    exit(1)

data = json.loads(f.read_text())
token = data.get('account_token', '')
if not token:
    print('No account_token')
    exit(1)

parts = token.split('.')
if len(parts) < 2:
    print('Invalid token')
    exit(1)

payload = parts[1] + '=' * (-len(parts[1]) % 4)
decoded = json.loads(base64.urlsafe_b64decode(payload))
exp = decoded.get('exp', 0)
remaining = exp - int(time.time())

if remaining > 0:
    print(f'Token valid for {remaining // 60} minutes ({remaining / 3600:.1f} hours)')
else:
    print(f'Token expired {-remaining} seconds ago')
    exit(1)
"
'''
        stdin, stdout, stderr = ssh.exec_command(cmd)
        output = stdout.read().decode().strip()
        log(f"Token status: {output}")
        
        # Restart services
        log("Restarting services...")
        cmd = '''
systemctl restart valuescan-token-refresher
sleep 2
systemctl restart valuescan-signal
sleep 2
systemctl status valuescan-token-refresher --no-pager -l | head -20
'''
        stdin, stdout, stderr = ssh.exec_command(cmd)
        output = stdout.read().decode()
        log("Service status:")
        for line in output.split("\n")[:15]:
            if line.strip():
                print(f"  {line}")
        
        log("=" * 50)
        log("Deployment complete!")
        log("=" * 50)
        
        ssh.close()
        return 0
        
    except Exception as exc:
        log(f"Error: {exc}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
