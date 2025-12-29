"""
Telegram 客户端监控
使用 Telethon 库监控群组消息
"""

import asyncio
import logging
from typing import Callable, Optional, List
from datetime import datetime

try:
    from telethon import TelegramClient, events
    from telethon.tl.types import Message
except ImportError:
    print("请安装 telethon: pip install telethon")
    raise

from .signal_parser import SignalParser, TradeSignal


class TelegramMonitor:
    """Telegram 群组监控器"""
    
    def __init__(
        self,
        api_id: int,
        api_hash: str,
        session_name: str = "copytrade_session",
        proxy: Optional[dict] = None
    ):
        """
        初始化监控器
        
        Args:
            api_id: Telegram API ID
            api_hash: Telegram API Hash
            session_name: 会话文件名
            proxy: 代理配置 {"proxy_type": "socks5", "addr": "127.0.0.1", "port": 1080}
        """
        self.logger = logging.getLogger(__name__)
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.proxy = proxy
        
        self.client: Optional[TelegramClient] = None
        self.parser = SignalParser()
        self.signal_callback: Optional[Callable[[TradeSignal], None]] = None
        
        self.monitor_group_ids: List[int] = []
        self.signal_user_ids: List[int] = []
        self.running = False
        
        # 统计
        self.messages_received = 0
        self.signals_parsed = 0
        self.last_signal_time: Optional[datetime] = None
    
    def set_signal_callback(self, callback: Callable[[TradeSignal], None]):
        """设置信号回调函数"""
        self.signal_callback = callback
    
    def set_monitor_group_ids(self, group_ids: List[int]):
        """设置要监控的群组ID"""
        self.monitor_group_ids = group_ids
    
    def set_signal_user_ids(self, user_ids: List[int]):
        """设置信号来源用户ID过滤"""
        self.signal_user_ids = user_ids
    
    async def start(self):
        """启动监控"""
        self.logger.info("🚀 启动 Telegram 监控...")
        
        # 创建客户端
        if self.proxy:
            self.client = TelegramClient(
                self.session_name,
                self.api_id,
                self.api_hash,
                proxy=self.proxy
            )
        else:
            self.client = TelegramClient(
                self.session_name,
                self.api_id,
                self.api_hash
            )
        
        await self.client.start()
        
        # 验证登录
        me = await self.client.get_me()
        self.logger.info(f"✅ 已登录: {me.first_name} (@{me.username})")
        
        # 注册消息处理器
        @self.client.on(events.NewMessage(chats=self.monitor_group_ids if self.monitor_group_ids else None))
        async def message_handler(event: events.NewMessage.Event):
            await self._handle_message(event.message)
        
        self.running = True
        self.logger.info(f"📡 开始监控群组ID: {self.monitor_group_ids}")
        
        # 保持运行
        await self.client.run_until_disconnected()
    
    async def _handle_message(self, message: Message):
        """处理收到的消息"""
        self.messages_received += 1
        
        # 获取消息文本
        text = message.text or message.message
        if not text:
            return
        
        # 用户ID过滤
        if self.signal_user_ids:
            sender = await message.get_sender()
            if sender and sender.id not in self.signal_user_ids:
                return
        
        # 解析信号
        signal = self.parser.parse(text)
        if signal:
            self.signals_parsed += 1
            self.last_signal_time = datetime.now()
            
            self.logger.info(
                f"📊 收到{signal.signal_type}信号: "
                f"{signal.symbol} {signal.direction} {signal.leverage}x"
            )
            
            # 调用回调
            if self.signal_callback:
                try:
                    self.signal_callback(signal)
                except Exception as e:
                    self.logger.error(f"信号回调执行失败: {e}")
    
    async def stop(self):
        """停止监控"""
        self.running = False
        if self.client:
            await self.client.disconnect()
            self.logger.info("🛑 Telegram 监控已停止")
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "messages_received": self.messages_received,
            "signals_parsed": self.signals_parsed,
            "last_signal_time": self.last_signal_time.isoformat() if self.last_signal_time else None,
            "running": self.running,
            "monitor_group_ids": self.monitor_group_ids
        }


async def test_monitor():
    """测试监控器（需要配置）"""
    import os
    
    # 从环境变量或配置文件读取
    api_id = int(os.environ.get("TELEGRAM_API_ID", "0"))
    api_hash = os.environ.get("TELEGRAM_API_HASH", "")
    
    if not api_id or not api_hash:
        print("请设置 TELEGRAM_API_ID 和 TELEGRAM_API_HASH 环境变量")
        return
    
    monitor = TelegramMonitor(api_id, api_hash)
    monitor.set_monitor_groups(["xhub888"])
    
    def on_signal(signal: TradeSignal):
        print(f"收到信号: {signal}")
    
    monitor.set_signal_callback(on_signal)
    
    await monitor.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_monitor())
