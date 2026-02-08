#!/usr/bin/env python3
"""
Fix systemd services to load valuescan.env environment file.

This script:
1. Creates systemd drop-in configs for all valuescan services
2. Updates valuescan.env with correct browser settings
3. Cleans up stale browser processes and profiles
4. Restarts services and shows logs

Required env:
  VALUESCAN_VPS_PASSWORD      SSH password
  VALUESCAN_EMAIL             ValueScan login email
  VALUESCAN_PASSWORD          ValueScan login password

Optional env:
  VALUESCAN_VPS_HOST (default: 82.158.88.34)
  VALUESCAN_VPS_USER (default: root)
"""

from __future__ import annotations

import os
import subprocess
import sys


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
        subprocess.run([sys.executable, "-m", "pip", "install", "paramiko"], check=True)
        import paramiko
        return paramiko


def _exec(ssh, cmd: str, desc: str, timeout: int = 180) -> str:
    print(f"\n[{desc}]")
    print(f"$ {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out.strip())
    if err:
        print(f"STDERR: {err.strip()}")
    if exit_code != 0:
        print(f"Warning: command exited with {exit_code}")
    return out


def main() -> int:
    paramiko = _get_paramiko()

    host = os.environ.get("VALUESCAN_VPS_HOST", "82.158.88.34")
    user = os.environ.get("VALUESCAN_VPS_USER", "root")
    password = _require_env("VALUESCAN_VPS_PASSWORD")
    email = _require_env("VALUESCAN_EMAIL")
    login_password = _require_env("VALUESCAN_PASSWORD")

    print(f"Connecting to {user}@{host} ...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password, timeout=30)

    # Step 1: Create systemd drop-in configs to load env file
    print("\n" + "="*60)
    print("Step 1: Creating systemd drop-in configs for env loading")
    print("="*60)

    services = ["valuescan-signal", "valuescan-token-refresher", "valuescan-monitor"]
    
    for service in services:
        drop_in_dir = f"/etc/systemd/system/{service}.service.d"
        drop_in_file = f"{drop_in_dir}/valuescan-env.conf"
        
        _exec(ssh, f"mkdir -p {drop_in_dir}", f"Create drop-in dir for {service}")
        
        drop_in_content = """[Service]
EnvironmentFile=/opt/valuescan/config/valuescan.env
"""
        cmd = f"cat > {drop_in_file} << 'DROPINEOF'\n{drop_in_content}DROPINEOF"
        _exec(ssh, cmd, f"Create drop-in config for {service}")

    # Step 2: Update valuescan.env with correct settings
    print("\n" + "="*60)
    print("Step 2: Updating valuescan.env with browser settings")
    print("="*60)

    # First ensure the config directory exists
    _exec(ssh, "mkdir -p /opt/valuescan/config", "Ensure config directory exists")

    env_content = f"""# ValueScan Environment Configuration
VALUESCAN_LOGIN_METHOD=browser
VALUESCAN_AUTO_RELOGIN=1
VALUESCAN_AUTO_RELOGIN_USE_BROWSER=1
VALUESCAN_BROWSER_PATH=/usr/bin/chromium-browser
VALUESCAN_KILL_STALE_BROWSERS=1
VALUESCAN_LOGIN_PROFILE_DIR=/opt/valuescan/chrome-login-profile
VALUESCAN_EMAIL={email}
VALUESCAN_PASSWORD={login_password}
"""
    
    # Write env file
    cmd = f"cat > /opt/valuescan/config/valuescan.env << 'ENVEOF'\n{env_content}ENVEOF"
    _exec(ssh, cmd, "Write valuescan.env")
    _exec(ssh, "chmod 600 /opt/valuescan/config/valuescan.env", "Secure env file permissions")

    # Step 3: Clean up stale browser processes and profiles
    print("\n" + "="*60)
    print("Step 3: Cleaning up stale browser processes and profiles")
    print("="*60)

    _exec(ssh, "pkill -9 chromium || true", "Kill chromium processes")
    _exec(ssh, "pkill -9 chrome || true", "Kill chrome processes")
    _exec(ssh, "rm -rf /opt/valuescan/chrome-login-profile", "Remove old login profile")

    # Step 4: Reload systemd and restart services
    print("\n" + "="*60)
    print("Step 4: Reloading systemd and restarting services")
    print("="*60)

    _exec(ssh, "systemctl daemon-reload", "Reload systemd daemon")
    _exec(ssh, "systemctl restart valuescan-token-refresher", "Restart token-refresher")
    _exec(ssh, "systemctl restart valuescan-signal", "Restart signal service")

    # Wait a moment for services to start
    import time
    print("\nWaiting 5 seconds for services to initialize...")
    time.sleep(5)

    # Step 5: Show logs
    print("\n" + "="*60)
    print("Step 5: Service logs")
    print("="*60)

    print("\n--- valuescan-token-refresher logs (last 50 lines) ---")
    _exec(ssh, "journalctl -u valuescan-token-refresher -n 50 --no-pager", "Token refresher logs")

    print("\n--- valuescan-signal logs (last 30 lines) ---")
    _exec(ssh, "journalctl -u valuescan-signal -n 30 --no-pager", "Signal service logs")

    # Verify env is loaded
    print("\n" + "="*60)
    print("Step 6: Verify environment loading")
    print("="*60)
    
    _exec(ssh, "cat /opt/valuescan/config/valuescan.env | grep -v PASSWORD", "Current env config (passwords hidden)")
    _exec(ssh, "systemctl show valuescan-token-refresher --property=EnvironmentFiles", "Check EnvironmentFiles property")

    ssh.close()
    
    print("\n" + "="*60)
    print("DONE!")
    print("="*60)
    print("""
If you still see 'account_token not found', ValueScan likely requires
verification code/2FA. You'll need to do ONE manual login with GUI:

1. SSH to VPS with X11 forwarding or use VNC
2. Run:
   cd /root/valuescan/signal_monitor
   python3.9 token_refresher.py --email "your_email" --password "your_pass" --once --no-headless

After successful GUI login, headless mode can handle token refresh.
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
