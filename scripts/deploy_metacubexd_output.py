import os
from pathlib import Path
import paramiko

HOST = '82.158.88.34'
USER = 'root'
PASSWORD = 'Qq159741'

LOCAL_ROOT = Path(r"E:\project\valuescan\metacubexd")
LOCAL_OUTPUT = LOCAL_ROOT / ".output"
REMOTE_ROOT = "/root/valuescan/metacubexd"
REMOTE_OUTPUT = f"{REMOTE_ROOT}/.output"


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


def sftp_mkdirs(sftp, remote_path):
    parts = remote_path.strip('/').split('/')
    current = ''
    for part in parts:
        current += '/' + part
        try:
            sftp.stat(current)
        except FileNotFoundError:
            sftp.mkdir(current)


def sftp_put_dir(sftp, local_dir: Path, remote_dir: str):
    for root, dirs, files in os.walk(local_dir):
        rel = os.path.relpath(root, local_dir)
        rel = '' if rel == '.' else rel.replace('\\', '/')
        target_dir = f"{remote_dir}/{rel}" if rel else remote_dir
        sftp_mkdirs(sftp, target_dir)
        for file in files:
            local_path = Path(root) / file
            remote_path = f"{target_dir}/{file}"
            sftp.put(str(local_path), remote_path)


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
        if "metacubexd" in name or "clash" in name:
            run_ssh(ssh, f"docker restart {name}")
            return

    print("No service manager detected for metacubexd; please restart manually if needed.")


def main():
    if not LOCAL_OUTPUT.exists():
        raise SystemExit(f"Local .output not found: {LOCAL_OUTPUT}")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)

    run_ssh(ssh, f"rm -rf {REMOTE_OUTPUT}")

    sftp = ssh.open_sftp()
    sftp_put_dir(sftp, LOCAL_OUTPUT, REMOTE_OUTPUT)
    sftp.close()

    restart_service(ssh)
    ssh.close()
    print(".output deployed.")


if __name__ == '__main__':
    main()
