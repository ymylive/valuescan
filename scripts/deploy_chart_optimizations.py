#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署图表优化和AI增强到VPS
包含所有优化：图表视觉、AI数据投喂、宏观分析、Gemini配置
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

DEFAULT_HOST = "82.158.88.34"
DEFAULT_USER = "root"
VALUESCAN_DIR = "/root/valuescan"

def _get_password() -> str | None:
    password = os.environ.get("VALUESCAN_VPS_PASSWORD", "")
    if password:
        return password
    print("❌ VALUESCAN_VPS_PASSWORD not set.")
    return None

def _exec(ssh: paramiko.SSHClient, cmd: str, timeout: int = 300) -> str:
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="ignore")
        err = stderr.read().decode("utf-8", errors="ignore")
        return (out + ("\n" + err if err else "")).strip()
    except Exception as exc:
        return f"[exec error] {cmd}: {exc}"

def _sftp_put_mkdir(sftp: paramiko.SFTPClient, local: Path, remote: str) -> None:
    """上传文件，自动创建目录"""
    remote_dir = remote.rsplit("/", 1)[0]
    parts = remote_dir.split("/")
    cur = ""
    for part in parts:
        if not part:
            continue
        cur += f"/{part}"
        try:
            sftp.stat(cur)
        except Exception:
            try:
                sftp.mkdir(cur)
            except Exception:
                pass
    sftp.put(str(local), remote)

def main():
    print("=" * 80)
    print("部署图表优化和AI增强到VPS")
    print("=" * 80)

    password = _get_password()
    if not password:
        return 1

    host = os.environ.get("VALUESCAN_VPS_HOST", DEFAULT_HOST)
    user = os.environ.get("VALUESCAN_VPS_USER", DEFAULT_USER)

    print(f"\n[连接] 连接到 {user}@{host}...")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname=host, username=user, password=password, timeout=30)
        sftp = ssh.open_sftp()
        print("[成功] SSH连接成功")

        # 需要部署的文件列表
        files_to_deploy = [
            # 图表生成器（优化后）
            ("signal_monitor/chart_pro_v10.py", f"{VALUESCAN_DIR}/signal_monitor/chart_pro_v10.py"),

            # 辅助线绘制器（优化后）
            ("signal_monitor/auxiliary_line_drawer.py", f"{VALUESCAN_DIR}/signal_monitor/auxiliary_line_drawer.py"),

            # AI市场分析（增强数据投喂）
            ("signal_monitor/ai_market_analysis.py", f"{VALUESCAN_DIR}/signal_monitor/ai_market_analysis.py"),

            # AI宏观分析（优化prompt和格式）
            ("signal_monitor/ai_market_summary.py", f"{VALUESCAN_DIR}/signal_monitor/ai_market_summary.py"),

            # AI配置（Gemini 3 Pro）
            ("signal_monitor/ai_summary_config.json", f"{VALUESCAN_DIR}/signal_monitor/ai_summary_config.json"),
        ]

        print(f"\n[上传] 开始上传文件...")
        for local_path, remote_path in files_to_deploy:
            local_file = Path(local_path)
            if not local_file.exists():
                print(f"  [跳过] 本地文件不存在: {local_path}")
                continue

            print(f"  [上传] {local_path} -> {remote_path}")
            try:
                _sftp_put_mkdir(sftp, local_file, remote_path)
                print(f"     [成功]")
            except Exception as e:
                print(f"     [失败] {e}")

        print(f"\n[检查] 检查VPS文件编码...")
        # 检查文件是否有BOM或编码问题
        check_cmd = f"""
cd {VALUESCAN_DIR}/signal_monitor
for f in chart_pro_v10.py ai_market_summary.py ai_market_analysis.py auxiliary_line_drawer.py; do
    if [ -f "$f" ]; then
        # 检查BOM
        if file "$f" | grep -q "UTF-8 Unicode (with BOM)"; then
            echo "修复BOM: $f"
            sed -i '1s/^\\xEF\\xBB\\xBF//' "$f"
        fi
        # 转换为Unix格式
        dos2unix "$f" 2>/dev/null || sed -i 's/\\r$//' "$f"
        echo "OK: $f"
    fi
done
"""
        result = _exec(ssh, check_cmd, timeout=60)
        print(result)

        print(f"\n[重启] 重启服务...")
        restart_cmd = f"""
systemctl restart valuescan-signal
systemctl restart valuescan-api
sleep 2
systemctl status valuescan-signal --no-pager | head -20
"""
        result = _exec(ssh, restart_cmd, timeout=60)
        print(result)

        print(f"\n[验证] 验证部署...")
        verify_cmd = f"""
cd {VALUESCAN_DIR}
echo "=== 文件大小 ==="
ls -lh signal_monitor/chart_pro_v10.py signal_monitor/ai_market_summary.py signal_monitor/ai_summary_config.json 2>/dev/null
echo ""
echo "=== AI配置 ==="
cat signal_monitor/ai_summary_config.json 2>/dev/null
echo ""
echo "=== 服务状态 ==="
systemctl is-active valuescan-signal valuescan-api
"""
        result = _exec(ssh, verify_cmd, timeout=30)
        print(result)

        sftp.close()
        ssh.close()

        print("\n" + "=" * 80)
        print("[完成] 部署完成！")
        print("=" * 80)
        print("\n已部署的优化:")
        print("  1. 图表视觉优化（70%元素减少）")
        print("  2. 智能标签位置管理")
        print("  3. 删除清算分析和修复乱码")
        print("  4. AI数据投喂增强（MACD、价格变化、成交量）")
        print("  5. 宏观分析升级（专业6部分框架）")
        print("  6. AI模型切换到Gemini 3 Pro")
        print("\n提示:")
        print("  - 查看日志: journalctl -u valuescan-signal -f")
        print("  - 测试图表: 等待下一个信号触发")
        print("  - 测试宏观分析: 等待定时任务（每小时）")

        return 0

    except Exception as e:
        print(f"\n[错误] 部署失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
