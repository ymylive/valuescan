from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List


@dataclass
class TradeMetrics:
    avg_holding_hours: float = 0.0
    avg_leverage: float = 0.0
    preferred_pairs: List[str] = field(default_factory=list)
    long_ratio: float = 0.5
    trade_count: int = 0
    win_rate: float = 0.0
    max_drawdown: float = 0.0


def analyze_trade_history(
    trades: Iterable[Dict],
    *,
    include_pnl_metrics: bool,
    default_win_rate: float = 0.0,
    default_max_drawdown: float = 0.0,
) -> TradeMetrics:
    metrics = TradeMetrics(win_rate=default_win_rate, max_drawdown=default_max_drawdown)
    trade_list = list(trades or [])
    if not trade_list:
        return metrics

    holding_times: List[float] = []
    leverages: List[float] = []
    pair_counts: Dict[str, int] = {}
    long_count = 0
    wins = 0
    losses = 0
    pnl_list: List[float] = []

    for trade in trade_list:
        # 支持多种字段名: opened/openTime, closed/closeTime
        open_time = trade.get("opened") or trade.get("openTime", 0)
        close_time = trade.get("closed") or trade.get("closeTime", 0)
        if open_time and close_time:
            hours = (close_time - open_time) / (1000 * 60 * 60)
            if 0 < hours < 10000:
                holding_times.append(hours)

        leverage = trade.get("leverage", 0)
        if leverage:
            leverages.append(float(leverage))

        symbol = trade.get("symbol", "")
        if symbol:
            pair_counts[symbol] = pair_counts.get(symbol, 0) + 1

        # 支持多种side格式: Short/Long 或 BUY/SELL
        side = trade.get("side", "").upper()
        if side in ("BUY", "LONG"):
            long_count += 1

        if include_pnl_metrics:
            # 支持多种pnl字段名: closingPnl, pnl, realizedPnl
            pnl = float(trade.get("closingPnl") or trade.get("pnl") or trade.get("realizedPnl", 0) or 0)
            if pnl != 0:
                pnl_list.append(pnl)
                if pnl > 0:
                    wins += 1
                else:
                    losses += 1

    metrics.trade_count = len(trade_list)
    if holding_times:
        metrics.avg_holding_hours = sum(holding_times) / len(holding_times)
    if leverages:
        metrics.avg_leverage = sum(leverages) / len(leverages)

    sorted_pairs = sorted(pair_counts.items(), key=lambda x: x[1], reverse=True)
    metrics.preferred_pairs = [p[0] for p in sorted_pairs[:5]]

    if metrics.trade_count > 0:
        metrics.long_ratio = long_count / metrics.trade_count

    if include_pnl_metrics:
        total_trades = wins + losses
        if total_trades > 0 and metrics.win_rate == 0:
            metrics.win_rate = wins / total_trades
        if pnl_list and metrics.max_drawdown == 0:
            cumulative = 0.0
            peak = 0.0
            max_dd = 0.0
            for pnl in pnl_list:
                cumulative += pnl
                if cumulative > peak:
                    peak = cumulative
                dd = (peak - cumulative) / max(peak, 1) * 100 if peak > 0 else 0
                if dd > max_dd:
                    max_dd = dd
            metrics.max_drawdown = max_dd

    return metrics


def analyze_transfers(transfers: Iterable[Dict], *, include_details: bool) -> List[Dict]:
    margin_additions: List[Dict] = []
    for record in transfers or []:
        trans_type = record.get("transType", "")
        amount = float(record.get("amount", 0))
        if trans_type in ("LEAD_DEPOSIT", "LEAD_FEE_DEPOSIT", "LEAD_INVEST") and amount > 0:
            item = {
                "time": record.get("time", 0),
                "amount": amount,
                "coin": record.get("coin", "USDT"),
                "type": trans_type,
            }
            if include_details:
                item["from"] = record.get("from", "")
                item["to"] = record.get("to", "")
            margin_additions.append(item)
    return margin_additions
