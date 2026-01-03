#!/usr/bin/env python3
"""IPC 服务器 - 接收信号监控转发的信号"""
import socket
import json
import threading
import logging
import sys

sys.path.insert(0, '/opt/valuescan/binance_trader')

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

IPC_HOST = '127.0.0.1'
IPC_PORT = 8765

class IPCServer:
    def __init__(self, trading_system):
        self.trading_system = trading_system
        self.server_socket = None
        self.running = False
    
    def start(self):
        """启动 IPC 服务器"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((IPC_HOST, IPC_PORT))
        self.server_socket.listen(5)
        self.running = True
        
        logger.info(f"🔌 IPC 服务器启动: {IPC_HOST}:{IPC_PORT}")
        
        while self.running:
            try:
                self.server_socket.settimeout(1.0)
                try:
                    client, addr = self.server_socket.accept()
                    threading.Thread(target=self.handle_client, args=(client,), daemon=True).start()
                except socket.timeout:
                    continue
            except Exception as e:
                if self.running:
                    logger.error(f"IPC 服务器错误: {e}")
    
    def handle_client(self, client):
        """处理客户端连接"""
        try:
            data = client.recv(65536)
            if data:
                signal = json.loads(data.decode('utf-8'))
                logger.info(f"📨 收到 IPC 信号: {signal.get('symbol')} type={signal.get('type')}")
                
                # 转发到交易系统
                if self.trading_system:
                    self.trading_system.process_signal(
                        signal_type=signal.get('type'),
                        signal_id=signal.get('id'),
                        symbol=signal.get('symbol'),
                        data=signal.get('data', {})
                    )
                
                client.send(b'OK')
        except Exception as e:
            logger.error(f"处理 IPC 信号失败: {e}")
        finally:
            client.close()
    
    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()


def run_with_ipc():
    """启动交易系统并监听 IPC"""
    from futures_main import FuturesAutoTradingSystem
    
    system = FuturesAutoTradingSystem()
    
    # 启动 IPC 服务器线程
    ipc_server = IPCServer(system)
    ipc_thread = threading.Thread(target=ipc_server.start, daemon=True)
    ipc_thread.start()
    
    # 运行交易系统
    system.run_standalone()


if __name__ == '__main__':
    run_with_ipc()
