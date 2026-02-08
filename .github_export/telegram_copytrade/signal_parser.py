"""
Telegram 信号解析器
解析群组消息中的交易信号
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional, Tuple
from datetime import datetime


@dataclass
class TradeSignal:
    """交易信号数据类"""
    signal_type: str  # "OPEN" 或 "CLOSE"
    symbol: str       # 交易对，如 "ETHUSDT"
    direction: str    # "LONG" 或 "SHORT"
    leverage: int     # 杠杆倍数
    position_size: float  # 仓位大小
    entry_price: float    # 开仓价格
    current_price: float  # 当前价格
    margin: float         # 保证金
    margin_type: str      # "ISOLATED" 或 "CROSSED"
    pnl: float = 0.0      # 收益额
    pnl_percent: float = 0.0  # 收益百分比
    raw_message: str = ""     # 原始消息
    timestamp: datetime = None


class SignalParser:
    """信号解析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 开仓信号关键词
        self.open_keywords = [
            "新开仓", "开仓", "建仓", "入场", "开单"
        ]
        
        # 平仓信号关键词
        self.close_keywords = [
            "已平仓", "平仓", "清仓", "出场", "止盈", "止损"
        ]
    
    def parse(self, message: str) -> Optional[TradeSignal]:
        """
        解析消息，提取交易信号
        
        Args:
            message: 原始消息文本
            
        Returns:
            TradeSignal 或 None
        """
        if not message:
            return None
            
        # 判断信号类型
        signal_type = self._detect_signal_type(message)
        if not signal_type:
            return None
            
        try:
            # 解析币种信息
            symbol, leverage, margin_type = self._parse_symbol_info(message)
            if not symbol:
                self.logger.debug(f"无法解析币种信息: {message[:50]}")
                return None
                
            # 解析方向
            direction = self._parse_direction(message)
            if not direction:
                self.logger.debug(f"无法解析方向: {message[:50]}")
                return None
                
            # 解析仓位
            position_size = self._parse_position_size(message, symbol)
            
            # 解析价格
            entry_price = self._parse_price(message, "开仓价")
            current_price = self._parse_price(message, "当前价")
            
            # 解析保证金
            margin = self._parse_margin(message)
            
            # 解析收益（平仓信号）
            pnl, pnl_percent = self._parse_pnl(message)
            
            signal = TradeSignal(
                signal_type=signal_type,
                symbol=symbol,
                direction=direction,
                leverage=leverage,
                position_size=position_size,
                entry_price=entry_price,
                current_price=current_price,
                margin=margin,
                margin_type=margin_type,
                pnl=pnl,
                pnl_percent=pnl_percent,
                raw_message=message,
                timestamp=datetime.now()
            )
            
            self.logger.info(f"解析到{signal_type}信号: {symbol} {direction} {leverage}x")
            return signal
            
        except Exception as e:
            self.logger.error(f"解析信号失败: {e}")
            return None
    
    def _detect_signal_type(self, message: str) -> Optional[str]:
        """检测信号类型"""
        for keyword in self.close_keywords:
            if keyword in message:
                return "CLOSE"
        for keyword in self.open_keywords:
            if keyword in message:
                return "OPEN"
        return None
    
    def _parse_symbol_info(self, message: str) -> Tuple[Optional[str], int, str]:
        """
        解析币种信息
        
        Returns:
            (symbol, leverage, margin_type)
        """
        # 匹配格式: 【币种】：ETHUSDT|永续|20x 或 【币种】: ETHUSDT | 永续 | 5x
        pattern = r'【币种】[：:]\s*([A-Z]+USDT?)\s*[|｜]\s*永续\s*[|｜]\s*(\d+)x'
        match = re.search(pattern, message, re.IGNORECASE)
        
        if match:
            symbol = match.group(1).upper()
            if not symbol.endswith("USDT"):
                symbol += "USDT"
            leverage = int(match.group(2))
            
            # 检测保证金类型
            margin_type = "CROSSED" if "全仓" in message else "ISOLATED"
            
            return symbol, leverage, margin_type
        
        return None, 0, "ISOLATED"
    
    def _parse_direction(self, message: str) -> Optional[str]:
        """解析交易方向"""
        if "做多" in message or "🟩" in message:
            return "LONG"
        elif "做空" in message or "🟥" in message:
            return "SHORT"
        return None
    
    def _parse_position_size(self, message: str, symbol: str) -> float:
        """解析仓位大小"""
        # 获取基础币种（去掉USDT）
        base_symbol = symbol.replace("USDT", "")
        
        # 匹配格式: 【仓位】：361.916 ETH 或 【仓位】: 21.518 ETH
        pattern = rf'【仓位】[：:]\s*([\d,\.]+)\s*{base_symbol}'
        match = re.search(pattern, message, re.IGNORECASE)
        
        if match:
            size_str = match.group(1).replace(",", "")
            return float(size_str)
        
        return 0.0
    
    def _parse_price(self, message: str, price_type: str) -> float:
        """解析价格"""
        # 匹配格式: 【开仓价】：3,388.46 或 【当前价】: 3,231.67
        pattern = rf'【{price_type}】[：:]\s*([\d,\.]+)'
        match = re.search(pattern, message)
        
        if match:
            price_str = match.group(1).replace(",", "")
            return float(price_str)
        
        return 0.0
    
    def _parse_margin(self, message: str) -> float:
        """解析保证金"""
        # 匹配格式: 【保证金】：3,476.95 USDT(全仓)
        pattern = r'【保证金】[：:]\s*([\d,\.]+)\s*USDT'
        match = re.search(pattern, message)
        
        if match:
            margin_str = match.group(1).replace(",", "")
            return float(margin_str)
        
        return 0.0
    
    def _parse_pnl(self, message: str) -> Tuple[float, float]:
        """
        解析收益
        
        Returns:
            (pnl_amount, pnl_percent)
        """
        pnl = 0.0
        pnl_percent = 0.0
        
        # 匹配收益额: +3,373.71 USDT 或 -100.00 USDT
        # 支持【最终收益额】和【收益额】
        pnl_pattern = r'【(?:最终)?收益额】[：:]\s*([+-]?[\d,\.]+)\s*USDT'
        pnl_match = re.search(pnl_pattern, message)
        
        if pnl_match:
            pnl_str = pnl_match.group(1).replace(",", "")
            pnl = float(pnl_str)
        
        # 匹配收益百分比: (+97.03%) 或 (-5.00%)
        percent_pattern = r'\(([+-]?[\d\.]+)%\)'
        percent_match = re.search(percent_pattern, message)
        
        if percent_match:
            pnl_percent = float(percent_match.group(1))
        
        return pnl, pnl_percent


def test_parser():
    """测试解析器"""
    parser = SignalParser()
    
    # 测试开仓信号
    open_msg = """🚀 注意，大佬新开仓
【币种】: ETHUSDT | 永续 | 5x
【方向】: 做多 🟩
【仓位】: 361.916 ETH
【开仓价】: 3,207.56
【当前价】: 3,209.58
【保证金】: 232,319.67 USDT(全仓)
【收益额】: +732.80 USDT(+0.32%)"""

    result = parser.parse(open_msg)
    if result:
        print(f"开仓信号: {result}")
    else:
        print("解析失败")
    
    # 测试平仓信号
    close_msg = """🚨 已平仓提醒
【币种】：ETHUSDT|永续|20x
【方向】：做空 🟥
【仓位】：21.518 ETH
【开仓价】：3,388.46
【当前价】：3,231.67
【保证金】：3,476.95 USDT(全仓)
【最终收益额】：+3,373.71 USDT(+97.03%)"""

    result = parser.parse(close_msg)
    if result:
        print(f"平仓信号: {result}")
    else:
        print("解析失败")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    test_parser()
