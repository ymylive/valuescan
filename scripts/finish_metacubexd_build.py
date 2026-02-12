import os
import time
import paramiko

HOST = '82.158.88.34'
USER = 'root'
PASSWORD = os.getenv("VALUESCAN_VPS_PASSWORD", "")
REMOTE_ROOT = '/root/valuescan/metacubexd'


def run_ssh(ssh, cmd, timeout=120):
    print(f">>> {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode(errors='replace')
    err = stderr.read().decode(errors='replace')
    if out:
        print(out)
    if err:
        print(f"STDERR: {err}")
    return exit_code, out, err


def restart_service(ssh):
    code, out, _ = run_ssh(
        ssh,
        "systemctl list-units --type=service --all | grep -i metacubexd || true",
    )
    service = ""
    for line in out.splitlines():
        parts = line.split()
        if parts:
            service = parts[0]
            break
    if service:
        run_ssh(ssh, f"systemctl restart {service}")
        run_ssh(ssh, f"systemctl status {service} --no-pager | head -n 10")
        return

    code, out, _ = run_ssh(ssh, "command -v pm2 >/dev/null 2>&1 && pm2 list || true")
    if "metacubexd" in out:
        run_ssh(ssh, "pm2 restart metacubexd")
        return

    code, out, _ = run_ssh(
        ssh, "command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' || true"
    )
    for name in out.splitlines():
        if "metacubexd" in name:
            run_ssh(ssh, f"docker restart {name}")
            return

    print("No service manager detected for metacubexd; please restart manually if needed.")


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)

    wait_start = time.time()
    while True:
        _, out, _ = run_ssh(ssh, "pgrep -f 'npm install' || true")
        if not out.strip():
            break
        if time.time() - wait_start > 1800:
            print("Timeout waiting for npm install to finish")
            ssh.close()
            return
        print("npm install still running, waiting 10s...")
        time.sleep(10)

    run_ssh(ssh, f"cd {REMOTE_ROOT} && npm run build", timeout=1200)
    restart_service(ssh)
    ssh.close()
    print("Build/Restart complete.")


if __name__ == '__main__':
    main()
