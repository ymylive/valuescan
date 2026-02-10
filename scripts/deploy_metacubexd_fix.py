import os
import sys
import time
from pathlib import Path

import paramiko

HOST = os.getenv("VALUESCAN_VPS_HOST", "82.158.88.34")
USER = os.getenv("VALUESCAN_VPS_USER", "root")
PASSWORD = os.getenv("VALUESCAN_VPS_PASSWORD", "Qq159741")

LOCAL_ROOT = Path(r"E:\project\valuescan")
LOCAL_FILE = LOCAL_ROOT / "metacubexd" / "composables" / "useApi.ts"

CANDIDATES = [
    "/root/valuescan/metacubexd",
    "/root/metacubexd",
    "/opt/valuescan/metacubexd",
    "/srv/valuescan/metacubexd",
    "/var/www/metacubexd",
]

FIND_BASES = ["/root", "/opt", "/srv", "/var/www"]


def run_ssh(ssh: paramiko.SSHClient, cmd: str, timeout: int = 120):
    print(f">>> {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    if out:
        print(out)
    if err:
        print(f"STDERR: {err}")
    return exit_code, out, err


def find_remote_root(ssh: paramiko.SSHClient) -> str | None:
    for candidate in CANDIDATES:
        code, _, _ = run_ssh(ssh, f"test -f {candidate}/package.json && echo OK")
        if code == 0:
            return candidate
    bases = " ".join(FIND_BASES)
    cmd = (
        f"find {bases} -maxdepth 4 -type d -name metacubexd 2>/dev/null | head -n 1"
    )
    code, out, _ = run_ssh(ssh, cmd)
    if code == 0:
        candidate = out.strip()
        if candidate:
            code, _, _ = run_ssh(ssh, f"test -f {candidate}/package.json && echo OK")
            if code == 0:
                return candidate
    return None


def detect_pkg_manager(ssh: paramiko.SSHClient) -> str:
    if run_ssh(ssh, "command -v pnpm")[0] == 0:
        return "pnpm"
    if run_ssh(ssh, "command -v npm")[0] == 0:
        return "npm"
    return ""


def restart_service(ssh: paramiko.SSHClient):
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
    if not LOCAL_FILE.exists():
        print(f"Local file not found: {LOCAL_FILE}")
        sys.exit(1)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print(f"Connecting to {HOST} as {USER}...")
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    print("Connected.")

    remote_root = find_remote_root(ssh)
    if not remote_root:
        print("Could not find metacubexd directory on VPS.")
        ssh.close()
        sys.exit(1)

    remote_file = f"{remote_root}/composables/useApi.ts"
    print(f"Deploying to: {remote_file}")

    sftp = ssh.open_sftp()
    sftp.put(str(LOCAL_FILE), remote_file)
    sftp.close()

    pkg = detect_pkg_manager(ssh)
    if not pkg:
        print("No npm/pnpm found on VPS.")
        ssh.close()
        sys.exit(1)

    run_ssh(ssh, f"cd {remote_root} && {pkg} -v")

    if pkg == "pnpm":
        build_cmd = "pnpm build"
    else:
        build_cmd = "npm run build"

    code, _, _ = run_ssh(ssh, f"cd {remote_root} && {build_cmd}", timeout=900)
    if code != 0:
        if pkg == "pnpm":
            run_ssh(ssh, f"cd {remote_root} && pnpm install --frozen-lockfile", timeout=900)
            run_ssh(ssh, f"cd {remote_root} && pnpm build", timeout=900)
        else:
            run_ssh(ssh, f"cd {remote_root} && npm install", timeout=900)
            run_ssh(ssh, f"cd {remote_root} && npm run build", timeout=900)

    restart_service(ssh)
    ssh.close()
    print("Deployment complete.")


if __name__ == "__main__":
    main()
