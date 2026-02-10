#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Issue and install SSL cert via acme.sh for a single domain.
"""
from __future__ import annotations

import os
import sys

import paramiko

DEFAULT_HOST = "43.128.227.29"
DEFAULT_USER = "root"
DEFAULT_PORT = 22
DEFAULT_DOMAIN = "cornna.abrdns.com"
DEFAULT_EMAIL = "ymy_live@outlook.com"
DEFAULT_SSL_DIR = "/etc/nginx/ssl"
DEFAULT_ACME_SH = "/root/.acme.sh/acme.sh"


def run_ssh(ssh: paramiko.SSHClient, cmd: str, check: bool = True) -> None:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=300)
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="ignore").strip()
    err = stderr.read().decode("utf-8", errors="ignore").strip()
    if out:
        print(out)
    if err:
        print(err, file=sys.stderr)
    if check and exit_status != 0:
        raise SystemExit(f"Command failed: {cmd}")


def main() -> None:
    host = os.getenv("VALUESCAN_VPS_HOST", DEFAULT_HOST)
    user = os.getenv("VALUESCAN_VPS_USER", DEFAULT_USER)
    port = int(os.getenv("VALUESCAN_VPS_PORT", str(DEFAULT_PORT)))
    domain = os.getenv("VALUESCAN_VPS_DOMAIN", DEFAULT_DOMAIN).strip()
    email = os.getenv("VALUESCAN_VPS_ACME_EMAIL", DEFAULT_EMAIL).strip()
    ssl_dir = os.getenv("VALUESCAN_VPS_SSL_DIR", DEFAULT_SSL_DIR).rstrip("/")
    acme_sh = os.getenv("VALUESCAN_VPS_ACME_SH", DEFAULT_ACME_SH)
    password = os.getenv("VALUESCAN_VPS_PASSWORD", "").strip()

    if not password:
        raise SystemExit("Missing VALUESCAN_VPS_PASSWORD env var.")
    if not domain:
        raise SystemExit("Missing VALUESCAN_VPS_DOMAIN.")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname=host,
        port=port,
        username=user,
        password=password,
        timeout=60,
        banner_timeout=60,
        auth_timeout=60,
    )

    print(f"Issuing SSL for {domain} on {host}...")
    run_ssh(ssh, f"{acme_sh} --version")
    run_ssh(
        ssh,
        "ACCOUNT_CONF=/root/.acme.sh/account.conf; "
        "if [ -f \"$ACCOUNT_CONF\" ]; then "
        f"sed -i \"s/^ACCOUNT_EMAIL=.*/ACCOUNT_EMAIL='{email}'/\" \"$ACCOUNT_CONF\"; "
        "else "
        f"echo \"ACCOUNT_EMAIL='{email}'\" > \"$ACCOUNT_CONF\"; "
        "fi",
    )
    run_ssh(ssh, f"{acme_sh} --register-account --server letsencrypt")
    run_ssh(ssh, f"mkdir -p {ssl_dir}/{domain}")
    run_ssh(
        ssh,
        f"{acme_sh} --issue --nginx -d {domain} --keylength ec-256 --server letsencrypt",
        check=False,
    )
    run_ssh(
        ssh,
        f"{acme_sh} --install-cert -d {domain} --ecc "
        f"--key-file {ssl_dir}/{domain}/key.pem "
        f"--fullchain-file {ssl_dir}/{domain}/cert.pem "
        f"--reloadcmd \"systemctl reload nginx\"",
    )
    run_ssh(ssh, "nginx -t")
    run_ssh(ssh, "systemctl reload nginx")

    ssh.close()
    print("SSL certificate installed.")


if __name__ == "__main__":
    main()
