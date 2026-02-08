#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ValuScan API 客户端 - 统一数据获取接口
"""
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
import requests

# 基础配置
# ==================== Signals ====================
BASE_DIR = Path(__file__).resolve().parent.parent
TOKEN_FILE = Path(os.getenv("VALUESCAN_TOKEN_FILE") or BASE_DIR / "signal_monitor" / "valuescan_localstorage.json")
API_BASE = os.getenv("VALUESCAN_API_BASE", "https://api.valuescan.io").rstrip("/")
TIMEOUT = float(os.getenv("VALUESCAN_API_TIMEOUT", "15"))
API_BASES_ENV = os.getenv("VALUESCAN_API_BASES", "").strip()
ACCESS_TICKET_FALLBACK = (os.getenv("VALUESCAN_ACCESS_TICKET_FALLBACK") or "LNe1VTyHk0bij3cyWB2gxg==").strip()


def _build_api_bases() -> List[str]:
    bases: List[str] = []
    if API_BASES_ENV:
        for item in API_BASES_ENV.split(","):
            base = item.strip().rstrip("/")
            if base:
                bases.append(base)
    if API_BASE:
        bases.append(API_BASE.rstrip("/"))
    bases.extend([
        "https://cornna.abrdns.com",
        "https://cornna.qzz.io",
        "https://api.valuescan.io",
        "https://www.valuescan.io",
    ])
    seen = set()
    unique: List[str] = []
    for base in bases:
        if base in seen:
            continue
        seen.add(base)
        unique.append(base)
    return unique


API_BASES = _build_api_bases()


class ValuScanClient:
    """ValuScan API 客户端"""
    
    # API 端点定义
    ENDPOINTS = {
        # 信号相关
        "warn_messages": "/api/account/message/getWarnMessage",
        "ai_messages": "/api/account/message/aiMessagePage",
        
        # 资金异动
        "funds_movement": "/api/chance/getFundsMovementPage",
        "funds_update": "/api/chance/getFundsMovementUpdate",
        
        # 涨跌榜
        "coin_rank": "/api/analysis/crypto/coin-rank",
        
        # 代币信息
        "token_detail": "/api/analysis/crypto/token-detail",
        "token_search": "/api/analysis/crypto/search",
        
        # K线数据
        "kline": "/api/analysis/crypto/kline",
        
        # 持仓分析
        "holder_analysis": "/api/analysis/crypto/holder-analysis",
        
        # 交易所数据
        "exchange_flow": "/api/analysis/crypto/exchange-flow",
        
        # 链上数据
        "onchain_activity": "/api/analysis/crypto/onchain-activity",
        
        # 热门代币
        "trending": "/api/analysis/crypto/trending",
        
        # 新币
        "new_listings": "/api/analysis/crypto/new-listings",
    }
    
    def __init__(self, token_file: Optional[Path] = None, proxy: Optional[str] = None):
        self.token_file = token_file or TOKEN_FILE
        self.session = requests.Session()
        self.session.trust_env = False
        self.proxy = proxy or os.getenv("VALUESCAN_PROXY") or os.getenv("SOCKS5_PROXY")
        self._token_cache: Optional[str] = None
        self._token_expiry: Optional[int] = None
        self._access_ticket_cache: Optional[str] = None

    @staticmethod
    def _format_coin_key(symbol: Optional[str], chain: Optional[str]) -> str:
        if not symbol:
            return ""
        base = str(symbol).upper().replace("$", "").replace("USDT", "").strip()
        chain_name = (chain or base).upper().strip()
        if not base:
            return ""
        return f"{base}_{chain_name}"
    
    def _get_proxies(self) -> Optional[Dict[str, str]]:
        if not self.proxy:
            return None
        if self.proxy.startswith("socks"):
            return {"http": self.proxy, "https": self.proxy}
        return {"http": self.proxy, "https": self.proxy}
    
    def _load_token(self) -> Optional[str]:
        """加载 account_token (不做本地过期检查，由服务器决定)"""
        
        try:
            if not self.token_file.exists():
                return None
            data = json.loads(self.token_file.read_text(encoding="utf-8"))
            token = (data.get("account_token") or "").strip()
            if not token and isinstance(data.get("data"), dict):
                token = (data["data"].get("account_token") or "").strip()
            if token:
                self._token_cache = token
            return token
        except Exception:
            return None

    def _load_access_ticket(self) -> Optional[str]:
        env_ticket = (os.getenv("VALUESCAN_ACCESS_TICKET") or "").strip()
        if env_ticket:
            self._access_ticket_cache = env_ticket
            return env_ticket
        if self._access_ticket_cache:
            return self._access_ticket_cache
        try:
            if self.token_file.exists():
                data = json.loads(self.token_file.read_text(encoding="utf-8"))
                for key in ("access_ticket", "accessTicket", "access-ticket", "accessTicketValue"):
                    val = data.get(key)
                    if isinstance(val, str) and val.strip():
                        self._access_ticket_cache = val.strip()
                        return self._access_ticket_cache
                if isinstance(data.get("data"), dict):
                    for key in ("access_ticket", "accessTicket", "access-ticket", "accessTicketValue"):
                        val = data["data"].get(key)
                        if isinstance(val, str) and val.strip():
                            self._access_ticket_cache = val.strip()
                            return self._access_ticket_cache
        except Exception:
            pass
        if ACCESS_TICKET_FALLBACK:
            self._access_ticket_cache = ACCESS_TICKET_FALLBACK
        return self._access_ticket_cache

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        token = self._load_token()
        access_ticket = self._load_access_ticket()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": "https://www.valuescan.io",
            "Referer": "https://www.valuescan.io/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if access_ticket:
            headers["Access-Ticket"] = access_ticket
        return headers

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_body: Optional[Dict] = None,
        _retry: bool = True,
    ) -> Dict[str, Any]:
        """Send request; return token_expired when token is invalid."""
        headers = self._build_headers()
        has_auth = bool(headers.get("Authorization"))
        headers_no_auth = dict(headers)
        headers_no_auth.pop("Authorization", None)
        proxies = self._get_proxies()
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            urls = [endpoint]
        else:
            path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
            urls = [f"{base}{path}" for base in API_BASES]

        last_error: Dict[str, Any] = {"error": "request_failed"}
        def _send_with_headers(url: str, request_headers: Dict[str, str], idx: int) -> Tuple[str, Dict[str, Any]]:
            try:
                resp = self.session.request(
                    method,
                    url,
                    headers=request_headers,
                    params=params,
                    json=json_body,
                    timeout=TIMEOUT,
                    proxies=proxies,
                    verify=True,
                )
            except requests.exceptions.SSLError as exc:
                try:
                    resp = self.session.request(
                        method,
                        url,
                        headers=request_headers,
                        params=params,
                        json=json_body,
                        timeout=TIMEOUT,
                        proxies=proxies,
                        verify=False,
                    )
                except requests.exceptions.RequestException as retry_exc:
                    return ("error", {"error": str(retry_exc)})
            except requests.exceptions.Timeout:
                return ("error", {"error": "timeout"})
            except requests.exceptions.RequestException as e:
                return ("error", {"error": str(e)})

            if resp.status_code in (404, 405) and idx < len(urls) - 1:
                return ("retry_base", {"error": f"http_{resp.status_code}"})
            if resp.status_code >= 500 and idx < len(urls) - 1:
                return ("retry_base", {"error": f"http_{resp.status_code}"})
            if resp.status_code in (401, 403):
                return ("token_expired", {"error": "token_expired", "code": resp.status_code})

            try:
                data = resp.json()
            except ValueError:
                return ("error", {"error": "invalid_json", "code": resp.status_code})

            code = data.get("code") if isinstance(data, dict) else None
            if code in (4000, 4002, 401, 403):
                return ("token_expired", {"error": "token_expired", "code": code})

            return ("ok", data)

        for idx, url in enumerate(urls):
            status, payload = _send_with_headers(url, headers, idx)
            if status == "ok":
                return payload
            if status == "retry_base":
                last_error = payload
                continue
            if status == "token_expired" and _retry and has_auth:
                status_no_auth, payload_no_auth = _send_with_headers(url, headers_no_auth, idx)
                if status_no_auth == "ok":
                    return payload_no_auth
                if status_no_auth == "retry_base":
                    last_error = payload_no_auth
                    continue
                last_error = payload_no_auth
                continue

            last_error = payload

        return last_error

    # ==================== Signals ====================
    
    def get_warn_messages(self) -> Dict[str, Any]:
        """获取预警消息"""
        return self._request("GET", self.ENDPOINTS["warn_messages"])
    
    def get_ai_messages(self, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """获取 AI 信号消息"""
        return self._request("POST", self.ENDPOINTS["ai_messages"], json_body={
            "pageNum": page,
            "pageSize": page_size,
        })
    
    def get_all_signals(self) -> Dict[str, Any]:
        """获取所有信号（合并预警和AI消息）"""
        warn = self.get_warn_messages()
        ai = self.get_ai_messages()
        
        messages = []
        if warn.get("code") == 200:
            messages.extend(warn.get("data") or [])
        if ai.get("code") == 200:
            ai_data = ai.get("data") or {}
            messages.extend(ai_data.get("records") or ai_data.get("list") or [])
        
        return {
            "code": 200,
            "data": messages,
            "sources": {
                "warn": warn.get("code") == 200,
                "ai": ai.get("code") == 200,
            }
        }
    
    # ==================== 资金异动 ====================
    
    def get_funds_movement(
        self,
        page: int = 1,
        page_size: int = 20,
        chain: Optional[str] = None,
        movement_type: Optional[int] = None,
    ) -> Dict[str, Any]:
        """获取资金异动列表"""
        payload = {"pageNum": page, "pageSize": page_size}
        if chain:
            payload["chain"] = chain
        if movement_type is not None:
            payload["type"] = movement_type
        return self._request("POST", self.ENDPOINTS["funds_movement"], json_body=payload)
    
    def get_funds_update(self, last_id: Optional[int] = None) -> Dict[str, Any]:
        """获取资金异动更新"""
        params = {}
        if last_id:
            params["lastId"] = last_id
        return self._request("GET", self.ENDPOINTS["funds_update"], params=params)
    
    # ==================== 涨跌榜 ====================
    
    def get_coin_rank(
        self,
        rank_type: int = 1,  # 1=涨幅榜, 2=跌幅榜
        page: int = 1,
        page_size: int = 20,
        time_range: str = "24h",
    ) -> Dict[str, Any]:
        """获取涨跌榜"""
        order_col = "percentChange24h"
        if time_range == "1h":
            order_col = "percentChange1h"
        elif time_range == "7d":
            order_col = "percentChange7d"
        
        payload = {
            "type": rank_type,
            "page": page,
            "pageSize": page_size,
            "order": [
                {"column": order_col, "asc": rank_type == 2},
                {"column": "marketCap", "asc": False},
            ]
        }
        return self._request("POST", self.ENDPOINTS["coin_rank"], json_body=payload)
    
    def get_gainers(self, page: int = 1, page_size: int = 20, time_range: str = "24h") -> Dict[str, Any]:
        """获取涨幅榜"""
        return self.get_coin_rank(1, page, page_size, time_range)
    
    def get_losers(self, page: int = 1, page_size: int = 20, time_range: str = "24h") -> Dict[str, Any]:
        """获取跌幅榜"""
        return self.get_coin_rank(2, page, page_size, time_range)
    
    # ==================== 代币信息 ====================
    
    def get_token_detail(self, symbol: str, chain: Optional[str] = None) -> Dict[str, Any]:
        """获取代币详情"""
        payload = {"symbol": symbol}
        if chain:
            payload["chain"] = chain
        return self._request("POST", self.ENDPOINTS["token_detail"], json_body=payload)
    
    def search_token(self, keyword: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """搜索代币"""
        return self._request("POST", self.ENDPOINTS["token_search"], json_body={
            "keyword": keyword,
            "page": page,
            "pageSize": page_size,
        })
    
    # ==================== K线数据 ====================
    
    def search_keyword(self, keyword: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Search token keyword mapping (ValueScan track search)."""
        return self._request("POST", "/api/track/coin/search-keyword", json_body={
            "search": keyword,
            "page": page,
            "pageSize": page_size,
        })

    def get_kline(
        self,
        symbol: str,
        interval: str = "1h",  # 1m, 5m, 15m, 1h, 4h, 1d
        limit: int = 100,
    ) -> Dict[str, Any]:
        """获取K线数据"""
        return self._request("POST", self.ENDPOINTS["kline"], json_body={
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        })
    
    # ==================== 链上数据 ====================
    
    def get_holder_analysis(self, symbol: str, chain: Optional[str] = None) -> Dict[str, Any]:
        """获取持仓分析"""
        payload = {"symbol": symbol}
        if chain:
            payload["chain"] = chain
        return self._request("POST", self.ENDPOINTS["holder_analysis"], json_body=payload)
    
    def get_exchange_flow(self, symbol: str, days: int = 7) -> Dict[str, Any]:
        """获取交易所资金流向"""
        return self._request("POST", self.ENDPOINTS["exchange_flow"], json_body={
            "symbol": symbol,
            "days": days,
        })
    
    def get_onchain_activity(self, symbol: str) -> Dict[str, Any]:
        """获取链上活动"""
        return self._request("POST", self.ENDPOINTS["onchain_activity"], json_body={
            "symbol": symbol,
        })
    
    # ==================== 热门和新币 ====================
    
    def get_trending(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取热门代币"""
        return self._request("POST", self.ENDPOINTS["trending"], json_body={
            "page": page,
            "pageSize": page_size,
        })
    
    def get_new_listings(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取新上线代币"""
        return self._request("POST", self.ENDPOINTS["new_listings"], json_body={
            "page": page,
            "pageSize": page_size,
        })
    
    # ==================== 币种详情 ====================
    
    def get_coin_detail(self, keyword: int) -> Dict[str, Any]:
        """获取币种完整详情（聚合多个API）"""
        detail = {
            "keyword": keyword,
            "basic": None,
            "ai_summary": None,
            "trade_inflow": None,
            "exchange_info": None,
            "exchange_flow_detail": None,
            "fund_flow_history": None,
            "fund_volume_history": None,
            "holders_top": None,
            "chains": None,
        }
        token_symbol = None
        token_chain = None
        
        # 基础信息
        basic = self._request("POST", "/api/vs-token/queryCoin", json_body={
            "keyword": keyword
        })
        if basic.get("code") == 200:
            detail["basic"] = basic.get("data")
            if isinstance(detail["basic"], dict):
                token_symbol = detail["basic"].get("symbol") or detail["basic"].get("tokenSymbol")
                token_chain = detail["basic"].get("chain") or detail["basic"].get("chainName")
        
        # AI 分析摘要
        ai = self._request("GET", f"/api/ai/getAiCoinSummarize?vsTokenId={keyword}")
        if ai.get("code") == 200:
            detail["ai_summary"] = ai.get("data")
        
        # 资金流入数据
        inflow = self._request("GET", f"/api/trade/getCoinTradeInflow?keyword={keyword}")
        if inflow.get("code") == 200:
            detail["trade_inflow"] = inflow.get("data")
        
        # 交易所信息
        exchange = self._request("GET", f"/api/track/judge/getExchangeCoinInfo?keyword={keyword}")
        if exchange.get("code") == 200:
            detail["exchange_info"] = exchange.get("data")

        flow_detail = self.get_exchange_flow_detail(keyword)
        if flow_detail.get("code") == 200:
            detail["exchange_flow_detail"] = flow_detail.get("data")

        flow_history = self.get_fund_trade_history_total(
            keyword,
            time_particle="12h",
            limit_size=60,
            flow=True,
            trade_type=2,
        )
        if flow_history.get("code") == 200:
            detail["fund_flow_history"] = flow_history.get("data")

        volume_history = self.get_fund_trade_history_total(
            keyword,
            time_particle="12h",
            limit_size=60,
            flow=False,
            trade_type=2,
        )
        if volume_history.get("code") == 200:
            detail["fund_volume_history"] = volume_history.get("data")

        holders = self.get_holder_page(
            keyword,
            page=1,
            page_size=20,
            symbol=token_symbol,
            chain=token_chain,
        )
        if holders.get("code") == 200:
            detail["holders_top"] = holders.get("data")

        chains = self.get_chain_page(symbol=token_symbol or "", page=1, page_size=20)
        if chains.get("code") == 200:
            detail["chains"] = chains.get("data")
        
        return {"code": 200, "data": detail}
    
    def get_coin_by_symbol(self, symbol: str) -> Dict[str, Any]:
        """通过币种符号获取详情"""
        # 先搜索获取 keyword
        search = self._request("POST", "/api/vs-token/queryCoin", json_body={
            "search": symbol,
            "page": 1,
            "pageSize": 10
        })
        if search.get("code") != 200:
            return search
        
        coins = search.get("data", {}).get("list", [])
        for coin in coins:
            if coin.get("symbol", "").upper() == symbol.upper():
                keyword = int(coin.get("vsTokenId") or coin.get("keyword") or 0)
                if keyword:
                    return self.get_coin_detail(keyword)
        
        return {"error": f"Coin {symbol} not found"}
    
    def get_ai_summary(self, keyword: int) -> Dict[str, Any]:
        """获取币种 AI 分析摘要"""
        return self._request("GET", f"/api/ai/getAiCoinSummarize?vsTokenId={keyword}")
    
    def get_trade_inflow(self, keyword: int) -> Dict[str, Any]:
        """获取币种资金流入数据"""
        return self._request("GET", f"/api/trade/getCoinTradeInflow?keyword={keyword}")
    

    def get_exchange_flow_detail(self, keyword: int) -> Dict[str, Any]:
        """Get exchange flow detail (time ranges) for a coin."""
        return self._request(
            "POST",
            f"/api/analysis/coin/exchange-flow-detail?keyword={keyword}",
            json_body={},
        )

    def get_fund_trade_history_total(
        self,
        keyword: int,
        time_particle: str = "12h",
        limit_size: int = 100,
        flow: bool = True,
        trade_type: int = 2,
    ) -> Dict[str, Any]:
        """Get fund/volume history by time buckets."""
        return self._request("POST", "/api/trade/fundTradeHistoryTotal", json_body={
            "timeParticle": time_particle,
            "limitSize": limit_size,
            "flow": bool(flow),
            "keyword": keyword,
            "type": trade_type,
        })

    def get_holder_page(
        self,
        keyword: int,
        page: int = 1,
        page_size: int = 20,
        address: str = "",
        coin_key: Optional[str] = None,
        symbol: Optional[str] = None,
        chain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get holder page for a coin (top holders)."""
        final_coin_key = coin_key or self._format_coin_key(symbol, chain)
        return self._request("POST", "/api/track/judge/holder-page", json_body={
            "page": page,
            "pageSize": page_size,
            "address": address or "",
            "coinKey": final_coin_key,
            "keyword": keyword,
        })

    def get_chain_page(self, symbol: str = "", page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Get chain list for tokens (CMC-style chain page)."""
        return self._request("POST", "/api/cmc/coin/chain/page", json_body={
            "symbol": symbol or "",
            "page": page,
            "pageSize": page_size,
        })

    def get_kline_time(self) -> Dict[str, Any]:
        """Get kline time reference."""
        return self._request("GET", "/api/kline/time")

    def get_trade_kline_history(
        self,
        trade_pairs: str,
        kline_type: str = "01",
        bucket_type: str = "1s",
        size: int = 300,
    ) -> Dict[str, Any]:
        """Get kline history via tradePairs payload."""
        return self._request("POST", "/api/kline/history", json_body={
            "tradePairs": trade_pairs,
            "klineType": kline_type,
            "bucketType": bucket_type,
            "size": size,
        })

    def get_trade_kline_miss(
        self,
        trade_pairs: str,
        kline_type: str = "01",
        start: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get missing kline ranges for tradePairs."""
        payload: Dict[str, Any] = {"tradePairs": trade_pairs, "klineType": kline_type}
        if start is not None:
            payload["start"] = start
        return self._request("POST", "/api/kline/missQuery", json_body=payload)

    def get_coin_kline(self, keyword: int) -> Dict[str, Any]:
        """获取币种K线数据"""
        return self._request("GET", f"/api/track/judge/getTradeCoinKline?keyword={keyword}")
    
    def get_dense_area(self, keyword: int, days: int = 90) -> Dict[str, Any]:
        """
        获取主力位数据（图表上的绿色水平线）
        
        API: /api/dense/getDenseAreaKLineHistory
        
        Args:
            keyword: 币种ID
            days: 查询天数，默认90天
        
        Returns:
            主力位数据列表，每个点包含:
            - time: 时间戳(毫秒)
            - type: 类型(2=主力位)
            - price: 主力位价格(绿色线的Y轴值)
        """
        import time
        end_time = int(time.time() * 1000)
        begin_time = end_time - (days * 24 * 60 * 60 * 1000)
        
        payload = {
            "vsTokenId": str(keyword),
            "beginTime": begin_time,
            "endTime": end_time,
        }
        resp = self._request("POST", "/api/dense/getDenseAreaKLineHistory", json_body=payload)
        if resp.get("code") == 200 and resp.get("data"):
            return resp
        fallback = self._request("POST", "/api/dense/getDenseAreaKLineHistory", json_body={
            "beginTime": begin_time,
            "endTime": end_time,
        })
        return fallback or resp
    
    def get_hold_cost(self, keyword: int, days: int = 90) -> Dict[str, Any]:
        """
        获取主力成本数据（持仓成本曲线）
        
        API: /api/track/judge/coin/getHoldCost
        
        Args:
            keyword: 币种ID
            days: 查询天数，默认90天
        
        Returns:
            主力成本数据，包含:
            - holdingPrice: 每日主力成本价格
            - price: 每日收盘价
            - balance: 每日余额
        """
        import time
        end_time = int(time.time() * 1000)
        begin_time = end_time - (days * 24 * 60 * 60 * 1000)
        
        return self._request("POST", "/api/track/judge/coin/getHoldCost", json_body={
            "keyword": keyword,
            "begin": begin_time,
            "end": end_time
        })
    
    def get_main_force_position(self, keyword: int, days: int = 90) -> Dict[str, Any]:
        """
        获取主力位数据（密集区，图表上的绿色水平线）
        
        Args:
            keyword: 币种ID
            days: 查询天数
        
        Returns:
            主力位数据
        """
        return self.get_dense_area(keyword, days)
    
    def get_detailed_inflow(self, keyword: int) -> Dict[str, Any]:
        """
        获取详细资金流入数据（含多个时间周期）
        
        Returns:
            包含5m/15m/30m/1h/4h/8h/12h/24h等多个周期的资金流入数据
            - stopTradeInflow: 现货资金流入
            - contractTradeInflow: 合约资金流入
            - stopTradeAmount: 现货交易量
            - contractTradeAmount: 合约交易量
        """
        return self._request("GET", f"/api/trade/getCoinTradeInflow?keyword={keyword}")
    
    def get_kline_history(self, keyword: int, interval: str = "1h", limit: int = 500) -> Dict[str, Any]:
        """
        获取K线历史数据
        
        Args:
            keyword: 币种ID
            interval: K线间隔 (1m/5m/15m/30m/1h/4h/1d等)
            limit: 返回数量
        """
        import time
        end_time = int(time.time() * 1000)
        
        return self._request("POST", "/api/kline/history", json_body={
            "vsTokenId": str(keyword),
            "interval": interval,
            "limit": limit,
            "endTime": end_time
        })
    
    def list_all_coins(self, page: int = 1, page_size: int = 100, is_binance: bool = False) -> Dict[str, Any]:
        """获取所有币种列表"""
        return self._request("POST", "/api/vs-token/queryCoin", json_body={
            "search": "",
            "isBinance": is_binance,
            "page": page,
            "pageSize": page_size
        })
    
    # ==================== 榜单和链上数据 ====================
    
    def get_coin_rank(self, rank_type: int = 1, page: int = 1, page_size: int = 20, 
                      order_by: str = "percentChange24h", asc: bool = False) -> Dict[str, Any]:
        """
        获取涨跌幅排行榜
        
        Args:
            rank_type: 1=涨幅榜, 其他=跌幅榜
            page: 页码
            page_size: 每页数量
            order_by: 排序字段 (percentChange24h/marketCap等)
            asc: 是否升序
        """
        return self._request("POST", "/api/analysis/crypto/coin-rank", json_body={
            "page": page,
            "pageSize": page_size,
            "order": [{"column": order_by, "asc": asc}, {"column": "marketCap", "asc": False}],
            "type": rank_type
        })
    
    def get_quality_rank(self, page: int = 1, page_size: int = 20, 
                         order_by: str = "marketCap", asc: bool = False) -> Dict[str, Any]:
        """
        获取主力成本排行榜
        
        Returns:
            包含 cost(主力成本), deviation(偏离度), costChange(成本变化) 等字段
        """
        return self._request("POST", "/api/analysis/coin/quality-rank", json_body={
            "page": page,
            "pageSize": page_size,
            "order": [{"column": order_by, "asc": asc}],
            "filters": []
        })
    
    def get_token_flow(self, time_period: str = "H12", page: int = 1, page_size: int = 20,
                       order_by: str = "inFlowValue", asc: bool = False) -> Dict[str, Any]:
        """
        获取代币流向数据
        
        Args:
            time_period: 时间周期 (H1/H4/H8/H12/D1/D2/D3/D7/D10/D15/D30/D60/D90/D120/D150/D180)
            page: 页码
            page_size: 每页数量
            order_by: 排序字段 (inFlowValue/outValue等)
            asc: 是否升序
        
        Returns:
            代币流入流出数据，包含:
            - inAmount/inValue: 流入数量/金额
            - outAmount/outValue: 流出数量/金额
            - inFlowValue: 净流入金额
            - inFlowValueChange: 净流入变化率
        """
        return self._request("POST", "/api/analysis/coin/getCoinExchangeFlowPage", json_body={
            "page": page,
            "pageSize": page_size,
            "order": [{"column": order_by, "asc": asc}],
            "filters": [],
            "time": time_period
        })
    
    def get_whale_flow(self, trade_type: int = 1, time_period: str = "m5", page: int = 1, 
                       page_size: int = 20, order_by: str = "tradeInflow", asc: bool = False) -> Dict[str, Any]:
        """
        获取主力资金流榜单
        
        Args:
            trade_type: 1=现货, 2=合约
            time_period: 时间周期 (m5/m15/m30/h1/h4/h8/h12/h24等)
            page: 页码
            page_size: 每页数量
            order_by: 排序字段 (tradeInflow/tradeAmount等)
            asc: 是否升序
        
        Returns:
            主力资金流数据，包含:
            - tradeInflow: 资金净流入
            - tradeAmount: 交易量
            - tradeIn/tradeOut: 流入/流出
            - tradeInflowChange: 流入变化率
        """
        return self._request("POST", "/api/trade/getTimeTradePage", json_body={
            "page": page,
            "pageSize": page_size,
            "order": [{"column": order_by, "asc": asc}],
            "filters": [],
            "time": time_period,
            "type": trade_type
        })
    
    def get_trade_coin_top(self, trade_type: int = 1) -> Dict[str, Any]:
        """
        获取交易热门币种（24小时和90天）
        
        Args:
            trade_type: 1=现货, 2=合约
        
        Returns:
            包含 coinCache24HList 和 coinCache90DList
        """
        return self._request("GET", f"/api/chance/getTradeCoinTop?type={trade_type}")
    
    def get_ai_signals(self, trade_type: int = 2, page: int = 1, page_size: int = 20,
                       order_by: str = "endTime", asc: bool = False) -> Dict[str, Any]:
        """
        获取AI智能选币信号（异动看涨监控）
        
        Args:
            trade_type: 1=现货, 2=合约
            page: 页码
            page_size: 每页数量
            order_by: 排序字段
            asc: 是否升序
        
        Returns:
            AI选币信号列表，包含:
            - symbol: 币种符号
            - beginPrice/price: 推送价格/当前价格
            - gains/decline: 推送后涨幅/跌幅
            - alpha: 是否Alpha信号
            - fomo: 是否FOMO信号
            - bullishRatio: 看涨情绪比例
            - number24h/numberNot24h: 小周期/大周期异动次数
        """
        return self._request("POST", "/api/chance/getFundsMovementPage", json_body={
            "page": page,
            "pageSize": page_size,
            "order": [{"column": order_by, "asc": asc}],
            "filters": [],
            "tradeType": trade_type
        })
    
    def get_opportunity_signals(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        获取机会看涨监控信号（AI评分系统）
        
        Returns:
            机会代币列表，包含:
            - symbol: 币种符号
            - score/beforeScore: 当前/之前评分
            - scoreChange: 评分变化率
            - grade: 评级
            - bullishRatio/bearishRatio: 看涨/看跌情绪
            - gains/decline: 涨幅/跌幅
            - percentChangeRanking: 各周期涨跌幅排名
        """
        return self._request("POST", "/api/chance/getChangeCoinPage", json_body={
            "page": page,
            "pageSize": page_size,
            "order": {"column": "date", "asc": False},
            "volumes": [],
            "inflows": [],
            "marketCap": True,
            "circulationRate": True
        })
    
    def get_risk_signals(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        获取风险看跌监控信号
        
        Returns:
            风险代币列表，包含:
            - symbol: 币种符号
            - score: AI评分 (75-80为下跌风险)
            - grade: 风险等级
            - gains/retracement: 涨幅/回撤
            - percentChangeRanking: 各周期涨跌幅排名
        """
        return self._request("POST", "/api/chance/getChangeCoinRiskPage", json_body={
            "page": page,
            "pageSize": page_size,
            "order": {"column": "date", "asc": False},
            "volumes": [],
            "inflows": [],
            "marketCap": True,
            "circulationRate": True
        })
    
    # ==================== 综合数据 ====================
    
    def get_market_overview(self) -> Dict[str, Any]:
        """获取市场概览（聚合多个数据源）"""
        return {
            "code": 200,
            "data": {
                "signals": self.get_all_signals().get("data", [])[:10],
                "gainers": self.get_gainers(page_size=10).get("data", {}).get("records", []),
                "losers": self.get_losers(page_size=10).get("data", {}).get("records", []),
                "funds_movement": self.get_funds_movement(page_size=10).get("data", {}).get("records", []),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# 便捷函数
_default_client: Optional[ValuScanClient] = None

def get_client() -> ValuScanClient:
    global _default_client
    if _default_client is None:
        _default_client = ValuScanClient()
    return _default_client

def get_signals() -> Dict[str, Any]:
    return get_client().get_all_signals()

def get_gainers(page_size: int = 20) -> Dict[str, Any]:
    return get_client().get_gainers(page_size=page_size)

def get_losers(page_size: int = 20) -> Dict[str, Any]:
    return get_client().get_losers(page_size=page_size)

def get_funds_movement(page_size: int = 20) -> Dict[str, Any]:
    return get_client().get_funds_movement(page_size=page_size)

def get_market_overview() -> Dict[str, Any]:
    return get_client().get_market_overview()
