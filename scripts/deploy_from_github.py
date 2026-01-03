#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy to VPS by pulling from GitHub and syncing web/dist.
Keeps local sensitive/config files untouched on VPS.
"""
from __future__ import annotations

import os
import posixpath
import time
from pathlib import Path

import paramiko


DEFAULT_HOST = "82.158.88.34"
DEFAULT_USER = "root"
DEFAULT_PROJECT_ROOT = "/root/valuescan"
DEFAULT_WEB_ROOT = "/var/www/valuescan"


def _exec(ssh: paramiko.SSHClient, cmd: str, timeout: int = 180) -> str:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")
    return (out + ("\n" + err if err else "")).strip()


def _sftp_mkdirs(sftp: paramiko.SFTPClient, remote_path: str) -> None:
    remote_dir = posixpath.dirname(remote_path)
    parts = remote_dir.split("/")
    cur = ""
    for part in parts:
        if not part:
            continue
        cur = f"{cur}/{part}"
        try:
            sftp.stat(cur)
        except Exception:
            try:
                sftp.mkdir(cur)
            except Exception:
                pass


def _sync_dist(sftp: paramiko.SFTPClient, local_dist: Path, remote_dist: str) -> None:
    for path in local_dist.rglob("*"):
        if path.is_dir():
            continue
        rel = path.relative_to(local_dist).as_posix()
        remote = f"{remote_dist}/{rel}"
        _sftp_mkdirs(sftp, remote)
        sftp.put(str(path), remote)


def _git_env_prefix() -> str:
    return "GIT_SSL_NO_VERIFY=1 " if os.getenv("VALUESCAN_GIT_SSL_NO_VERIFY") == "1" else ""

def _move_untracked(ssh: paramiko.SSHClient, project_root: str, backup_dir: str) -> None:
    script = f"""
import os
import shutil
import subprocess

repo = {project_root!r}
backup = {backup_dir!r}
os.makedirs(backup, exist_ok=True)

out = subprocess.check_output(
    ["git", "-C", repo, "ls-files", "--others", "--exclude-standard"],
    stderr=subprocess.STDOUT,
).decode("utf-8", errors="ignore")
paths = [line.strip() for line in out.splitlines() if line.strip()]
count = 0
for rel in paths:
    src = os.path.join(repo, rel)
    if not os.path.exists(src):
        continue
    dst = os.path.join(backup, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(src, dst)
    count += 1
print(f"moved_untracked={{count}}")
"""
    _exec(ssh, f"python3 - <<'PY'\n{script}\nPY", timeout=300)


def _restore_untracked(ssh: paramiko.SSHClient, project_root: str, backup_dir: str) -> None:
    script = f"""
import os
import shutil

repo = {project_root!r}
backup = {backup_dir!r}
restored = 0
skipped = 0
if not os.path.exists(backup):
    print("backup_missing")
    raise SystemExit(0)

for root, _dirs, files in os.walk(backup):
    for name in files:
        src = os.path.join(root, name)
        rel = os.path.relpath(src, backup)
        dst = os.path.join(repo, rel)
        if os.path.exists(dst):
            skipped += 1
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        restored += 1

print(f"restored={{restored}} skipped={{skipped}}")
"""
    _exec(ssh, f"python3 - <<'PY'\n{script}\nPY", timeout=300)


def main() -> int:
    host = os.getenv("VALUESCAN_VPS_HOST", DEFAULT_HOST)
    user = os.getenv("VALUESCAN_VPS_USER", DEFAULT_USER)
    password = (os.getenv("VALUESCAN_VPS_PASSWORD") or "").strip()
    project_root = os.getenv("VALUESCAN_VPS_PROJECT_ROOT", DEFAULT_PROJECT_ROOT)
    web_root = os.getenv("VALUESCAN_VPS_WEB_ROOT", DEFAULT_WEB_ROOT)
    local_root = Path(__file__).resolve().parent.parent
    local_dist = local_root / "web" / "dist"

    if not password:
        print("Missing VALUESCAN_VPS_PASSWORD.")
        return 1
    if not local_dist.exists():
        print("Missing web/dist. Run npm -C web run build first.")
        return 1

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname=host,
        port=22,
        username=user,
        password=password,
        look_for_keys=False,
        allow_agent=False,
        timeout=30,
        banner_timeout=30,
        auth_timeout=30,
    )
    sftp = ssh.open_sftp()

    print("Updating repo from GitHub ...")
    env_prefix = _git_env_prefix()
    backup_dir = f"/root/valuescan_untracked_backup_{int(time.time())}"
    _move_untracked(ssh, project_root, backup_dir)

    # Commit local changes to avoid overwriting; keep local state intact
    _exec(ssh, f"cd {project_root} && git config user.name 'valuescan-local'", timeout=30)
    _exec(ssh, f"cd {project_root} && git config user.email 'valuescan-local@localhost'", timeout=30)
    _exec(ssh, f"cd {project_root} && git add -A", timeout=120)
    _exec(ssh, f"cd {project_root} && git commit -m 'vps local changes before sync' || true", timeout=120)

    pull_cmds = [
        f"cd {project_root} && {env_prefix}git fetch origin",
        f"cd {project_root} && git checkout master",
        f"cd {project_root} && git merge --no-ff --allow-unrelated-histories -X ours origin/master",
    ]
    for cmd in pull_cmds:
        result = _exec(ssh, cmd, timeout=300)
        if result:
            print(result)

    _restore_untracked(ssh, project_root, backup_dir)

    print("Syncing web/dist ...")
    _exec(ssh, f"mkdir -p {project_root}/web/dist && rm -rf {project_root}/web/dist/*", timeout=120)
    _sync_dist(sftp, local_dist, f"{project_root}/web/dist")
    if web_root:
        _exec(
            ssh,
            f"mkdir -p {web_root} && cp -r {project_root}/web/dist/* {web_root}/",
            timeout=120,
        )

    print("Restarting services ...")
    for svc in ("valuescan-api", "valuescan-signal", "valuescan-trader"):
        _exec(ssh, f"systemctl restart {svc}")

    sftp.close()
    ssh.close()
    print("Deployment completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
