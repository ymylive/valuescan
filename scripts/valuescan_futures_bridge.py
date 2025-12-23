#!/usr/bin/env python3
"""
ValueScan → Binance Futures IPC Bridge

开启本地 TCP 服务，接收 ValueScan 信号（JSON 按行发送），并交由
FuturesAutoTradingSystem 处理，实现 signal_monitor 与交易模块的进程解耦。
"""

import argparse
import json
import logging
import os
import socketserver
import sys
import threading
import time
from typing import Any, Dict, Optional

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from binance_trader.futures_main import FuturesAutoTradingSystem
from ipc_config import IPC_HOST, IPC_PORT

LOGGER = logging.getLogger("valuescan.ipc_bridge")


def _normalize_symbol(symbol: Optional[str]) -> Optional[str]:
    if not symbol:
        return None

    cleaned = symbol.strip().upper()

    if cleaned.startswith("$"):
        cleaned = cleaned[1:]

    if "/" in cleaned:
        cleaned = cleaned.split("/", 1)[0]

    if cleaned.endswith("USDT") and len(cleaned) > 4:
        cleaned = cleaned[:-4]

    return cleaned or None


def _extract_symbol(payload: Dict[str, Any]) -> Optional[str]:
    symbol = payload.get("symbol_hint")

    if not symbol:
        data_content = (
            payload.get("data", {}).get("content") if isinstance(payload.get("data"), dict) else {}
        )
        if isinstance(data_content, dict):
            symbol = (
                data_content.get("symbol")
                or data_content.get("pair")
                or data_content.get("symbolName")
            )

    if not symbol:
        raw = payload.get("data", {}).get("raw_message")
        if isinstance(raw, dict):
            symbol = raw.get("symbol")
            if not symbol:
                title = raw.get("title")
                if isinstance(title, str):
                    symbol = title.split(" ")[0]

    return _normalize_symbol(symbol)


class SignalRequestHandler(socketserver.StreamRequestHandler):
    """
    逐行读取客户端发送的 JSON，解析后调用交易系统处理信号
    """

    def handle(self):
        client = f"{self.client_address[0]}:{self.client_address[1]}"
        LOGGER.debug("📥 IPC 客户端已连接: %s", client)  # 改为 DEBUG 级别

        for raw_line in self.rfile:
            line = raw_line.decode("utf-8", errors="ignore").strip()
            if not line:
                continue

            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                LOGGER.warning("无法解析客户端消息（JSON 错误）: %s | 错误: %s", line[:200], exc)
                continue

            self._process_payload(payload)

        LOGGER.debug("📤 IPC 客户端断开: %s", client)  # 改为 DEBUG 级别

    def _process_payload(self, payload: Dict[str, Any]):
        message_type = payload.get("message_type")
        message_id = payload.get("message_id")

        if message_type not in {110, 112, 113}:
            LOGGER.debug("忽略非交易信号类型: %s", message_type)
            return

        if not message_id:
            LOGGER.warning("IPC 载荷缺少 message_id: %s", payload)
            return

        symbol = _extract_symbol(payload)
        if not symbol:
            LOGGER.warning(
                "无法解析标的符号，跳过信号: id=%s payload=%s",
                message_id,
                json.dumps(payload, ensure_ascii=False)[:200],
            )
            return

        data = payload.get("data") or {}

        LOGGER.info(
            "➡️  收到信号: type=%s id=%s symbol=%s",
            message_type,
            message_id,
            symbol,
        )

        self.server.system.process_signal(  # type: ignore[attr-defined]
            message_type=int(message_type),
            message_id=str(message_id),
            symbol=symbol,
            data=data,
        )


class SignalTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, server_address, handler_class, system):
        super().__init__(server_address, handler_class)
        self.system = system
        self.logger = LOGGER


def start_maintenance_loop(system: FuturesAutoTradingSystem, stop_event: threading.Event):
    """
    维护风控、移动止损等定时任务，保持与原有独立模式一致
    """
    consecutive_errors = 0
    max_consecutive_errors = 10

    while not stop_event.is_set():
        try:
            system.monitor_positions()
            system.check_trailing_stops()
            system.check_pyramiding_exits()
            system.update_balance()

            # 操作成功，重置错误计数
            consecutive_errors = 0
            time.sleep(1)

        except KeyboardInterrupt:
            LOGGER.info("维护循环收到中断信号")
            stop_event.set()
            break

        except Exception as e:
            consecutive_errors += 1
            LOGGER.warning(
                f"维护循环发生异常 (第 {consecutive_errors} 次): {e}"
            )

            # 如果连续错误太多，退出循环
            if consecutive_errors >= max_consecutive_errors:
                LOGGER.error(
                    f"维护循环连续失败 {max_consecutive_errors} 次，停止运行"
                )
                stop_event.set()
                break

            # 等待后重试，避免错误风暴
            time.sleep(5)


def main():
    parser = argparse.ArgumentParser(description="启动 ValueScan → Binance Futures IPC 桥接服务")
    parser.add_argument("--host", default=IPC_HOST, help="监听地址 (默认: %(default)s)")
    parser.add_argument("--port", type=int, default=IPC_PORT, help="监听端口 (默认: %(default)s)")
    args = parser.parse_args()

    system = FuturesAutoTradingSystem()

    stop_event = threading.Event()
    maintenance_thread = threading.Thread(
        target=start_maintenance_loop,
        args=(system, stop_event),
        daemon=True,
    )
    maintenance_thread.start()

    server = SignalTCPServer((args.host, args.port), SignalRequestHandler, system)

    LOGGER.info("IPC 服务启动: %s:%s", args.host, args.port)
    LOGGER.info("等待 ValueScan 信号 (TCP JSON Lines)... 按 Ctrl+C 退出")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("收到中断信号，正在关闭 IPC 服务...")
    finally:
        stop_event.set()
        server.shutdown()
        server.server_close()
        maintenance_thread.join(timeout=5)
        LOGGER.info("IPC 桥接服务已退出")


if __name__ == "__main__":
    main()
