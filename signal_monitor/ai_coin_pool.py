"""
ValueScan AI 智能选币数据 -> AI500(coinpool) 兼容数据结构转换。

目标：
- 从网页表格（或任意行数据 dict）提取币种/价格/标记时间/标记价格/AI 评分等关键字段
- 输出与 `provider/data_provider.go` 兼容的 JSON 结构（success + data.coins）

本模块不依赖浏览器；抓取逻辑在 `ai_coin_pool_server.py` 中。
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence


BEIJING_TZ = timezone(timedelta(hours=8))


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    return str(value).strip()


def _parse_float(value: Any) -> Optional[float]:
    text = _clean_text(value)
    if not text:
        return None

    text = text.replace(",", "").replace("$", "").replace("USDT", "").strip()

    is_percent = text.endswith("%")
    if is_percent:
        text = text[:-1].strip()

    try:
        return float(text)
    except ValueError:
        return None


def _parse_datetime_to_epoch_seconds(value: Any) -> Optional[int]:
    """
    解析表格里常见的时间字符串（如 2025-12-15 08:00 / 2025-12-15 08:00:00）。
    默认按北京时间（UTC+8）解释：如果你的 ValueScan 界面使用其它时区，可在上层做二次转换。
    """
    text = _clean_text(value)
    if not text:
        return None

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(text, fmt)
            return int(dt.replace(tzinfo=BEIJING_TZ).timestamp())
        except ValueError:
            continue
    return None


def _first(row: Dict[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in row and row.get(key) not in (None, ""):
            return row.get(key)
    return None


def _extract_symbol(raw: Any) -> Optional[str]:
    symbol = _clean_text(raw)
    if not symbol:
        return None

    symbol = symbol.upper().strip()
    if symbol.startswith("$"):
        symbol = symbol[1:]
    if "/" in symbol:
        symbol = symbol.split("/", 1)[0]
    if symbol.endswith("USDT") and len(symbol) > 4:
        symbol = symbol[:-4]

    symbol = symbol.strip()
    return symbol or None


@dataclass(frozen=True)
class CoinPoolCoin:
    pair: str
    score: float
    start_time: int
    start_price: float
    last_score: float
    max_score: float
    max_price: float
    increase_percent: float


def row_to_coin_pool_coin(row: Dict[str, Any]) -> Optional[CoinPoolCoin]:
    """
    将 ValueScan 表格的一行（dict）转换为 AI500 coinpool CoinData。

    兼容中/英文列名（不同语言/版本 UI 可能不同）。
    """
    symbol = _extract_symbol(
        _first(
            row,
            keys=(
                "币种",
                "Symbol",
                "Coin",
                "Token",
                "symbol",
                "pair",
                "symbolName",
            ),
        )
    )
    if not symbol:
        return None

    price = _parse_float(_first(row, keys=("币价($)", "币价", "Price($)", "Price", "price")))
    mark_price = _parse_float(
        _first(row, keys=("标记价格($)", "标记价格", "Mark Price($)", "Mark Price", "mark_price"))
    )
    score = _parse_float(_first(row, keys=("AI评分", "AI Score", "Score", "score")))
    start_time = _parse_datetime_to_epoch_seconds(_first(row, keys=("标记时间", "Mark Time", "Time", "time")))

    if price is None or mark_price is None or score is None:
        return None

    if start_time is None:
        start_time = int(datetime.now(timezone.utc).timestamp())

    increase_percent = 0.0
    if mark_price != 0:
        increase_percent = (price - mark_price) / mark_price * 100.0

    pair = f"{symbol}USDT"

    return CoinPoolCoin(
        pair=pair,
        score=float(score),
        start_time=int(start_time),
        start_price=float(mark_price),
        last_score=float(score),
        max_score=float(score),
        max_price=float(max(price, mark_price)),
        increase_percent=float(increase_percent),
    )


def rows_to_coin_pool(
    rows: Iterable[Dict[str, Any]],
    limit: Optional[int] = None,
) -> List[CoinPoolCoin]:
    coins: List[CoinPoolCoin] = []
    for row in rows:
        coin = row_to_coin_pool_coin(row)
        if coin:
            coins.append(coin)
        if limit and len(coins) >= limit:
            break
    return coins


def coin_pool_response(
    coins: Sequence[CoinPoolCoin],
) -> Dict[str, Any]:
    return {
        "success": True,
        "data": {
            "coins": [asdict(c) for c in coins],
            "count": len(coins),
        },
    }
