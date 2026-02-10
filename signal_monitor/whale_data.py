"""
巨鲸数据模块 - 基于 ValueScan 资金流信号
无需外部 API Key，直接使用 ValueScan 已有的资金流数据
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

try:
    from .database import get_recent_signals
except ImportError:
    try:
        from database import get_recent_signals
    except ImportError:
        get_recent_signals = None


@dataclass
class WhaleAnalysis:
    """巨鲸分析结果"""
    symbol: str
    time_range_hours: int = 24
    total_transfers: int = 0
    total_volume_usd: float = 0.0
    exchange_inflow_usd: float = 0.0
    exchange_outflow_usd: float = 0.0
    net_flow_usd: float = 0.0
    signal: str = "neutral"
    signal_strength: int = 0
    analysis_text: str = ""

    def to_prompt_text(self) -> str:
        """生成用于AI分析的文本"""
        if self.total_transfers == 0:
            return f"## 资金流向分析 ({self.symbol})\n暂无资金流数据"

        lines = [
            f"## 资金流向分析 ({self.symbol}, 最近{self.time_range_hours}小时)",
            f"- 资金流信号数: {self.total_transfers}",
            f"- 流入信号: {int(self.exchange_inflow_usd)}次",
            f"- 流出信号: {int(self.exchange_outflow_usd)}次",
            f"- 净流向: {'流入' if self.net_flow_usd > 0 else '流出'} ({abs(int(self.net_flow_usd))}次)",
            f"- 信号: {self.signal} (强度: {self.signal_strength}/100)",
        ]
        if self.analysis_text:
            lines.append(f"\n分析: {self.analysis_text}")
        return "\n".join(lines)


def get_whale_analysis(symbol: str, hours: int = 24) -> WhaleAnalysis:
    """
    获取巨鲸/资金流分析 - 基于 ValueScan 信号

    Args:
        symbol: 币种 (BTC/ETH/SOL等)
        hours: 时间范围
    """
    analysis = WhaleAnalysis(symbol=symbol.upper(), time_range_hours=hours)

    if not get_recent_signals:
        analysis.analysis_text = "数据库模块不可用"
        return analysis

    try:
        # 获取最近的信号
        signals = get_recent_signals(hours=hours)
        if not signals:
            analysis.analysis_text = "暂无资金流数据"
            return analysis

        symbol_upper = symbol.upper()
        inflow_count = 0
        outflow_count = 0

        for sig in signals:
            sig_symbol = (sig.get("symbol") or "").upper()
            if symbol_upper not in sig_symbol:
                continue

            funds_type = sig.get("fundsType")
            if funds_type is None:
                continue

            analysis.total_transfers += 1

            # funds_type: 1=大单买入, 2=主力流入, 3=资金流入, 4=资金流出
            if funds_type in (1, 2, 3):
                inflow_count += 1
            elif funds_type == 4:
                outflow_count += 1

        analysis.exchange_inflow_usd = float(inflow_count)
        analysis.exchange_outflow_usd = float(outflow_count)
        analysis.net_flow_usd = float(inflow_count - outflow_count)

        # 生成信号
        if analysis.total_transfers < 3:
            analysis.signal = "neutral"
            analysis.signal_strength = 20
            analysis.analysis_text = "资金流信号较少，信号不明显"
        elif analysis.net_flow_usd > 2:
            analysis.signal = "bullish"
            analysis.signal_strength = min(80, 40 + int(analysis.net_flow_usd * 10))
            analysis.analysis_text = "资金净流入，主力可能在吸筹"
        elif analysis.net_flow_usd < -2:
            analysis.signal = "bearish"
            analysis.signal_strength = min(80, 40 + int(abs(analysis.net_flow_usd) * 10))
            analysis.analysis_text = "资金净流出，可能有抛售压力"
        else:
            analysis.signal = "neutral"
            analysis.signal_strength = 30
            analysis.analysis_text = "资金流入流出基本平衡"

    except Exception as e:
        analysis.analysis_text = f"分析失败: {e}"

    return analysis


def get_whale_prompt_text(symbol: str, hours: int = 24) -> str:
    """获取用于AI分析的资金流数据文本"""
    return get_whale_analysis(symbol, hours).to_prompt_text()


def detect_whale_anomaly(symbol: str = None, hours: int = 1, threshold: int = 5) -> Optional[Dict[str, Any]]:
    """
    检测资金异动

    Args:
        symbol: 币种 (None=全市场)
        hours: 时间范围
        threshold: 触发异动的信号数阈值
    """
    try:
        symbols = [symbol] if symbol else ["BTC", "ETH", "SOL", "DOGE"]
        total_inflow = 0
        total_outflow = 0
        total_count = 0

        for sym in symbols:
            analysis = get_whale_analysis(sym, hours)
            total_count += analysis.total_transfers
            total_inflow += int(analysis.exchange_inflow_usd)
            total_outflow += int(analysis.exchange_outflow_usd)

        if total_count < threshold:
            return None

        net_flow = total_inflow - total_outflow
        intensity = min(100, total_count * 10)

        if net_flow > 2:
            direction = "bullish"
            description = f"检测到资金异动: {total_count}个信号，净流入{net_flow}次"
        elif net_flow < -2:
            direction = "bearish"
            description = f"检测到资金异动: {total_count}个信号，净流出{abs(net_flow)}次"
        else:
            direction = "neutral"
            description = f"检测到资金异动: {total_count}个信号"

        return {
            "symbol": symbol or "MARKET",
            "type": "whale_anomaly",
            "direction": direction,
            "intensity": intensity,
            "description": description,
            "total_volume_usd": total_count,
            "net_flow_usd": net_flow,
            "transfer_count": total_count,
        }
    except Exception:
        return None


def get_market_whale_summary(hours: int = 24) -> str:
    """获取市场整体资金流摘要"""
    symbols = ["BTC", "ETH", "SOL", "DOGE"]
    summaries = []
    total_inflow = 0
    total_outflow = 0

    for symbol in symbols:
        try:
            analysis = get_whale_analysis(symbol, hours)
            if analysis.total_transfers > 0:
                net = int(analysis.net_flow_usd)
                summaries.append(f"- {symbol}: {analysis.total_transfers}个信号, "
                               f"净{'流入' if net > 0 else '流出'}{abs(net)}次")
                total_inflow += int(analysis.exchange_inflow_usd)
                total_outflow += int(analysis.exchange_outflow_usd)
        except Exception:
            continue

    if not summaries:
        return ""

    net_total = total_inflow - total_outflow
    lines = [
        f"## 市场资金流摘要 (最近{hours}小时)",
        f"- 流入信号: {total_inflow}次",
        f"- 流出信号: {total_outflow}次",
        f"- 净流向: {'流入' if net_total > 0 else '流出'} {abs(net_total)}次",
        "",
        "各币种详情:",
    ]
    lines.extend(summaries)

    if net_total > 5:
        lines.append("\n✅ 积极: 资金净流入，市场情绪偏多")
    elif net_total < -5:
        lines.append("\n⚠️ 警告: 资金净流出，注意风险")

    return "\n".join(lines)
