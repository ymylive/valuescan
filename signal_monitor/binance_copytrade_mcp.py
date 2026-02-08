"""
币安跟单 Chrome MCP 数据获取模块
通过 Chrome DevTools MCP 获取完整的交易员数据
"""

import json
import time
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

# 导入原有的数据结构
try:
    from .binance_copytrade_api import TraderData, BinanceCopyTradeAPI, get_api
    from .trader_metrics import analyze_trade_history, analyze_transfers
except ImportError:
    from binance_copytrade_api import TraderData, BinanceCopyTradeAPI, get_api
    from trader_metrics import analyze_trade_history, analyze_transfers


@dataclass
class MCPConfig:
    """MCP 配置"""
    timeout: int = 30000  # 页面加载超时（毫秒）
    wait_for_data: int = 5000  # 等待数据加载（毫秒）
    max_retries: int = 3  # 最大重试次数


class BinanceCopyTradeMCP:
    """
    通过 Chrome MCP 获取币安跟单数据

    使用方式：
    1. 确保 Chrome MCP 服务已启动
    2. 调用 fetch_trader_data_via_mcp() 获取数据
    3. 如果 MCP 不可用，自动回退到 HTTP API
    """

    def __init__(self, config: MCPConfig = None):
        self.config = config or MCPConfig()
        self._api_fallback = get_api()  # HTTP API 作为备用
        self._captured_data: Dict[str, Any] = {}

    def fetch_trader_data_via_mcp(self, portfolio_id: str, mcp_tools: Dict = None) -> Optional[TraderData]:
        """
        通过 MCP 获取交易员数据

        Args:
            portfolio_id: 交易员 ID
            mcp_tools: MCP 工具字典（由调用方提供）

        Returns:
            TraderData 或 None
        """
        if not mcp_tools:
            # 没有 MCP 工具，回退到 HTTP API
            print("[CopyTradeMCP] No MCP tools available, falling back to HTTP API")
            return self._api_fallback.fetch_full_trader_data(portfolio_id)

        try:
            # 1. 打开交易员页面
            trader_url = f"https://www.binance.com/zh-CN/copy-trading/lead-details/{portfolio_id}"

            # 使用 MCP 打开新页面
            if 'new_page' in mcp_tools:
                mcp_tools['new_page'](url=trader_url, timeout=self.config.timeout)

            # 2. 等待页面加载
            if 'wait_for' in mcp_tools:
                mcp_tools['wait_for'](text="跟随者", timeout=self.config.timeout)

            # 3. 获取网络请求
            if 'list_network_requests' in mcp_tools:
                requests = mcp_tools['list_network_requests'](
                    resourceTypes=["xhr", "fetch"]
                )

                # 4. 解析 API 响应
                trader_data = self._parse_network_requests(requests, portfolio_id, mcp_tools)

                if trader_data:
                    return trader_data

            # MCP 获取失败，回退到 HTTP
            print("[CopyTradeMCP] MCP data incomplete, falling back to HTTP API")
            return self._api_fallback.fetch_full_trader_data(portfolio_id)

        except Exception as e:
            print(f"[CopyTradeMCP] Error: {e}, falling back to HTTP API")
            return self._api_fallback.fetch_full_trader_data(portfolio_id)

    def _parse_network_requests(self, requests: List, portfolio_id: str,
                                 mcp_tools: Dict) -> Optional[TraderData]:
        """解析网络请求，提取交易员数据"""
        trader = TraderData(portfolio_id=portfolio_id)
        data_found = {
            'info': False,
            'performance': False,
            'positions': False,
            'history': False,
        }

        for req in requests:
            url = req.get('url', '')
            reqid = req.get('reqid')

            if not reqid:
                continue

            # 获取请求详情
            if 'get_network_request' in mcp_tools:
                try:
                    detail = mcp_tools['get_network_request'](reqid=reqid)
                    response_body = detail.get('response', {}).get('body', '')

                    if not response_body:
                        continue

                    # 解析 JSON 响应
                    try:
                        data = json.loads(response_body)
                        if not data.get('success') and data.get('code') != '000000':
                            continue

                        api_data = data.get('data', data)

                        # 根据 URL 判断数据类型
                        if 'lead-portfolio/detail' in url:
                            self._parse_trader_info(trader, api_data)
                            data_found['info'] = True

                        elif 'lead-portfolio/performance' in url:
                            self._parse_performance(trader, api_data, url)
                            data_found['performance'] = True

                        elif 'lead-data/positions' in url:
                            trader.current_positions = api_data if isinstance(api_data, list) else []
                            data_found['positions'] = True

                        elif 'position-history' in url:
                            history = api_data.get('list', []) if isinstance(api_data, dict) else api_data
                            trader.trade_history.extend(history)
                            data_found['history'] = True

                        elif 'chart-data' in url:
                            trader.roi_curve = api_data if isinstance(api_data, list) else []

                        elif 'performance/coin' in url:
                            trader.coin_distribution = api_data if isinstance(api_data, list) else []

                        elif 'transfer-history' in url:
                            transfers = api_data.get('list', []) if isinstance(api_data, dict) else api_data
                            trader.transfer_history.extend(transfers)

                        elif 'order-history' in url:
                            orders = api_data.get('list', []) if isinstance(api_data, dict) else api_data
                            trader.order_history.extend(orders)

                    except json.JSONDecodeError:
                        continue

                except Exception as e:
                    print(f"[CopyTradeMCP] Error parsing request {reqid}: {e}")
                    continue

        # 检查是否获取到足够数据
        if data_found['info']:
            # 分析交易历史
            if trader.trade_history:
                self._analyze_trade_history(trader)

            # 分析转账记录
            if trader.transfer_history:
                self._analyze_transfers(trader)

            return trader

        return None

    def _parse_trader_info(self, trader: TraderData, data: Dict):
        """解析交易员基本信息"""
        trader.nickname = data.get('nickName', data.get('nickname', 'Unknown'))
        trader.follower_count = int(data.get('followerCount', 0))
        trader.aum = float(data.get('aum', 0))
        trader.total_roi = float(data.get('roi', 0))
        trader.win_rate = float(data.get('winRate', 0))
        trader.max_drawdown = float(data.get('mdd', data.get('maxDrawdown', 0)))
        trader.sharpe_ratio = float(data.get('sharpeRatio', 0))
        trader.raw_data['info'] = data

    def _parse_performance(self, trader: TraderData, data: Dict, url: str):
        """解析表现数据"""
        roi = float(data.get('roi', 0))

        # 从 URL 判断时间范围
        if '7D' in url.upper() or '7d' in url:
            trader.roi_7d = roi
        elif '30D' in url.upper() or '30d' in url:
            trader.roi_30d = roi
        elif '90D' in url.upper() or '90d' in url:
            trader.roi_90d = roi

        trader.raw_data[f'performance_{url}'] = data

    def _analyze_trade_history(self, trader: TraderData):
        """分析交易历史"""
        metrics = analyze_trade_history(
            trader.trade_history,
            include_pnl_metrics=False,
            default_win_rate=trader.win_rate,
            default_max_drawdown=trader.max_drawdown,
        )
        trader.avg_holding_hours = metrics.avg_holding_hours
        trader.avg_leverage = metrics.avg_leverage
        trader.preferred_pairs = metrics.preferred_pairs
        trader.long_ratio = metrics.long_ratio
        trader.trade_count = metrics.trade_count or trader.trade_count
        trader.win_rate = metrics.win_rate
        trader.max_drawdown = metrics.max_drawdown

    def _analyze_transfers(self, trader: TraderData):
        """分析转账记录，检测保证金添加行为"""
        trader.margin_additions = analyze_transfers(trader.transfer_history, include_details=False)


def create_mcp_fetcher(config: MCPConfig = None) -> BinanceCopyTradeMCP:
    """创建 MCP 数据获取器"""
    return BinanceCopyTradeMCP(config)


def fetch_trader_data_with_mcp(portfolio_id: str, mcp_tools: Dict = None) -> Optional[TraderData]:
    """
    便捷函数：通过 MCP 获取交易员数据

    如果 MCP 不可用，自动回退到 HTTP API
    """
    fetcher = create_mcp_fetcher()
    return fetcher.fetch_trader_data_via_mcp(portfolio_id, mcp_tools)


# 集成到 telegram_bot 的辅助函数
def get_mcp_tools_from_router():
    """
    从 MCP Router 获取工具

    注意：这个函数需要在有 MCP 环境的上下文中调用
    返回一个工具字典，包含：
    - new_page: 打开新页面
    - wait_for: 等待元素
    - list_network_requests: 列出网络请求
    - get_network_request: 获取请求详情
    - take_snapshot: 获取页面快照
    """
    # 这里返回 None，实际使用时由调用方提供 MCP 工具
    # 在 Claude Code 环境中，这些工具会自动可用
    return None
