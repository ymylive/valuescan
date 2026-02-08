"""
币安跟单 API 客户端
获取带单交易员数据用于评测分析
"""

import requests
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

try:
    from .trader_metrics import analyze_trade_history, analyze_transfers
except ImportError:
    from trader_metrics import analyze_trade_history, analyze_transfers

BASE_URL = "https://www.binance.com/bapi/futures"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Content-Type": "application/json",
    "Origin": "https://www.binance.com",
    "Referer": "https://www.binance.com/zh-CN/copy-trading",
    "clienttype": "web",
}


@dataclass
class TraderData:
    """交易员完整数据"""
    portfolio_id: str
    nickname: str = ""
    follower_count: int = 0
    aum: float = 0.0
    roi_7d: float = 0.0
    roi_30d: float = 0.0
    roi_90d: float = 0.0
    total_roi: float = 0.0
    win_rate: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    trade_count: int = 0
    avg_holding_hours: float = 0.0
    avg_leverage: float = 0.0
    preferred_pairs: List[str] = field(default_factory=list)
    long_ratio: float = 0.5
    trade_history: List[Dict] = field(default_factory=list)  # 仓位历史
    order_history: List[Dict] = field(default_factory=list)  # 操作记录
    roi_curve: List[Dict] = field(default_factory=list)
    current_positions: List[Dict] = field(default_factory=list)
    margin_additions: List[Dict] = field(default_factory=list)
    transfer_history: List[Dict] = field(default_factory=list)
    coin_distribution: List[Dict] = field(default_factory=list)
    raw_data: Dict = field(default_factory=dict)


class BinanceCopyTradeAPI:
    """币安跟单 API 客户端"""

    def __init__(self, timeout: int = 30, max_retries: int = 1, retry_backoff: float = 0.6):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self._cache: Dict[str, tuple] = {}
        self._cache_ttl = 300  # 5分钟缓存

    def _request(self, method: str, endpoint: str, params: Dict = None, payload: Dict = None) -> Optional[Dict]:
        """发送 HTTP 请求"""
        url = f"{BASE_URL}{endpoint}"
        for attempt in range(self.max_retries + 1):
            try:
                json_payload = None if method.upper() == "GET" else (payload or {})
                resp = self.session.request(
                    method,
                    url,
                    params=params,
                    json=json_payload,
                    timeout=self.timeout,
                )
                if resp.status_code != 200:
                    return None
                data = resp.json()
                if data.get("success") or data.get("code") == "000000":
                    return data.get("data", data)
                return None
            except Exception as e:
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff + attempt * self.retry_backoff)
                    continue
                print(f"[CopyTradeAPI] Request error: {e}")
                return None

    def _get(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """发送 GET 请求"""
        return self._request("GET", endpoint, params=params)

    def _post(self, endpoint: str, payload: Dict = None) -> Optional[Dict]:
        """发送 POST 请求"""
        return self._request("POST", endpoint, payload=payload)

    def _paginate(
        self,
        endpoint: str,
        payload: Dict,
        *,
        page_size: int,
        max_pages: Optional[int] = None,
    ) -> List[Dict]:
        all_items: List[Dict] = []
        page = 1
        while True:
            page_payload = dict(payload)
            page_payload["pageNumber"] = page
            page_payload["pageSize"] = page_size
            data = self._post(endpoint, page_payload)
            if not data:
                break

            items = data.get("list", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            if not items:
                break

            all_items.extend(items)
            total = data.get("total", 0) if isinstance(data, dict) else 0
            if total and len(all_items) >= total:
                break
            if len(items) < page_size:
                break
            page += 1
            if max_pages and page > max_pages:
                break

        return all_items

    def get_trader_info(self, portfolio_id: str) -> Optional[Dict]:
        """获取交易员基本信息"""
        return self._get("/v1/friendly/future/copy-trade/lead-portfolio/detail", {"portfolioId": portfolio_id})

    def get_performance(self, portfolio_id: str, time_range: str = "7D") -> Optional[Dict]:
        """获取历史表现 (7D/30D/90D/ALL)"""
        return self._get("/v1/public/future/copy-trade/lead-portfolio/performance", {
            "portfolioId": portfolio_id,
            "timeRange": time_range.upper()
        })

    def get_trade_history(self, portfolio_id: str, page: int = 1, size: int = 100) -> Optional[List]:
        """获取交易历史 (POST)"""
        data = self._post("/v1/friendly/future/copy-trade/lead-portfolio/position-history", {
            "pageNumber": page,
            "pageSize": size,
            "portfolioId": portfolio_id
        })
        return data.get("list", []) if data and isinstance(data, dict) else (data if isinstance(data, list) else [])

    def get_all_trade_history(self, portfolio_id: str) -> List[Dict]:
        """获取全部交易历史（自动分页）"""
        return self._paginate(
            "/v1/friendly/future/copy-trade/lead-portfolio/position-history",
            {"portfolioId": portfolio_id},
            page_size=200,
        )

    def get_all_transfer_history(self, portfolio_id: str) -> List[Dict]:
        """获取全部转账记录（自动分页）"""
        return self._paginate(
            "/v1/friendly/future/copy-trade/lead-portfolio/transfer-history",
            {"portfolioId": portfolio_id},
            page_size=100,
        )

    def get_current_positions(self, portfolio_id: str) -> Optional[List]:
        """获取当前持仓"""
        data = self._get("/v1/friendly/future/copy-trade/lead-data/positions", {"portfolioId": portfolio_id})
        return data if isinstance(data, list) else (data.get("list", []) if data else [])

    def get_roi_curve(self, portfolio_id: str, time_range: str = "90D") -> Optional[List]:
        """获取 ROI 曲线数据"""
        data = self._get("/v1/public/future/copy-trade/lead-portfolio/chart-data", {
            "portfolioId": portfolio_id,
            "timeRange": time_range.upper(),
            "dataType": "ROI"
        })
        return data if isinstance(data, list) else []

    def get_pnl_history(self, portfolio_id: str, days: int = 90) -> Optional[List]:
        """获取盈亏历史（用于检测保证金变动）"""
        end_time = int(time.time() * 1000)
        start_time = end_time - (days * 24 * 60 * 60 * 1000)
        data = self._get("/v1/public/future/copy-trade/lead-portfolio/pnl-history", {
            "portfolioId": portfolio_id,
            "startTime": start_time,
            "endTime": end_time
        })
        return data if isinstance(data, list) else []

    def get_coin_distribution(self, portfolio_id: str, time_range: str = "90D") -> Optional[List]:
        """获取币种交易分布"""
        data = self._get("/v1/public/future/copy-trade/lead-portfolio/performance/coin", {
            "portfolioId": portfolio_id,
            "timeRange": time_range.upper()
        })
        if data:
            # API 返回 {data: [...]} 结构
            if isinstance(data, dict) and "data" in data:
                return data.get("data", [])
            elif isinstance(data, list):
                return data
        return []

    def get_transfer_history(self, portfolio_id: str, page: int = 1, size: int = 50) -> Optional[List]:
        """获取转账记录（充值/提现/保证金）"""
        data = self._post("/v1/friendly/future/copy-trade/lead-portfolio/transfer-history", {
            "pageNumber": page,
            "pageSize": size,
            "portfolioId": portfolio_id
        })
        return data.get("list", []) if data and isinstance(data, dict) else (data if isinstance(data, list) else [])

    def get_order_history(self, portfolio_id: str, start_time: int = None, end_time: int = None, page_size: int = 200) -> Optional[List]:
        """获取操作记录（开仓/平仓订单）"""
        if not end_time:
            end_time = int(time.time() * 1000)
        if not start_time:
            start_time = end_time - (365 * 24 * 60 * 60 * 1000)  # 默认1年
        data = self._post("/v1/friendly/future/copy-trade/lead-portfolio/order-history", {
            "portfolioId": portfolio_id,
            "startTime": start_time,
            "endTime": end_time,
            "pageSize": page_size
        })
        return data.get("list", []) if data and isinstance(data, dict) else (data if isinstance(data, list) else [])

    def get_all_order_history(self, portfolio_id: str, max_pages: int = 50) -> List[Dict]:
        """获取全部操作记录（使用分页）"""
        now = int(time.time() * 1000)
        start_time = now - (30 * 24 * 60 * 60 * 1000)  # 最近30天
        return self._paginate(
            "/v1/friendly/future/copy-trade/lead-portfolio/order-history",
            {
                "portfolioId": portfolio_id,
                "startTime": start_time,
                "endTime": now,
            },
            page_size=200,
            max_pages=max_pages,
        )

    def fetch_full_trader_data(self, portfolio_id: str) -> Optional[TraderData]:
        """获取交易员完整数据"""
        # 检查缓存
        cache_key = f"trader_{portfolio_id}"
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                return cached_data

        # 获取基本信息
        info = self.get_trader_info(portfolio_id)
        if not info:
            return None

        trader = TraderData(portfolio_id=portfolio_id)
        trader.raw_data["info"] = info

        # 解析基本信息 - 修复字段名不一致问题
        trader.nickname = info.get("nickName", info.get("nickname", "Unknown"))
        trader.follower_count = int(info.get("currentCopyCount", info.get("followerCount", 0)))
        trader.aum = float(info.get("aumAmount", info.get("aum", 0)))
        trader.total_roi = float(info.get("roi", 0))
        trader.sharpe_ratio = float(info.get("sharpRatio", info.get("sharpeRatio", 0)))

        # 从tag中估算杠杆范围
        tags = info.get("tag", [])
        estimated_leverage = 0.0
        if "LOW_LEVERAGE" in tags:
            estimated_leverage = 5.0  # <10x
        elif "MEDIUM_LEVERAGE" in tags:
            estimated_leverage = 15.0  # 10x-20x
        elif "HIGH_LEVERAGE" in tags:
            estimated_leverage = 30.0  # >20x

        # 获取各时间段 performance 数据
        for period in ["7D", "30D", "90D"]:
            perf = self.get_performance(portfolio_id, period)
            if perf:
                trader.raw_data[f"performance_{period.lower()}"] = perf
                roi_key = f"roi_{period.lower()}"
                setattr(trader, roi_key, float(perf.get("roi", 0)))

                # 从90D数据获取胜率和回撤
                if period == "90D":
                    # 尝试多种字段名 - winRate返回的是百分比值(如98.6471)
                    win_rate = perf.get("winRate") or perf.get("winRatio") or perf.get("win_rate")
                    if win_rate is not None:
                        wr = float(win_rate)
                        # 如果大于1，说明是百分比形式，需要转换为小数
                        trader.win_rate = wr / 100 if wr > 1 else wr

                    mdd = perf.get("mdd") or perf.get("maxDrawdown") or perf.get("max_drawdown")
                    if mdd is not None:
                        trader.max_drawdown = float(mdd)

        # 获取交易历史 (全量)
        trade_history = self.get_all_trade_history(portfolio_id)
        if trade_history:
            trader.trade_history = trade_history
            trader.trade_count = len(trade_history)
            trader.raw_data["trade_history"] = trade_history
            metrics = analyze_trade_history(
                trade_history,
                include_pnl_metrics=True,
                default_win_rate=trader.win_rate,
                default_max_drawdown=trader.max_drawdown,
            )
            trader.avg_holding_hours = metrics.avg_holding_hours
            # 如果交易历史中没有杠杆数据，使用从tag估算的值
            trader.avg_leverage = metrics.avg_leverage if metrics.avg_leverage > 0 else estimated_leverage
            trader.preferred_pairs = metrics.preferred_pairs
            trader.long_ratio = metrics.long_ratio
            trader.trade_count = metrics.trade_count or trader.trade_count
            trader.win_rate = metrics.win_rate
            trader.max_drawdown = metrics.max_drawdown
        else:
            # 没有交易历史时也使用估算的杠杆
            trader.avg_leverage = estimated_leverage

        # 获取当前持仓
        positions = self.get_current_positions(portfolio_id)
        if positions:
            trader.current_positions = positions
            trader.raw_data["positions"] = positions

        # 获取 ROI 曲线
        roi_curve = self.get_roi_curve(portfolio_id)
        if roi_curve:
            trader.roi_curve = roi_curve
            trader.raw_data["roi_curve"] = roi_curve

        # 获取币种分布
        coin_dist = self.get_coin_distribution(portfolio_id)
        if coin_dist:
            trader.coin_distribution = coin_dist
            trader.raw_data["coin_distribution"] = coin_dist

        # 获取转账记录（全量）
        transfers = self.get_all_transfer_history(portfolio_id)
        if transfers:
            trader.transfer_history = transfers
            trader.raw_data["transfer_history"] = transfers
            trader.margin_additions = analyze_transfers(transfers, include_details=True)

        # 获取操作记录（全量）
        order_history = self.get_all_order_history(portfolio_id)
        if order_history:
            trader.order_history = order_history
            trader.raw_data["order_history"] = order_history

        # 缓存结果
        self._cache[cache_key] = (trader, time.time())

        return trader

# 单例实例
_api_instance: Optional[BinanceCopyTradeAPI] = None

def get_api() -> BinanceCopyTradeAPI:
    """获取 API 单例"""
    global _api_instance
    if _api_instance is None:
        _api_instance = BinanceCopyTradeAPI()
    return _api_instance


def fetch_trader_data(portfolio_id: str) -> Optional[TraderData]:
    """便捷函数：获取交易员数据"""
    return get_api().fetch_full_trader_data(portfolio_id)
