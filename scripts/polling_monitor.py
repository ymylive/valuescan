#!/usr/bin/env python3
"""主动轮询 API 获取信号 - 替代浏览器监听"""
import json
import time
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# 配置
POLL_INTERVAL = 10  # 轮询间隔(秒)
PROXIES = {'http': 'socks5://127.0.0.1:1080', 'https': 'socks5://127.0.0.1:1080'}

# 读取 token
with open('/opt/valuescan/signal_monitor/valuescan_localstorage.json', 'r') as f:
    ls_data = json.load(f)
TOKEN = ls_data.get('account_token', '')

# 导入消息处理和 Telegram
try:
    import sys
    sys.path.insert(0, '/opt/valuescan/signal_monitor')
    from message_handler import process_response_data
    from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, SOCKS5_PROXY, ENABLE_IPC_FORWARDING
    from ipc_client import forward_signal
    logger.info("✅ 导入模块成功")
except Exception as e:
    logger.error(f"导入模块失败: {e}")
    forward_signal = None

def fetch_signals():
    """获取信号"""
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
    logger.info("🚀 启动主动轮询监控...")
    logger.info(f"轮询间隔: {POLL_INTERVAL} 秒")
    
    seen_ids = set()
    
    while True:
        try:
            data = fetch_signals()
            if data and data.get('code') == 200:
                messages = data.get('data', [])
                new_count = 0
                for msg in messages:
                    msg_id = msg.get('id')
                    if msg_id and msg_id not in seen_ids:
                        seen_ids.add(msg_id)
                        new_count += 1
                        logger.info(f"📨 新信号: {msg.get('title')} - {msg.get('type')}")
                        
                        # 处理信号
                        process_response_data(
                            data,
                            send_to_telegram=True,
                            seen_ids=seen_ids,
                            signal_callback=forward_signal if ENABLE_IPC_FORWARDING else None
                        )
                        break  # 一次只处理一批
                
                if new_count == 0:
                    logger.debug("无新信号")
            
            time.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("停止监控")
            break
        except Exception as e:
            logger.error(f"错误: {e}")
            time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    main()
