#!/usr/bin/env python3
"""
本地编译 NOFX 后端并上传到 VPS
"""

import paramiko
import os
import subprocess
import tempfile
import shutil
from pathlib import Path

VPS_HOST = "82.158.88.34"
VPS_USER = "root"
VPS_PASSWORD = os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741')
NOFX_DIR = "/opt/nofx"

def run_cmd(cmd, cwd=None, timeout=300):
    """运行本地命令"""
    print(f"  > {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if result.stdout:
        print(result.stdout)
    if result.returncode != 0 and result.stderr:
        print(f"错误: {result.stderr}")
    return result.returncode == 0

def main():
    print("=" * 60)
    print("本地编译 NOFX 后端并上传到 VPS")
    print("=" * 60)
    
    # 连接 VPS
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD)
    sftp = ssh.open_sftp()
    
    # 创建临时目录
    temp_dir = Path(tempfile.mkdtemp(prefix="nofx_build_"))
    print(f"\n临时目录: {temp_dir}")
    
    try:
        # 1. 从 VPS 下载修改后的源码
        print("\n1. 从 VPS 下载修改后的 Go 源码...")
        
        files_to_download = [
            "trader/binance_futures.go",
            "trader/auto_trader.go",
            "manager/trader_manager.go",
            "go.mod",
            "go.sum",
        ]
        
        # 下载整个项目结构
        stdin, stdout, stderr = ssh.exec_command(f'cd {NOFX_DIR} && find . -name "*.go" -type f')
        go_files = stdout.read().decode().strip().split('\n')
        
        for go_file in go_files:
            if not go_file:
                continue
            remote_path = f"{NOFX_DIR}/{go_file}"
            local_path = temp_dir / go_file
            local_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                sftp.get(remote_path, str(local_path))
            except Exception as e:
                print(f"  跳过: {go_file} ({e})")
        
        # 下载 go.mod 和 go.sum
        for f in ["go.mod", "go.sum"]:
            sftp.get(f"{NOFX_DIR}/{f}", str(temp_dir / f))
        
        print(f"  下载了 {len(go_files)} 个 Go 文件")
        
        # 2. 本地编译
        print("\n2. 本地编译 (Linux amd64)...")
        
        # 检查本地是否有 Go
        if not run_cmd("go version"):
            print("错误: 本地未安装 Go，请先安装 Go")
            return
        
        # 设置交叉编译环境变量
        env = os.environ.copy()
        env["GOOS"] = "linux"
        env["GOARCH"] = "amd64"
        env["CGO_ENABLED"] = "0"
        
        # 编译
        print("  编译中...")
        result = subprocess.run(
            ["go", "build", "-o", "nofx", "."],
            cwd=str(temp_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if result.returncode != 0:
            print(f"编译失败: {result.stderr}")
            return
        
        binary_path = temp_dir / "nofx"
        if not binary_path.exists():
            print("编译失败: 未生成二进制文件")
            return
        
        print(f"  编译成功: {binary_path} ({binary_path.stat().st_size / 1024 / 1024:.1f} MB)")
        
        # 3. 上传到 VPS
        print("\n3. 上传到 VPS...")
        
        # 停止现有服务
        print("  停止现有 NOFX 服务...")
        stdin, stdout, stderr = ssh.exec_command('systemctl stop nofx 2>/dev/null || pkill -f "/opt/nofx/nofx" || true')
        stdout.read()
        
        # 备份旧二进制
        stdin, stdout, stderr = ssh.exec_command(f'mv {NOFX_DIR}/nofx {NOFX_DIR}/nofx.bak 2>/dev/null || true')
        stdout.read()
        
        # 上传新二进制
        print("  上传二进制文件...")
        sftp.put(str(binary_path), f"{NOFX_DIR}/nofx")
        
        # 设置执行权限
        stdin, stdout, stderr = ssh.exec_command(f'chmod +x {NOFX_DIR}/nofx')
        stdout.read()
        
        print("  上传完成!")
        
        # 4. 验证
        print("\n4. 验证...")
        stdin, stdout, stderr = ssh.exec_command(f'ls -la {NOFX_DIR}/nofx')
        print(stdout.read().decode())
        
        # 测试运行
        print("  测试运行...")
        stdin, stdout, stderr = ssh.exec_command(f'{NOFX_DIR}/nofx --version 2>&1 || {NOFX_DIR}/nofx -h 2>&1 | head -5')
        print(stdout.read().decode())
        
        print("\n" + "=" * 60)
        print("编译和上传完成!")
        print("=" * 60)
        print(f"\n二进制文件位置: {NOFX_DIR}/nofx")
        print("启动命令: cd /opt/nofx && ./nofx")
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)
        sftp.close()
        ssh.close()

if __name__ == "__main__":
    main()
