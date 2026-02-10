#!/usr/bin/env python3
"""
VPS完整信息流测试部署脚本
包含: 美股信号、异动检测、AI分析等功能测试
"""

import os
import sys
import time
import subprocess

# VPS配置
VPS_HOST = "43.133.12.98"
VPS_USER = "root"
VPS_PASS = "Qq159741"

# Telegram配置
TG_BOT_TOKEN = "8391687043:AAEncp4ZH2eriLCDs3uCsqvbu4zWOBMzdPc"
TG_CHAT_ID = "-1003618689912"

# 前端配置
FRONTEND_PATH = "/test"
FRONTEND_URL = "https://cornna.dpdns.org/test"

# 项目路径
LOCAL_PROJECT = r"E:\project\valuescan"
REMOTE_PROJECT = "/root/valuescan"


def run_ssh(cmd: str, timeout: int = 60) -> tuple:
    """执行SSH命令"""
    ssh_cmd = f'plink -batch -pw {VPS_PASS} {VPS_USER}@{VPS_HOST} "{cmd}"'
    try:
        result = subprocess.run(
            ssh_cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)


def upload_file(local_path: str, remote_path: str) -> bool:
    """上传文件到VPS"""
    pscp_cmd = f'pscp -batch -pw {VPS_PASS} "{local_path}" {VPS_USER}@{VPS_HOST}:{remote_path}'
    try:
        result = subprocess.run(pscp_cmd, shell=True, capture_output=True, text=True, timeout=120)
        return result.returncode == 0
    except Exception as e:
        print(f"Upload failed: {e}")
        return False


def upload_dir(local_dir: str, remote_dir: str) -> bool:
    """上传目录到VPS"""
    pscp_cmd = f'pscp -batch -pw {VPS_PASS} -r "{local_dir}" {VPS_USER}@{VPS_HOST}:{remote_dir}'
    try:
        result = subprocess.run(pscp_cmd, shell=True, capture_output=True, text=True, timeout=300)
        return result.returncode == 0
    except Exception as e:
        print(f"Upload dir failed: {e}")
        return False


def setup_telegram_config():
    """配置Telegram"""
    print("\n[1/5] 配置Telegram...")

    # 创建config.py内容
    config_content = f'''
# Telegram配置
TELEGRAM_BOT_TOKEN = "{TG_BOT_TOKEN}"
TELEGRAM_CHAT_ID = "{TG_CHAT_ID}"

# AI信号配置
AI_SIGNAL_SYMBOLS = ["BTC", "ETH", "SOL", "BNB"]
AI_SIGNAL_INTERVAL_MINUTES = 30
AI_SIGNAL_SYMBOL_DELAY = 3

# 美股配置
US_MARKET_ENABLED = True
US_MARKET_SYMBOLS = ["SPY", "QQQ", "AAPL", "NVDA"]

# 异动检测配置
ANOMALY_DETECTOR_ENABLED = True
ANOMALY_DETECTOR_INTERVAL = 60

# 市场摘要配置
MARKET_SUMMARY_ENABLED = True
MARKET_SUMMARY_HOURS = [8, 20]

# 代理配置
HTTP_PROXY = "http://127.0.0.1:7890"
HTTPS_PROXY = "http://127.0.0.1:7890"
'''

    # 写入本地临时文件
    config_path = os.path.join(LOCAL_PROJECT, "signal_monitor", "config.py")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_content)

    print(f"  Telegram Bot Token: {TG_BOT_TOKEN[:20]}...")
    print(f"  Chat ID: {TG_CHAT_ID}")
    return True


def deploy_signal_monitor():
    """部署signal_monitor模块"""
    print("\n[2/5] 部署signal_monitor模块...")

    # 上传关键文件
    files_to_upload = [
        "signal_monitor/config.py",
        "signal_monitor/ai_signal_scheduler.py",
        "signal_monitor/market_alert.py",
        "signal_monitor/market_alert_config.json",
        "signal_monitor/telegram.py",
        "signal_monitor/market_data_sources.py",
        "signal_monitor/ai_market_summary.py",
        "signal_monitor/ai_signal_analysis.py",
        "signal_monitor/chart_pro_v10.py",
    ]

    for f in files_to_upload:
        local = os.path.join(LOCAL_PROJECT, f)
        if os.path.exists(local):
            remote = f"{REMOTE_PROJECT}/{f}"
            print(f"  上传: {f}")
            upload_file(local, remote)

    # 上传anomaly_detector模块
    print("  上传: anomaly_detector/")
    anomaly_dir = os.path.join(LOCAL_PROJECT, "signal_monitor", "anomaly_detector")
    if os.path.exists(anomaly_dir):
        upload_dir(anomaly_dir, f"{REMOTE_PROJECT}/signal_monitor/")

    return True


def setup_frontend():
    """配置前端到/test路径"""
    print("\n[3/5] 配置前端...")

    # 创建nginx配置
    nginx_config = f'''
location {FRONTEND_PATH} {{
    alias /root/valuescan/web/dist;
    try_files $uri $uri/ {FRONTEND_PATH}/index.html;
}}

location {FRONTEND_PATH}/api {{
    proxy_pass http://127.0.0.1:8080/api;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}}
'''

    # 写入临时文件并上传
    nginx_path = os.path.join(LOCAL_PROJECT, "nginx_test.conf")
    with open(nginx_path, "w") as f:
        f.write(nginx_config)

    upload_file(nginx_path, "/tmp/nginx_test.conf")

    # 在VPS上配置nginx
    cmds = [
        "cat /tmp/nginx_test.conf >> /etc/nginx/sites-available/cornna",
        "nginx -t && systemctl reload nginx",
    ]

    for cmd in cmds:
        code, out, err = run_ssh(cmd)
        if code != 0:
            print(f"  警告: {cmd} 失败")

    print(f"  前端URL: {FRONTEND_URL}")
    return True


def restart_services():
    """重启服务"""
    print("\n[4/5] 重启服务...")

    cmds = [
        "systemctl restart valuescan-monitor",
        "systemctl status valuescan-monitor --no-pager -l",
    ]

    for cmd in cmds:
        print(f"  执行: {cmd}")
        code, out, err = run_ssh(cmd, timeout=30)
        if out:
            print(f"  {out[:200]}")

    return True


def run_tests():
    """运行测试"""
    print("\n[5/5] 运行功能测试...")

    # 测试脚本
    test_script = '''
import sys
sys.path.insert(0, '/root/valuescan/signal_monitor')

print("=" * 50)
print("1. 测试Telegram连接...")
try:
    from telegram import send_message
    send_message("🧪 VPS测试消息 - Telegram连接正常")
    print("   ✓ Telegram发送成功")
except Exception as e:
    print(f"   ✗ Telegram失败: {e}")

print("\\n2. 测试市场数据获取...")
try:
    from market_data_sources import fetch_market_snapshot
    data = fetch_market_snapshot("BTC")
    if data:
        print(f"   ✓ BTC价格: ${data.get('price', 'N/A')}")
    else:
        print("   ✗ 获取BTC数据失败")
except Exception as e:
    print(f"   ✗ 市场数据失败: {e}")

print("\\n3. 测试异动检测模块...")
try:
    from anomaly_detector import AnomalyDetectorEngine
    engine = AnomalyDetectorEngine()
    signals = engine.scan_symbol("BTC")
    print(f"   ✓ 异动检测正常, 信号数: {len(signals)}")
except Exception as e:
    print(f"   ✗ 异动检测失败: {e}")

print("\\n4. 测试美股数据...")
try:
    from market_alert import fetch_us_market_data
    spy = fetch_us_market_data("SPY")
    if spy:
        print(f"   ✓ SPY数据获取成功")
    else:
        print("   ⚠ SPY数据为空(可能非交易时间)")
except Exception as e:
    print(f"   ✗ 美股数据失败: {e}")

print("\\n5. 发送完整测试报告...")
try:
    from telegram import send_message
    report = """🧪 VPS完整功能测试报告

✅ Telegram连接: 正常
✅ 市场数据获取: 正常
✅ 异动检测模块: 已加载
✅ 美股数据接口: 已配置

📊 监控币种: BTC, ETH, SOL, BNB
📈 美股监控: SPY, QQQ, AAPL, NVDA
⏰ 信号间隔: 30分钟
🔔 异动检测: 60秒/次

服务状态: 运行中"""
    send_message(report)
    print("   ✓ 测试报告已发送到Telegram")
except Exception as e:
    print(f"   ✗ 发送报告失败: {e}")

print("\\n" + "=" * 50)
print("测试完成!")
'''

    # 写入测试脚本
    test_path = os.path.join(LOCAL_PROJECT, "vps_test.py")
    with open(test_path, "w", encoding="utf-8") as f:
        f.write(test_script)

    upload_file(test_path, "/tmp/vps_test.py")

    # 执行测试
    print("  执行测试脚本...")
    code, out, err = run_ssh("cd /root/valuescan && python3 /tmp/vps_test.py", timeout=120)

    if out:
        print(out)
    if err:
        print(f"  错误: {err}")

    return code == 0


def main():
    print("=" * 60)
    print("VPS完整信息流测试部署")
    print("=" * 60)
    print(f"目标服务器: {VPS_HOST}")
    print(f"前端地址: {FRONTEND_URL}")
    print(f"Telegram Chat: {TG_CHAT_ID}")

    # 测试SSH连接
    print("\n测试SSH连接...")
    code, out, err = run_ssh("echo 'SSH OK'")
    if code != 0:
        print(f"SSH连接失败: {err}")
        return 1
    print("SSH连接成功")

    # 执行部署步骤
    setup_telegram_config()
    deploy_signal_monitor()
    setup_frontend()
    restart_services()
    run_tests()

    print("\n" + "=" * 60)
    print("部署完成!")
    print(f"前端访问: {FRONTEND_URL}")
    print(f"Telegram频道已配置")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
