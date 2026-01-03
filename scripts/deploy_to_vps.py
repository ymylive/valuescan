#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ValueScan VPS 自动部署脚本 (使用 paramiko)
使用环境变量 VALUESCAN_VPS_PASSWORD 存储密码
"""
import os
import sys
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("错误: 未安装 paramiko 库")
    print("请运行: pip install paramiko")
    sys.exit(1)

# VPS 配置（支持环境变量覆盖）
VPS_HOST = os.environ.get("VALUESCAN_VPS_HOST", "82.158.88.34")
VPS_USER = os.environ.get("VALUESCAN_VPS_USER", "root")
VPS_PORT = int(os.environ.get("VALUESCAN_VPS_PORT", "22"))
VPS_PATH = os.environ.get("VALUESCAN_VPS_PATH", "/root/valuescan")
VPS_BRANCH = os.environ.get("VALUESCAN_VPS_BRANCH", "").strip()
FORCE_RESET = os.environ.get("VALUESCAN_VPS_FORCE_RESET", "").strip() == "1"
SYNC_MODE = os.environ.get("VALUESCAN_VPS_SYNC_MODE", "git").strip().lower()
UPLOAD_PATHS_RAW = os.environ.get("VALUESCAN_VPS_UPLOAD_PATHS", "").strip()

LOCAL_ROOT = Path(__file__).resolve().parent.parent
SKIP_DIR_PREFIXES = [
    ".git",
    ".github",
    ".idea",
    ".vscode",
    "__pycache__",
    "logs",
    "output",
    "data",
    "screenshots",
    "web/node_modules",
    "web/dist",
    "signal_monitor/output",
    "signal_monitor/chrome-debug-profile",
]
SKIP_FILE_SUFFIXES = [".log"]
SKIP_FILE_NAMES = {"nul", "valuescan-web-dist.tar.gz"}

def run_ssh_command(ssh, command, show_output=True, capture_output=False):
    """执行 SSH 命令"""
    try:
        stdin, stdout, stderr = ssh.exec_command(command, timeout=300)
        exit_status = stdout.channel.recv_exit_status()

        output = stdout.read().decode("utf-8", errors="ignore")
        error = stderr.read().decode("utf-8", errors="ignore")

        if show_output:
            if output:
                print(output)
            if error and "WARNING" not in error:
                print(error, file=sys.stderr)

        if capture_output:
            return exit_status == 0, output.strip(), error.strip()
        return exit_status == 0
    except Exception as e:
        print(f"执行失败: {e}")
        if capture_output:
            return False, "", str(e)
        return False

def get_current_branch(ssh):
    ok, output, _ = run_ssh_command(
        ssh,
        f"cd {VPS_PATH} && git rev-parse --abbrev-ref HEAD",
        show_output=False,
        capture_output=True,
    )
    if ok and output:
        return output.splitlines()[-1].strip()
    return ""

def _should_skip_dir(rel_path: Path) -> bool:
    if rel_path == Path("."):
        return False
    rel_posix = rel_path.as_posix()
    for prefix in SKIP_DIR_PREFIXES:
        if rel_posix == prefix or rel_posix.startswith(prefix + "/"):
            return True
    return False

def _should_skip_file(rel_path: Path) -> bool:
    if rel_path.name in SKIP_FILE_NAMES:
        return True
    for suffix in SKIP_FILE_SUFFIXES:
        if rel_path.name.endswith(suffix):
            return True
    return False

def _add_paths_to_tar(tar, base_paths):
    for base_path in base_paths:
        abs_path = (LOCAL_ROOT / base_path).resolve()
        if not abs_path.exists():
            continue
        if abs_path.is_file():
            rel_file = abs_path.relative_to(LOCAL_ROOT)
            if _should_skip_file(rel_file) or _should_skip_dir(rel_file.parent):
                continue
            tar.add(abs_path, arcname=str(rel_file))
            continue
        for base, dirs, files in os.walk(abs_path, topdown=True):
            base_path = Path(base)
            rel_base = base_path.relative_to(LOCAL_ROOT)
            if _should_skip_dir(rel_base):
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if not _should_skip_dir(rel_base / d)]
            for file_name in files:
                rel_file = rel_base / file_name
                if _should_skip_file(rel_file):
                    continue
                tar.add(base_path / file_name, arcname=str(rel_file))

def _create_upload_archive(base_paths=None) -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="valuescan_upload_"))
    archive_path = temp_dir / "valuescan_upload.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        targets = base_paths or [Path(".")]
        _add_paths_to_tar(tar, targets)
    return archive_path

def _upload_workspace(ssh, base_paths=None) -> bool:
    archive_path = _create_upload_archive(base_paths)
    remote_archive = f"/tmp/valuescan_upload_{int(time.time())}.tar.gz"
    sftp = ssh.open_sftp()
    try:
        sftp.put(str(archive_path), remote_archive)
    finally:
        sftp.close()
    if not run_ssh_command(ssh, f"mkdir -p {VPS_PATH}"):
        return False
    if not run_ssh_command(ssh, f"tar -xzf {remote_archive} -C {VPS_PATH}"):
        return False
    if not run_ssh_command(ssh, f"rm -f {remote_archive}"):
        return False
    try:
        archive_path.unlink(missing_ok=True)
    except Exception:
        pass
    return True

def _collect_changed_paths() -> list[Path]:
    try:
        output = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=str(LOCAL_ROOT),
            text=True,
        )
    except Exception:
        return []

    paths = []
    for line in output.splitlines():
        if not line:
            continue
        status = line[:2]
        if "?" in status or "D" in status:
            continue
        if "M" not in status and "A" not in status and "R" not in status:
            continue
        payload = line[3:].strip()
        if " -> " in payload:
            payload = payload.split(" -> ", 1)[-1].strip()
        if payload:
            paths.append(Path(payload))
    return paths

def _parse_upload_paths(raw: str) -> list[Path]:
    if not raw:
        return []
    return [Path(p.strip()) for p in raw.split(",") if p.strip()]

def main():
    # 设置 Windows 控制台编码
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

    print("=" * 50)
    print("  ValueScan VPS 自动部署")
    print("=" * 50)
    print(f"\nVPS: {VPS_USER}@{VPS_HOST}:{VPS_PORT}")
    print(f"路径: {VPS_PATH}\n")

    # 获取密码
    password = os.environ.get('VALUESCAN_VPS_PASSWORD')
    if not password:
        print("错误: 未设置 VPS 密码环境变量")
        print("\n请先设置密码:")
        print("  Windows: set VALUESCAN_VPS_PASSWORD=your_password")
        print("  Linux/Mac: export VALUESCAN_VPS_PASSWORD=your_password")
        sys.exit(1)

    # 连接 SSH
    print("正在连接 VPS...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(
            hostname=VPS_HOST,
            port=VPS_PORT,
            username=VPS_USER,
            password=password,
            timeout=30
        )
        print("✓ SSH 连接成功\n")
    except Exception as e:
        print(f"连接失败: {e}")
        sys.exit(1)

    branch = VPS_BRANCH or get_current_branch(ssh) or "master"
    upload_paths_override = _parse_upload_paths(UPLOAD_PATHS_RAW)

    steps = []
    if SYNC_MODE in {"upload", "upload-min"}:
        steps.append(("上传本地代码", None))
    else:
        if FORCE_RESET:
            steps.append(("拉取最新代码", f"cd {VPS_PATH} && git fetch origin && git reset --hard origin/{branch}"))
        else:
            steps.append(("拉取最新代码", f"cd {VPS_PATH} && git fetch origin && git checkout {branch} && git pull --ff-only origin {branch}"))

    steps.extend([
        ("安装前端依赖", f"cd {VPS_PATH}/web && npm install"),
        ("构建前端", f"cd {VPS_PATH}/web && npm run build"),
        ("同步前端到 Nginx 目录", f"mkdir -p /var/www/valuescan && cp -r {VPS_PATH}/web/dist/* /var/www/valuescan/"),
        ("重启 Nginx", "systemctl restart nginx"),
        ("重启 API 服务", "systemctl restart valuescan-api"),
        ("重启信号监控", "systemctl restart valuescan-signal"),
        ("重启交易机器人", "systemctl restart valuescan-trader"),
    ])

    success = True
    for i, (desc, cmd) in enumerate(steps, 1):
        print(f"[{i}/{len(steps)}] {desc}...")
        if desc == "上传本地代码":
            upload_paths = None
            if upload_paths_override:
                upload_paths = upload_paths_override
            elif SYNC_MODE == "upload-min":
                upload_paths = _collect_changed_paths()
                if not upload_paths:
                    upload_paths = None
            if not _upload_workspace(ssh, upload_paths):
                print(f"步骤失败: {desc}")
                success = False
                break
        else:
            if not run_ssh_command(ssh, cmd):
                print(f"步骤失败: {desc}")
                success = False
                break
        print(f"✓ {desc}完成\n")

    ssh.close()

    if success:
        print("=" * 50)
        print("  ✓ 部署完成!")
        print("=" * 50)
        print("\n已重启服务:")
        print("  - valuescan-api (API 服务)")
        print("  - valuescan-signal (信号监控)")
        print("  - valuescan-trader (交易机器人)")
        print()
    else:
        print("\n部署失败，请检查错误信息")
        sys.exit(1)

if __name__ == "__main__":
    main()
