#!/usr/bin/env python3
"""
Bootstrap SSH key-based login for the ValueScan VPS (Windows-friendly).

This script:
1) Generates a dedicated RSA keypair if missing: ~/.ssh/valuescan_vps (+ .pub)
2) Connects to VPS using password (prompt or env var VALUESCAN_VPS_PASSWORD)
3) Appends the public key to ~/.ssh/authorized_keys (idempotent)
4) Verifies key-based login works (no password)

Security notes:
- Do NOT hardcode passwords in scripts.
- Prefer entering the password interactively when you run this script.
"""

from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path

import paramiko
from paramiko.ssh_exception import AuthenticationException, BadAuthenticationType, SSHException


DEFAULT_HOST = os.getenv("VALUESCAN_VPS_HOST", "82.158.88.34")
DEFAULT_USER = os.getenv("VALUESCAN_VPS_USER", "root")


def _default_key_path() -> Path:
    return Path.home() / ".ssh" / "valuescan_vps"


def _ensure_keypair(private_key_path: Path, bits: int = 3072) -> tuple[Path, str]:
    private_key_path.parent.mkdir(parents=True, exist_ok=True)
    public_key_path = private_key_path.with_suffix(".pub")

    if private_key_path.exists() and public_key_path.exists():
        pub_line = public_key_path.read_text(encoding="utf-8", errors="ignore").strip()
        return private_key_path, pub_line

    key = paramiko.RSAKey.generate(bits=bits)
    key.write_private_key_file(str(private_key_path))

    comment = f"valuescan@{os.environ.get('COMPUTERNAME') or 'windows'}"
    pub_line = f"{key.get_name()} {key.get_base64()} {comment}".strip()
    public_key_path.write_text(pub_line + "\n", encoding="utf-8")
    return private_key_path, pub_line


def _connect_password(host: str, user: str, password: str, port: int = 22) -> paramiko.SSHClient:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=host, username=user, password=password, port=port, timeout=30)
    return ssh


def _connect_key(host: str, user: str, key_file: Path, port: int = 22) -> paramiko.SSHClient:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=host, username=user, key_filename=str(key_file), port=port, timeout=30)
    return ssh


def _exec(ssh: paramiko.SSHClient, cmd: str) -> str:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")
    return (out + ("\n" + err if err else "")).strip()


def _install_pubkey(ssh: paramiko.SSHClient, pub_line: str) -> None:
    safe_pub = pub_line.replace("'", r"'\''")
    cmd = (
        "set -e; "
        "mkdir -p ~/.ssh; chmod 700 ~/.ssh; "
        "touch ~/.ssh/authorized_keys; chmod 600 ~/.ssh/authorized_keys; "
        f"grep -qxF '{safe_pub}' ~/.ssh/authorized_keys || echo '{safe_pub}' >> ~/.ssh/authorized_keys; "
        "echo OK"
    )
    result = _exec(ssh, cmd)
    if "OK" not in result:
        raise SystemExit(f"Failed to install key: {result}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Setup SSH key-based login for ValueScan VPS")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--user", default=DEFAULT_USER)
    parser.add_argument("--port", type=int, default=22)
    parser.add_argument("--key-file", default=str(_default_key_path()))
    parser.add_argument("--bits", type=int, default=3072)
    args = parser.parse_args()

    key_file = Path(args.key_file).expanduser()
    key_file, pub_line = _ensure_keypair(key_file, bits=int(args.bits))

    password = (os.environ.get("VALUESCAN_VPS_PASSWORD") or "").strip()
    if not password:
        password = getpass.getpass(f"SSH password for {args.user}@{args.host}: ")
    if not password:
        raise SystemExit("Missing password")

    print(f"Connecting to {args.user}@{args.host}:{args.port} with password...")
    ssh = _connect_password(args.host, args.user, password, port=int(args.port))
    try:
        _install_pubkey(ssh, pub_line)
        print("✅ Public key installed to ~/.ssh/authorized_keys")
    finally:
        ssh.close()

    print("Verifying key-based login (no password)...")
    try:
        ssh2 = _connect_key(args.host, args.user, key_file, port=int(args.port))
    except BadAuthenticationType as exc:
        allowed = getattr(exc, "allowed_types", None)
        allowed_display = ", ".join(allowed) if allowed else "unknown"
        print("❌ 服务器未启用 publickey 认证，无法免密登录。")
        print(f"   SSH 允许的认证方式: {allowed_display}")
        print("")
        print("Fix on VPS (login with password first):")
        print("- Ensure `PubkeyAuthentication yes` in `/etc/ssh/sshd_config`")
        print("- Ensure `AuthorizedKeysFile .ssh/authorized_keys` is enabled")
        print("- Ensure your user can use keys (e.g. `PermitRootLogin prohibit-password` or a non-root user)")
        print("- Then restart SSH: `systemctl restart sshd` (or `systemctl restart ssh`)")
        return 2
    except (AuthenticationException, SSHException) as exc:
        print("❌ Key-based login failed (server rejected the key).")
        print(f"   Error: {exc}")
        print("")
        print("Fix on VPS:")
        print("- Confirm the public key was appended to `~/.ssh/authorized_keys`")
        print("- Check `~/.ssh` permissions: `700` and `authorized_keys`: `600`")
        print("- Check `/etc/ssh/sshd_config` and restart sshd")
        return 2

    try:
        out = _exec(ssh2, "echo ok")
        if "ok" not in out:
            raise SystemExit(f"Key auth check failed: {out}")
        print("✅ Key-based login OK")
    finally:
        ssh2.close()

    print("")
    print("Next:")
    print(f"- Set env var VALUESCAN_VPS_KEY_FILE to: {key_file}")
    print("- Then run: .\\deploy_to_vps.ps1 -Mode runtime")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
