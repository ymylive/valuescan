"""
优化的辅助线绘制算法
基于技术分析规则，精确绘制辅助线
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from scipy.signal import find_peaks, argrelextrema
from scipy.stats import linregress


class AuxiliaryLineDrawer:
    """辅助线绘制器"""

    def __init__(self, df: pd.DataFrame, current_price: float, atr: float = None):
        self.df = df
        self.current_price = current_price
        self.atr = atr or self._calculate_atr()
        self.highs = df['high'].values
        self.lows = df['low'].values
        self.closes = df['close'].values
        self.volumes = df['volume'].values

    def _calculate_atr(self, period: int = 14) -> float:
        """计算ATR"""
        high = self.df['high']
        low = self.df['low']
        close = self.df['close'].shift(1)
        tr = pd.concat([
            high - low,
            (high - close).abs(),
            (low - close).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        return float(atr.iloc[-1]) if not atr.empty and not pd.isna(atr.iloc[-1]) else self.current_price * 0.01

    def find_significant_pivots(self, lookback: int = 100) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]]]:
        """
        查找显著的枢轴点
        使用更严格的标准，确保枢轴点的重要性
        """
        # 只看最近的数据
        start_idx = max(0, len(self.highs) - lookback)

        # 查找高点
        high_peaks, high_props = find_peaks(
            self.highs[start_idx:],
            prominence=self.atr * 0.5,  # 显著性要求
            distance=5  # 最小间隔
        )

        # 查找低点
        low_peaks, low_props = find_peaks(
            -self.lows[start_idx:],
            prominence=self.atr * 0.5,
            distance=5
        )

        # 转换为全局索引
        high_pivots = [(i + start_idx, self.highs[i + start_idx]) for i in high_peaks]
        low_pivots = [(i + start_idx, self.lows[i + start_idx]) for i in low_peaks]

        # 按重要性排序（最近的权重更高）
        high_pivots.sort(key=lambda x: x[0], reverse=True)
        low_pivots.sort(key=lambda x: x[0], reverse=True)

        return high_pivots[:10], low_pivots[:10]  # 最多10个

    def draw_trendline(
        self,
        pivots: List[Tuple[int, float]],
        is_resistance: bool = True,
        min_touches: int = 2
    ) -> Optional[Dict[str, Any]]:
        """
        绘制趋势线
        严格遵循技术分析规则
        """
        if len(pivots) < 2:
            return None

        best_line = None
        best_score = 0

        # 尝试不同的点组合
        for i in range(len(pivots)):
            for j in range(i + 1, min(i + 5, len(pivots))):  # 只尝试相近的点
                p1_idx, p1_price = pivots[i]
                p2_idx, p2_price = pivots[j]

                # 计算斜率和截距
                if p2_idx == p1_idx:
                    continue

                slope = (p2_price - p1_price) / (p2_idx - p1_idx)
                intercept = p1_price - slope * p1_idx

                # 计算触碰次数
                touches = 0
                touch_indices = []
                tolerance = self.atr * 0.3

                series = self.highs if is_resistance else self.lows

                for k in range(p1_idx, len(series)):
                    line_value = slope * k + intercept
                    if abs(series[k] - line_value) <= tolerance:
                        touches += 1
                        touch_indices.append(k)

                if touches < min_touches:
                    continue

                # 检查线是否穿越价格（不应该）
                violations = 0
                for k in range(p1_idx, len(series)):
                    line_value = slope * k + intercept
                    if is_resistance:
                        if self.closes[k] > line_value + tolerance:
                            violations += 1
                    else:
                        if self.closes[k] < line_value - tolerance:
                            violations += 1

                if violations > touches * 0.3:  # 违规不能超过30%
                    continue

                # 计算得分
                score = touches * 10  # 触碰次数
                score -= violations * 5  # 违规惩罚
                score += (len(series) - p1_idx) / 10  # 长度奖励

                # 检查是否延伸到当前
                extends_to_current = (len(series) - p2_idx) < 20

                if extends_to_current:
                    score += 20

                if score > best_score:
                    best_score = score
                    best_line = {
                        'x1': p1_idx,
                        'y1': p1_price,
                        'x2': len(series) - 1,
                        'y2': slope * (len(series) - 1) + intercept,
                        'slope': slope,
                        'intercept': intercept,
                        'touches': touches,
                        'score': score,
                        'type': 'resistance' if is_resistance else 'support'
                    }

        return best_line

    def draw_channel(self, lookback: int = 100) -> Optional[Dict[str, Any]]:
        """
        绘制通道
        上下轨必须平行且都有效
        """
        high_pivots, low_pivots = self.find_significant_pivots(lookback)

        # 绘制上轨
        upper_line = self.draw_trendline(high_pivots, is_resistance=True, min_touches=2)
        if not upper_line:
            return None

        # 绘制下轨
        lower_line = self.draw_trendline(low_pivots, is_resistance=False, min_touches=2)
        if not lower_line:
            return None

        # 检查平行度
        slope_diff = abs(upper_line['slope'] - lower_line['slope'])
        slope_avg = (abs(upper_line['slope']) + abs(lower_line['slope'])) / 2 + 1e-9

        if slope_diff / slope_avg > 0.3:  # 斜率差异不能超过30%
            return None

        # 检查通道宽度
        width_start = upper_line['y1'] - lower_line['y1']
        width_end = upper_line['y2'] - lower_line['y2']

        if width_start <= 0 or width_end <= 0:
            return None

        if abs(width_end - width_start) / width_start > 0.3:  # 宽度变化不能超过30%
            return None

        # 判断通道类型
        if upper_line['slope'] > self.atr * 0.1:
            channel_type = 'ascending'
        elif upper_line['slope'] < -self.atr * 0.1:
            channel_type = 'descending'
        else:
            channel_type = 'horizontal'

        return {
            'type': 'channel',
            'subtype': channel_type,
            'upper': upper_line,
            'lower': lower_line,
            'score': (upper_line['score'] + lower_line['score']) / 2,
            'touches': upper_line['touches'] + lower_line['touches']
        }

    def draw_support_resistance_zones(self) -> List[Dict[str, Any]]:
        """
        绘制支撑/阻力区域
        基于价格聚集和成交量
        """
        zones = []

        # 使用Volume Profile找到高成交量区域
        price_min = self.df['low'].min()
        price_max = self.df['high'].max()
        num_bins = 50

        bins = np.linspace(price_min, price_max, num_bins)
        volume_profile = np.zeros(num_bins - 1)

        for i in range(len(self.df)):
            low_idx = np.searchsorted(bins, self.df['low'].iloc[i]) - 1
            high_idx = np.searchsorted(bins, self.df['high'].iloc[i]) - 1

            low_idx = max(0, min(low_idx, num_bins - 2))
            high_idx = max(0, min(high_idx, num_bins - 2))

            if low_idx <= high_idx:
                volume_profile[low_idx:high_idx + 1] += self.df['volume'].iloc[i] / (high_idx - low_idx + 1)

        # 找到高成交量区域
        threshold = np.percentile(volume_profile, 80)  # 前20%
        high_volume_indices = np.where(volume_profile >= threshold)[0]

        # 合并相邻区域
        if len(high_volume_indices) > 0:
            zones_temp = []
            current_zone = [high_volume_indices[0]]

            for i in range(1, len(high_volume_indices)):
                if high_volume_indices[i] - high_volume_indices[i - 1] <= 2:
                    current_zone.append(high_volume_indices[i])
                else:
                    zones_temp.append(current_zone)
                    current_zone = [high_volume_indices[i]]

            zones_temp.append(current_zone)

            # 转换为价格区域
            for zone_indices in zones_temp:
                zone_min = bins[min(zone_indices)]
                zone_max = bins[max(zone_indices) + 1]
                zone_mid = (zone_min + zone_max) / 2

                # 判断是支撑还是阻力
                if zone_mid < self.current_price:
                    zone_type = 'support'
                elif zone_mid > self.current_price:
                    zone_type = 'resistance'
                else:
                    continue

                zones.append({
                    'type': 'zone',
                    'subtype': zone_type,
                    'price_min': zone_min,
                    'price_max': zone_max,
                    'price_mid': zone_mid,
                    'volume': sum(volume_profile[i] for i in zone_indices),
                    'strength': sum(volume_profile[i] for i in zone_indices) / volume_profile.sum() * 100
                })

        return zones

    def draw_all_lines(self) -> Dict[str, Any]:
        """
        绘制所有辅助线
        返回完整的绘图数据
        """
        result = {
            'trendlines': [],
            'channels': [],
            'zones': []
        }

        # 1. 尝试绘制通道
        channel = self.draw_channel(lookback=100)
        if channel:
            result['channels'].append(channel)

        # 2. 如果没有通道，绘制独立的趋势线 (限制为最佳1条)
        if not channel:
            high_pivots, low_pivots = self.find_significant_pivots(100)

            # 阻力线
            resistance_line = self.draw_trendline(high_pivots, is_resistance=True, min_touches=2)

            # 支撑线
            support_line = self.draw_trendline(low_pivots, is_resistance=False, min_touches=2)

            # 只选择得分最高的一条
            if resistance_line and support_line:
                if resistance_line['score'] >= support_line['score']:
                    result['trendlines'].append(resistance_line)
                else:
                    result['trendlines'].append(support_line)
            elif resistance_line:
                result['trendlines'].append(resistance_line)
            elif support_line:
                result['trendlines'].append(support_line)

        # 3. 绘制支撑/阻力区域 (限制为2个最强的)
        zones = self.draw_support_resistance_zones()
        # 按强度排序
        zones.sort(key=lambda z: z.get('strength', 0), reverse=True)
        result['zones'] = zones[:2]  # 最多2个区域 (原: 3)

        return result


def draw_auxiliary_lines_optimized(
    df: pd.DataFrame,
    current_price: float,
    atr: float = None,
    ai_analysis: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    优化的辅助线绘制
    结合AI分析和本地算法
    """
    drawer = AuxiliaryLineDrawer(df, current_price, atr)
    lines = drawer.draw_all_lines()

    # 如果有AI分析，用AI的关键位增强
    if ai_analysis and 'key_levels' in ai_analysis:
        key_levels = ai_analysis['key_levels']

        # AI支撑位
        if 'supports' in key_levels:
            for item in key_levels['supports'][:3]:
                if isinstance(item, dict) and 'price' in item:
                    lines['zones'].append({
                        'type': 'zone',
                        'subtype': 'support',
                        'price_min': item['price'] * 0.998,
                        'price_max': item['price'] * 1.002,
                        'price_mid': item['price'],
                        'strength': item.get('strength', 50),
                        'reason': item.get('reason', ''),
                        'source': 'AI'
                    })

        # AI阻力位
        if 'resistances' in key_levels:
            for item in key_levels['resistances'][:3]:
                if isinstance(item, dict) and 'price' in item:
                    lines['zones'].append({
                        'type': 'zone',
                        'subtype': 'resistance',
                        'price_min': item['price'] * 0.998,
                        'price_max': item['price'] * 1.002,
                        'price_mid': item['price'],
                        'strength': item.get('strength', 50),
                        'reason': item.get('reason', ''),
                        'source': 'AI'
                    })

    return lines
