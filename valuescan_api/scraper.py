#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ValuScan 全面数据抓取器
通过 API 获取所有币种数据
"""
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
TOKEN_FILE = BASE_DIR / "signal_monitor" / "valuescan_localstorage.json"
DATA_DIR = BASE_DIR / "valuescan_api" / "data"
API_BASE = "https://api.valuescan.io"


class ValuScanScraper:
    """ValuScan 数据抓取器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.trust_env = False
        self.token = self._load_token()
        DATA_DIR.mkdir(exist_ok=True)
    
    def _load_token(self) -> Optional[str]:
        try:
            data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
            return (data.get("account_token") or "").strip()
        except Exception:
            return None
    
    def _headers(self) -> Dict[str, str]:
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
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    def _request(self, method: str, path: str, **kwargs) -> Dict:
        url = f"{API_BASE}{path}"
        try:
            resp = self.session.request(method, url, headers=self._headers(), timeout=30, **kwargs)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_coin_rank(self, rank_type: int = 1, page: int = 1, page_size: int = 100) -> Dict:
        """获取涨跌榜 (type=1涨幅, type=2跌幅)"""
        return self._request("POST", "/api/analysis/crypto/coin-rank", json={
            "page": page,
            "pageSize": page_size,
            "type": rank_type,
            "order": [
                {"column": "percentChange24h", "asc": rank_type == 2},
                {"column": "marketCap", "asc": False}
            ]
        })
    
    def get_all_coins(self, rank_type: int = 1) -> List[Dict]:
        """获取所有币种数据"""
        all_coins = []
        page = 1
        page_size = 100
        
        while True:
            print(f"  获取第 {page} 页...")
            resp = self.get_coin_rank(rank_type, page, page_size)
            if resp.get("code") != 200:
                break
            
            data = resp.get("data", {})
            coins = data.get("list", [])
            if not coins:
                break
            
            all_coins.extend(coins)
            total = data.get("total", 0)
            
            if len(all_coins) >= total:
                break
            
            page += 1
            time.sleep(0.5)
        
        return all_coins
    
    def get_funds_movement(self, page: int = 1, page_size: int = 100, trade_type: int = 2) -> Dict:
        """获取资金异动"""
        return self._request("POST", "/api/chance/getFundsMovementPage", json={
            "page": page,
            "pageSize": page_size,
            "tradeType": trade_type,
            "order": [{"column": "endTime", "asc": False}],
            "filters": []
        })
    
    def get_ai_messages(self, page: int = 1, page_size: int = 100) -> Dict:
        """获取 AI 消息"""
        return self._request("POST", "/api/account/message/aiMessagePage", json={
            "page": page,
            "pageSize": page_size
        })
    
    def get_warn_messages(self) -> Dict:
        """获取预警消息"""
        return self._request("GET", "/api/account/message/getWarnMessage")
    
    def get_token_detail(self, keyword: int) -> Dict:
        """获取代币详情"""
        return self._request("POST", "/api/vs-token/queryCoin", json={
            "keyword": keyword
        })
    
    def scrape_all(self) -> Dict[str, Any]:
        """抓取所有数据"""
        print("=" * 60)
        print("ValuScan 全面数据抓取")
        print("=" * 60)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "data": {}
        }
        
        # 1. 涨幅榜
        print("\n1. 抓取涨幅榜...")
        gainers = self.get_all_coins(rank_type=1)
        result["data"]["gainers"] = {
            "count": len(gainers),
            "list": gainers
        }
        print(f"   ✓ 获取 {len(gainers)} 条")
        
        # 2. 跌幅榜
        print("\n2. 抓取跌幅榜...")
        losers = self.get_all_coins(rank_type=2)
        result["data"]["losers"] = {
            "count": len(losers),
            "list": losers
        }
        print(f"   ✓ 获取 {len(losers)} 条")
        
        # 3. 资金异动(合约)
        print("\n3. 抓取资金异动(合约)...")
        movement_contract = self.get_funds_movement(page_size=100, trade_type=2)
        if movement_contract.get("code") == 200:
            data = movement_contract.get("data", {})
            result["data"]["funds_movement_contract"] = {
                "count": data.get("total", 0),
                "list": data.get("list", [])
            }
            print(f"   ✓ 获取 {len(data.get('list', []))} 条")
        
        # 4. 资金异动(现货)
        print("\n4. 抓取资金异动(现货)...")
        movement_spot = self.get_funds_movement(page_size=100, trade_type=1)
        if movement_spot.get("code") == 200:
            data = movement_spot.get("data", {})
            result["data"]["funds_movement_spot"] = {
                "count": data.get("total", 0),
                "list": data.get("list", [])
            }
            print(f"   ✓ 获取 {len(data.get('list', []))} 条")
        
        # 5. AI 消息
        print("\n5. 抓取 AI 消息...")
        ai_messages = self.get_ai_messages(page_size=100)
        if ai_messages.get("code") == 200:
            data = ai_messages.get("data", {})
            result["data"]["ai_messages"] = {
                "total": data.get("total", 0),
                "list": data.get("list", [])
            }
            print(f"   ✓ 获取 {len(data.get('list', []))} 条 (总数: {data.get('total', 0)})")
        
        # 6. 预警消息
        print("\n6. 抓取预警消息...")
        warn_messages = self.get_warn_messages()
        if warn_messages.get("code") == 200:
            data = warn_messages.get("data", [])
            result["data"]["warn_messages"] = {
                "count": len(data),
                "list": data
            }
            print(f"   ✓ 获取 {len(data)} 条")
        
        # 保存数据
        output_file = DATA_DIR / f"valuescan_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n数据已保存到: {output_file}")
        
        # 同时保存最新数据
        latest_file = DATA_DIR / "latest.json"
        latest_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        
        # 统计
        print("\n" + "=" * 60)
        print("抓取完成统计:")
        print(f"  - 涨幅榜: {result['data'].get('gainers', {}).get('count', 0)} 条")
        print(f"  - 跌幅榜: {result['data'].get('losers', {}).get('count', 0)} 条")
        print(f"  - 资金异动(合约): {result['data'].get('funds_movement_contract', {}).get('count', 0)} 条")
        print(f"  - 资金异动(现货): {result['data'].get('funds_movement_spot', {}).get('count', 0)} 条")
        print(f"  - AI消息: {result['data'].get('ai_messages', {}).get('total', 0)} 条")
        print(f"  - 预警消息: {result['data'].get('warn_messages', {}).get('count', 0)} 条")
        print("=" * 60)
        
        return result


def main():
    scraper = ValuScanScraper()
    scraper.scrape_all()


if __name__ == "__main__":
    main()
