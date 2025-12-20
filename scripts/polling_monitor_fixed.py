#!/usr/bin/env python3
"""主动轮询 API 获取信号"""
import json
import time
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

POLL_INTERVAL = 10
PROXIES = {'http': 'socks5://127.0.0.1:1080', 'https': 'socks5://127.0.0.1:1080'}

with open('/opt/valuescan/signal_monitor/valuescan_localstorage.json', 'r') as f:
    ls_data = json.load(f)
TOKEN = ls_data.get('account_token', '')

try:
    import sys
    sys.path.insert(0, '/opt/valuescan/signal_monitor')
    from message_handler import process_response_data
    from config import ENABLE_IPC_FORWARDING
    from ipc_client import forward_signal
    logger.info("导入模块成功")
except Exception as e:
    logger.error(f"导入模块失败: {e}")
    forward_signal = None
    ENABLE_IPC_FORWARDING = False

def fetch_signals():
    headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}
    url = 'https://api.valuescan.io/api/account/message/getWarnMessage'
    try:
        resp = requests.get(url, headers=headers, proxies=PROXIES, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        else:
            logger.warning(f"API 返回状态码: {resp.status_code}")
            return None
    except Exception as e:
        logger.error(f"请求失败: {e}")
        return None

def main():
    logger.info("启动主动轮询监控...")
    logger.info(f"轮询间隔: {POLL_INTERVAL} 秒")
    
    # 不使用内存 seen_ids，完全依赖数据库去重
    while True:
        try:
            data = fetch_signals()
            if data and data.get('code') == 200:
                messages = data.get('data', [])
                if messages:
                    logger.info(f"API 返回 {len(messages)} 条消息")
                    # 直接调用 process_response_data，让它内部处理去重
                    new_count = process_response_data(
                        data,
                        send_to_telegram=True,
                        seen_ids=None,  # 不传 seen_ids，完全依赖数据库
                        signal_callback=forward_signal if ENABLE_IPC_FORWARDING else None
                    )
                    if new_count > 0:
                        logger.info(f"处理了 {new_count} 条新消息")
            
            time.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("停止监控")
            break
        except Exception as e:
            logger.error(f"错误: {e}")
            time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    main()
