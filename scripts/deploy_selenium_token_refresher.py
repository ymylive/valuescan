#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Selenium-based token refresher to VPS.

This script deploys the tested and working selenium_token_refresher.py to the VPS.

Required env:
  VALUESCAN_VPS_PASSWORD      SSH password
  VALUESCAN_EMAIL             ValueScan login email (optional, can use credentials file)
  VALUESCAN_PASSWORD          ValueScan login password (optional, can use credentials file)

Optional env:
  VALUESCAN_VPS_HOST (default: 82.158.88.34)
  VALUESCAN_VPS_USER (default: root)
"""

import os
import subprocess
import sys
import json
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


def _require_env(key: str) -> str:
    val = (os.environ.get(key) or "").strip()
    if not val:
        print(f"Error: environment variable {key} is required.")
        sys.exit(1)
    return val


def _get_paramiko():
    try:
        import paramiko
        return paramiko
    except ImportError:
        print("Installing paramiko...")
        subprocess.run([sys.executable, "-m", "pip", "install", "paramiko"], check=True)
        import paramiko
        return paramiko


def _exec(ssh, cmd: str, desc: str) -> tuple:
    """Execute command and return (exit_code, stdout, stderr)"""
    print(f"\n[{desc}]")
    print(f"$ {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=180)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode()
    err = stderr.read().decode()

    if out:
        print(out.strip())
    if err:
        print(f"STDERR: {err.strip()}")
    if exit_code != 0:
        print(f"Warning: command exited with {exit_code}")

    return exit_code, out, err


def main() -> int:
    paramiko = _get_paramiko()

    # Get connection details
    host = os.environ.get("VALUESCAN_VPS_HOST", "82.158.88.34")
    user = os.environ.get("VALUESCAN_VPS_USER", "root")
    password = _require_env("VALUESCAN_VPS_PASSWORD")

    # Get credentials (optional if using credentials file)
    email = os.environ.get("VALUESCAN_EMAIL", "").strip()
    login_password = os.environ.get("VALUESCAN_PASSWORD", "").strip()

    print(f"Connecting to {user}@{host} ...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password, timeout=30)
    sftp = ssh.open_sftp()

    print("\n" + "="*60)
    print("STEP 1: Upload selenium_token_refresher.py")
    print("="*60)

    # Upload the selenium token refresher script
    local_script = "signal_monitor/selenium_token_refresher.py"
    remote_script = "/root/valuescan/signal_monitor/selenium_token_refresher.py"

    if not os.path.exists(local_script):
        print(f"Error: {local_script} not found!")
        ssh.close()
        return 1

    print(f"Uploading {local_script} -> {remote_script}")
    sftp.put(local_script, remote_script)
    sftp.chmod(remote_script, 0o755)
    print("[OK] Upload complete")

    print("\n" + "="*60)
    print("STEP 2: Upload or create credentials file")
    print("="*60)

    cred_path = "/root/valuescan/signal_monitor/valuescan_credentials.json"

    # Check if local credentials file exists
    local_cred = "signal_monitor/valuescan_credentials.json"
    if os.path.exists(local_cred):
        print(f"Uploading {local_cred} -> {cred_path}")
        sftp.put(local_cred, cred_path)
        sftp.chmod(cred_path, 0o600)
        print("[OK] Credentials uploaded from local file")
    elif email and login_password:
        print(f"Creating credentials file from environment variables")
        cred_payload = json.dumps({"email": email, "password": login_password}, indent=2)
        with sftp.open(cred_path, "w") as f:
            f.write(cred_payload)
        sftp.chmod(cred_path, 0o600)
        print("[OK] Credentials created from env vars")
    else:
        print("Warning: No credentials provided. Assuming credentials file already exists on VPS.")

    sftp.close()

    print("\n" + "="*60)
    print("STEP 3: Install dependencies")
    print("="*60)

    # Install selenium if not already installed
    _exec(ssh, "pip3 install selenium --quiet", "Install selenium")

    # Check if chromium is installed
    exit_code, out, err = _exec(ssh, "which chromium-browser || which chromium || which google-chrome", "Check Chrome/Chromium")
    if exit_code != 0:
        print("\nWarning: Chrome/Chromium not found. Installing...")
        _exec(ssh, "yum install -y chromium || apt-get install -y chromium-browser", "Install Chromium")

    # Install Xvfb for virtual display
    print("\nInstalling Xvfb for virtual display...")
    _exec(ssh, "yum install -y xorg-x11-server-Xvfb || apt-get install -y xvfb", "Install Xvfb")

    # Start Xvfb on display :99
    print("\nStarting Xvfb on display :99...")
    _exec(ssh, "pkill -9 Xvfb || true", "Kill existing Xvfb")
    _exec(ssh, "nohup Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &", "Start Xvfb")

    print("\n" + "="*60)
    print("STEP 4: Update systemd service")
    print("="*60)

    # Create systemd service file content
    service_content = """[Unit]
Description=ValueScan Token Refresher (Selenium)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/valuescan/signal_monitor
ExecStart=/usr/bin/python3 /root/valuescan/signal_monitor/selenium_token_refresher.py --interval 0.8
Restart=always
RestartSec=300
StandardOutput=journal
StandardError=journal

Environment=PYTHONUNBUFFERED=1
Environment=DISPLAY=:99
Environment=SELENIUM_HEADLESS=false

[Install]
WantedBy=multi-user.target
"""

    # Upload service file
    service_path = "/etc/systemd/system/valuescan-token-refresher.service"
    print(f"Creating {service_path}")
    with ssh.open_sftp().open(service_path, "w") as f:
        f.write(service_content)
    print("[OK] Service file created")

    print("\n" + "="*60)
    print("STEP 5: Reload and restart service")
    print("="*60)

    # Stop the old service first
    _exec(ssh, "systemctl stop valuescan-token-refresher", "Stop old service")

    # Reload systemd
    _exec(ssh, "systemctl daemon-reload", "Reload systemd")

    # Enable service
    _exec(ssh, "systemctl enable valuescan-token-refresher", "Enable service")

    # Start service
    _exec(ssh, "systemctl start valuescan-token-refresher", "Start service")

    # Wait a moment for service to start
    import time
    time.sleep(2)

    # Check service status
    _exec(ssh, "systemctl status valuescan-token-refresher --no-pager -l | head -20", "Service status")

    print("\n" + "="*60)
    print("STEP 6: Verify deployment")
    print("="*60)

    # Check if token file exists
    _exec(ssh, "ls -lh /root/valuescan/signal_monitor/valuescan_localstorage.json 2>/dev/null || echo 'Token file not yet created'", "Check token file")

    # Show recent logs
    _exec(ssh, "journalctl -u valuescan-token-refresher -n 30 --no-pager", "Recent logs")

    ssh.close()

    print("\n" + "="*60)
    print("DEPLOYMENT COMPLETE!")
    print("="*60)
    print("\nService commands:")
    print("  systemctl status valuescan-token-refresher")
    print("  systemctl restart valuescan-token-refresher")
    print("  journalctl -u valuescan-token-refresher -f")
    print("\nToken file location:")
    print("  /root/valuescan/signal_monitor/valuescan_localstorage.json")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
