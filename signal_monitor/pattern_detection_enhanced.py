"""
增强版形态检测算法
主要改进：
1. 多时间框架分析
2. 动态自适应参数
3. 更精确的触碰检测
4. 形态强度评分系统
5. 突破预测
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from scipy.signal import find_peaks
from scipy.stats import linregress


class PatternDetector:
    """增强版形态检测器"""

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

    def _adaptive_tolerance(self, window: int) -> float:
        """动态容差 - 根据窗口期和波动率"""
        recent_volatility = np.std(self.closes[-window:]) / np.mean(self.closes[-window:])
        base_tol = self.atr * 0.5
        volatility_factor = 1.0 + (recent_volatility / 0.02)
        return base_tol * volatility_factor

    def _find_pivot_points(self, series: np.ndarray, window: int = 5, mode: str = "high") -> List[Tuple[int, float]]:
        """
        查找枢轴点 - 改进版
        使用scipy的find_peaks，更准确
        """
        if mode == "high":
            peaks, properties = find_peaks(series, distance=window, prominence=self.atr * 0.3)
            return [(int(i), float(series[i])) for i in peaks]
        else:
            valleys, properties = find_peaks(-series, distance=window, prominence=self.atr * 0.3)
            return [(int(i), float(series[i])) for i in valleys]

    def _fit_line_robust(self, points: List[Tuple[int, float]]) -> Tuple[float, float, float, List[int]]:
        """
        鲁棒线性拟合 - 使用RANSAC思想
        返回: (slope, intercept, r2, inlier_indices)
        """
        if len(points) < 2:
            return 0.0, 0.0, 0.0, []

        x = np.array([p[0] for p in points])
        y = np.array([p[1] for p in points])

        # 标准线性回归
        slope, intercept, r_value, p_value, std_err = linregress(x, y)
        r2 = r_value ** 2

        # 计算残差
        y_pred = slope * x + intercept
        residuals = np.abs(y - y_pred)

        # 识别内点 (残差小于1.5倍ATR)
        threshold = self.atr * 1.5
        inliers = np.where(residuals < threshold)[0].tolist()

        # 如果内点太少，降低阈值
        if len(inliers) < max(2, len(points) * 0.5):
            threshold = self.atr * 2.5
            inliers = np.where(residuals < threshold)[0].tolist()

        return float(slope), float(intercept), float(r2), inliers

    def _count_touches_precise(self, series: np.ndarray, slope: float, intercept: float,
                                start_idx: int, window: int, tolerance: float) -> Tuple[int, List[int]]:
        """
        精确触碰计数
        返回: (触碰次数, 触碰索引列表)
        """
        touches = []
        for i in range(start_idx, min(start_idx + window, len(series))):
            line_value = slope * i + intercept
            if abs(series[i] - line_value) <= tolerance:
                touches.append(i)

        return len(touches), touches

    def _calculate_pattern_strength(self, pattern: Dict[str, Any], touch_indices_upper: List[int],
                                     touch_indices_lower: List[int]) -> float:
        """
        计算形态强度 (0-1)
        考虑因素:
        1. R²拟合度 (30%)
        2. 触碰次数和分布 (30%)
        3. 成交量特征 (20%)
        4. 形态完整性 (20%)
        """
        strength = 0.0

        # 1. R²拟合度
        upper = pattern.get('upper', (0, 0))
        lower = pattern.get('lower', (0, 0))
        if len(upper) >= 3 and len(lower) >= 3:
            r2_upper = upper[2] if len(upper) > 2 else 0
            r2_lower = lower[2] if len(lower) > 2 else 0
            r2_score = (r2_upper + r2_lower) / 2.0
            strength += r2_score * 0.3

        # 2. 触碰次数和分布
        total_touches = len(touch_indices_upper) + len(touch_indices_lower)
        touch_score = min(total_touches / 8.0, 1.0)  # 8次触碰为满分

        # 检查触碰分布均匀性
        window = pattern.get('window', 60)
        if total_touches > 0:
            all_touches = sorted(touch_indices_upper + touch_indices_lower)
            gaps = [all_touches[i+1] - all_touches[i] for i in range(len(all_touches)-1)]
            if gaps:
                avg_gap = np.mean(gaps)
                gap_std = np.std(gaps)
                distribution_score = 1.0 - min(gap_std / (avg_gap + 1e-9), 1.0)
                touch_score *= (0.7 + 0.3 * distribution_score)

        strength += touch_score * 0.3

        # 3. 成交量特征
        start_idx = len(self.volumes) - window
        if start_idx >= 0:
            vol_window = self.volumes[start_idx:]
            vol_trend = np.polyfit(range(len(vol_window)), vol_window, 1)[0]

            # 形态形成时成交量应该递减
            if vol_trend < 0:
                vol_score = 1.0
            else:
                vol_score = 0.5

            # 检查突破点附近的成交量
            recent_vol = np.mean(vol_window[-5:])
            avg_vol = np.mean(vol_window)
            if recent_vol > avg_vol * 1.2:
                vol_score *= 1.2  # 突破前成交量放大

            strength += min(vol_score, 1.0) * 0.2

        # 4. 形态完整性
        # 检查价格是否在形态内部
        if 'upper' in pattern and 'lower' in pattern:
            slope_u, intercept_u = pattern['upper'][0], pattern['upper'][1]
            slope_l, intercept_l = pattern['lower'][0], pattern['lower'][1]

            current_idx = len(self.closes) - 1
            upper_line = slope_u * current_idx + intercept_u
            lower_line = slope_l * current_idx + intercept_l

            # 当前价格应该在形态内部
            if lower_line <= self.current_price <= upper_line:
                completeness_score = 1.0
            else:
                # 计算偏离程度
                if self.current_price > upper_line:
                    deviation = (self.current_price - upper_line) / upper_line
                else:
                    deviation = (lower_line - self.current_price) / lower_line
                completeness_score = max(0, 1.0 - deviation / 0.05)  # 5%偏离为0分

            strength += completeness_score * 0.2

        return min(strength, 1.0)

    def _predict_breakout(self, pattern: Dict[str, Any]) -> Dict[str, Any]:
        """
        预测突破方向和目标价位
        """
        if 'upper' not in pattern or 'lower' not in pattern:
            return {}

        slope_u, intercept_u = pattern['upper'][0], pattern['upper'][1]
        slope_l, intercept_l = pattern['lower'][0], pattern['lower'][1]
        window = pattern.get('window', 60)

        # 计算形态末端的宽度
        end_idx = len(self.closes) - 1
        upper_end = slope_u * end_idx + intercept_u
        lower_end = slope_l * end_idx + intercept_l
        width = upper_end - lower_end

        # 计算形态起点的宽度
        start_idx = end_idx - window
        upper_start = slope_u * start_idx + intercept_u
        lower_start = slope_l * start_idx + intercept_l
        start_width = upper_start - lower_start

        # 分析价格位置
        price_position = (self.current_price - lower_end) / (width + 1e-9)

        # 分析成交量趋势
        recent_vol = np.mean(self.volumes[-5:])
        avg_vol = np.mean(self.volumes[-window:])
        vol_ratio = recent_vol / (avg_vol + 1e-9)

        # 分析动量
        recent_closes = self.closes[-10:]
        momentum = (recent_closes[-1] - recent_closes[0]) / recent_closes[0]

        # 预测突破方向
        breakout_score = 0.0

        # 1. 价格位置 (40%)
        if price_position > 0.6:
            breakout_score += 0.4
        elif price_position < 0.4:
            breakout_score -= 0.4

        # 2. 成交量 (30%)
        if vol_ratio > 1.2:
            breakout_score += 0.3 if momentum > 0 else -0.3

        # 3. 动量 (30%)
        breakout_score += momentum * 3.0  # 归一化到±0.3

        # 确定方向
        if breakout_score > 0.2:
            direction = "upward"
            target = upper_end + width  # 突破后目标 = 形态高度
        elif breakout_score < -0.2:
            direction = "downward"
            target = lower_end - width
        else:
            direction = "uncertain"
            target = self.current_price

        return {
            'direction': direction,
            'target': float(target),
            'confidence': min(abs(breakout_score), 1.0),
            'price_position': float(price_position),
            'volume_ratio': float(vol_ratio),
            'momentum': float(momentum)
        }

    def detect_channel_enhanced(self, windows: Tuple[int, ...] = (60, 80, 120, 150),
                                 r2_min: float = 0.55) -> Optional[Dict[str, Any]]:
        """
        增强版通道检测
        """
        best = None
        best_strength = 0.0

        for window in windows:
            if len(self.df) < window + 10:
                continue

            start_idx = len(self.highs) - window

            # 查找枢轴点
            high_pivots = self._find_pivot_points(self.highs[start_idx:], window=5, mode="high")
            low_pivots = self._find_pivot_points(self.lows[start_idx:], window=5, mode="low")

            if len(high_pivots) < 2 or len(low_pivots) < 2:
                continue

            # 调整索引
            high_pivots = [(i + start_idx, p) for i, p in high_pivots]
            low_pivots = [(i + start_idx, p) for i, p in low_pivots]

            # 拟合上轨和下轨
            slope_h, intercept_h, r2_h, inliers_h = self._fit_line_robust(high_pivots)
            slope_l, intercept_l, r2_l, inliers_l = self._fit_line_robust(low_pivots)

            if min(r2_h, r2_l) < r2_min:
                continue

            # 检查平行度
            slope_diff = abs(slope_h - slope_l)
            slope_avg = (abs(slope_h) + abs(slope_l)) / 2.0 + 1e-9
            parallel_score = max(0.0, 1.0 - slope_diff / (slope_avg * 0.5))

            if parallel_score < 0.6:  # 平行度要求
                continue

            # 检查通道宽度
            width_start = intercept_h - intercept_l
            width_end = (slope_h * (len(self.highs) - 1) + intercept_h) - \
                        (slope_l * (len(self.lows) - 1) + intercept_l)
            width_avg = (abs(width_start) + abs(width_end)) / 2.0

            if width_avg < self.atr * 1.5:  # 通道太窄
                continue

            # 精确触碰检测
            tolerance = self._adaptive_tolerance(window)
            touch_count_h, touch_indices_h = self._count_touches_precise(
                self.highs, slope_h, intercept_h, start_idx, window, tolerance
            )
            touch_count_l, touch_indices_l = self._count_touches_precise(
                self.lows, slope_l, intercept_l, start_idx, window, tolerance
            )

            if touch_count_h < 2 or touch_count_l < 2:
                continue

            # 构建形态
            pattern = {
                'type': 'up' if slope_h > 0 else 'down' if slope_h < 0 else 'sideways',
                'upper': (slope_h, intercept_h, r2_h),
                'lower': (slope_l, intercept_l, r2_l),
                'window': window,
                'parallel_score': float(parallel_score),
                'touch_count_upper': touch_count_h,
                'touch_count_lower': touch_count_l,
            }

            # 计算强度
            strength = self._calculate_pattern_strength(pattern, touch_indices_h, touch_indices_l)
            pattern['strength'] = strength

            # 预测突破
            pattern['breakout'] = self._predict_breakout(pattern)

            # 计算综合得分
            score = r2_h * 0.25 + r2_l * 0.25 + parallel_score * 0.25 + strength * 0.25
            pattern['score'] = float(score)

            if score > best_strength:
                best = pattern
                best_strength = score

        return best

    def detect_wedge_enhanced(self, windows: Tuple[int, ...] = (40, 60, 80, 100),
                              r2_min: float = 0.5) -> Optional[Dict[str, Any]]:
        """
        增强版楔形检测
        """
        best = None
        best_strength = 0.0

        for window in windows:
            if len(self.df) < window + 10:
                continue

            start_idx = len(self.highs) - window

            # 查找枢轴点
            high_pivots = self._find_pivot_points(self.highs[start_idx:], window=4, mode="high")
            low_pivots = self._find_pivot_points(self.lows[start_idx:], window=4, mode="low")

            if len(high_pivots) < 2 or len(low_pivots) < 2:
                continue

            # 调整索引
            high_pivots = [(i + start_idx, p) for i, p in high_pivots]
            low_pivots = [(i + start_idx, p) for i, p in low_pivots]

            # 拟合上轨和下轨
            slope_h, intercept_h, r2_h, inliers_h = self._fit_line_robust(high_pivots)
            slope_l, intercept_l, r2_l, inliers_l = self._fit_line_robust(low_pivots)

            if min(r2_h, r2_l) < r2_min:
                continue

            # 楔形特征：两条线同向收敛
            if slope_h == 0 or slope_l == 0:
                continue

            if slope_h * slope_l < 0:  # 方向相反
                continue

            # 检查收敛性
            width_start = intercept_h - intercept_l
            width_end = (slope_h * (len(self.highs) - 1) + intercept_h) - \
                        (slope_l * (len(self.lows) - 1) + intercept_l)

            if abs(width_end) >= abs(width_start) * 0.7:  # 收敛不够
                continue

            # 检查斜率差异
            if abs(slope_h - slope_l) < abs(slope_h) * 0.2:  # 太平行
                continue

            # 精确触碰检测
            tolerance = self._adaptive_tolerance(window)
            touch_count_h, touch_indices_h = self._count_touches_precise(
                self.highs, slope_h, intercept_h, start_idx, window, tolerance
            )
            touch_count_l, touch_indices_l = self._count_touches_precise(
                self.lows, slope_l, intercept_l, start_idx, window, tolerance
            )

            if touch_count_h < 2 or touch_count_l < 2:
                continue

            # 构建形态
            pattern = {
                'type': 'rising' if slope_h > 0 else 'falling',
                'upper': (slope_h, intercept_h, r2_h),
                'lower': (slope_l, intercept_l, r2_l),
                'window': window,
                'convergence': float(1.0 - abs(width_end) / abs(width_start)),
                'touch_count_upper': touch_count_h,
                'touch_count_lower': touch_count_l,
            }

            # 计算强度
            strength = self._calculate_pattern_strength(pattern, touch_indices_h, touch_indices_l)
            pattern['strength'] = strength

            # 预测突破
            pattern['breakout'] = self._predict_breakout(pattern)

            # 计算综合得分
            convergence_score = 1.0 - abs(width_end) / abs(width_start)
            score = r2_h * 0.25 + r2_l * 0.25 + convergence_score * 0.25 + strength * 0.25
            pattern['score'] = float(score)

            if score > best_strength:
                best = pattern
                best_strength = score

        return best

    def detect_triangle_enhanced(self, windows: Tuple[int, ...] = (40, 60, 80, 100),
                                 r2_min: float = 0.5) -> Optional[Dict[str, Any]]:
        """
        增强版三角形检测
        """
        best = None
        best_strength = 0.0

        for window in windows:
            if len(self.df) < window + 10:
                continue

            start_idx = len(self.highs) - window

            # 查找枢轴点
            high_pivots = self._find_pivot_points(self.highs[start_idx:], window=4, mode="high")
            low_pivots = self._find_pivot_points(self.lows[start_idx:], window=4, mode="low")

            if len(high_pivots) < 2 or len(low_pivots) < 2:
                continue

            # 调整索引
            high_pivots = [(i + start_idx, p) for i, p in high_pivots]
            low_pivots = [(i + start_idx, p) for i, p in low_pivots]

            # 拟合上轨和下轨
            slope_h, intercept_h, r2_h, inliers_h = self._fit_line_robust(high_pivots)
            slope_l, intercept_l, r2_l, inliers_l = self._fit_line_robust(low_pivots)

            if min(r2_h, r2_l) < r2_min:
                continue

            # 检查收敛性
            width_start = intercept_h - intercept_l
            width_end = (slope_h * (len(self.highs) - 1) + intercept_h) - \
                        (slope_l * (len(self.lows) - 1) + intercept_l)

            if abs(width_end) >= abs(width_start) * 0.8:  # 收敛不够
                continue

            # 判断三角形类型
            flat_threshold = self.atr * 0.2
            is_flat_top = abs(slope_h) <= flat_threshold
            is_flat_bottom = abs(slope_l) <= flat_threshold

            if is_flat_top:
                triangle_type = "descending"
            elif is_flat_bottom:
                triangle_type = "ascending"
            elif slope_h < 0 and slope_l > 0:
                triangle_type = "symmetrical"
            else:
                continue

            # 精确触碰检测
            tolerance = self._adaptive_tolerance(window)
            touch_count_h, touch_indices_h = self._count_touches_precise(
                self.highs, slope_h, intercept_h, start_idx, window, tolerance
            )
            touch_count_l, touch_indices_l = self._count_touches_precise(
                self.lows, slope_l, intercept_l, start_idx, window, tolerance
            )

            if touch_count_h < 2 or touch_count_l < 2:
                continue

            # 构建形态
            pattern = {
                'type': triangle_type,
                'upper': (slope_h, intercept_h, r2_h),
                'lower': (slope_l, intercept_l, r2_l),
                'window': window,
                'convergence': float(1.0 - abs(width_end) / abs(width_start)),
                'touch_count_upper': touch_count_h,
                'touch_count_lower': touch_count_l,
            }

            # 计算强度
            strength = self._calculate_pattern_strength(pattern, touch_indices_h, touch_indices_l)
            pattern['strength'] = strength

            # 预测突破
            pattern['breakout'] = self._predict_breakout(pattern)

            # 计算综合得分
            convergence_score = 1.0 - abs(width_end) / abs(width_start)
            score = r2_h * 0.25 + r2_l * 0.25 + convergence_score * 0.25 + strength * 0.25
            pattern['score'] = float(score)

            if score > best_strength:
                best = pattern
                best_strength = score

        return best

    def detect_flag_enhanced(self, impulse_lookback: int = 20,
                             windows: Tuple[int, ...] = (10, 15, 20, 25)) -> Optional[Dict[str, Any]]:
        """
        增强版旗形检测
        """
        best = None
        best_strength = 0.0

        for window in windows:
            if len(self.df) < window + impulse_lookback + 10:
                continue

            # 检测冲动波
            flag_start_idx = len(self.closes) - window
            impulse_start_idx = flag_start_idx - impulse_lookback

            impulse_move = self.closes[flag_start_idx] - self.closes[impulse_start_idx]
            impulse_pct = impulse_move / self.closes[impulse_start_idx]

            # 冲动波要求：至少3倍ATR或3%
            if abs(impulse_move) < max(self.atr * 3.0, self.current_price * 0.03):
                continue

            impulse_direction = 1 if impulse_move > 0 else -1

            # 旗形部分
            start_idx = flag_start_idx
            high_pivots = self._find_pivot_points(self.highs[start_idx:], window=3, mode="high")
            low_pivots = self._find_pivot_points(self.lows[start_idx:], window=3, mode="low")

            if len(high_pivots) < 2 or len(low_pivots) < 2:
                continue

            # 调整索引
            high_pivots = [(i + start_idx, p) for i, p in high_pivots]
            low_pivots = [(i + start_idx, p) for i, p in low_pivots]

            # 拟合上轨和下轨
            slope_h, intercept_h, r2_h, inliers_h = self._fit_line_robust(high_pivots)
            slope_l, intercept_l, r2_l, inliers_l = self._fit_line_robust(low_pivots)

            if min(r2_h, r2_l) < 0.45:  # 旗形R²要求较低
                continue

            # 旗形特征：回调方向与冲动波相反
            if impulse_direction > 0 and slope_h > 0:  # 上涨后不应继续上涨
                continue
            if impulse_direction < 0 and slope_l < 0:  # 下跌后不应继续下跌
                continue

            # 精确触碰检测
            tolerance = self._adaptive_tolerance(window)
            touch_count_h, touch_indices_h = self._count_touches_precise(
                self.highs, slope_h, intercept_h, start_idx, window, tolerance
            )
            touch_count_l, touch_indices_l = self._count_touches_precise(
                self.lows, slope_l, intercept_l, start_idx, window, tolerance
            )

            if touch_count_h < 2 or touch_count_l < 2:
                continue

            # 构建形态
            pattern = {
                'type': 'bullish' if impulse_direction > 0 else 'bearish',
                'upper': (slope_h, intercept_h, r2_h),
                'lower': (slope_l, intercept_l, r2_l),
                'window': window,
                'impulse_pct': float(impulse_pct),
                'impulse_direction': impulse_direction,
                'touch_count_upper': touch_count_h,
                'touch_count_lower': touch_count_l,
            }

            # 计算强度
            strength = self._calculate_pattern_strength(pattern, touch_indices_h, touch_indices_l)
            pattern['strength'] = strength

            # 预测突破（旗形通常延续冲动波方向）
            breakout_info = self._predict_breakout(pattern)
            # 修正方向为冲动波方向
            if impulse_direction > 0:
                breakout_info['direction'] = 'upward'
                breakout_info['confidence'] = min(breakout_info['confidence'] * 1.2, 1.0)
            else:
                breakout_info['direction'] = 'downward'
                breakout_info['confidence'] = min(breakout_info['confidence'] * 1.2, 1.0)

            pattern['breakout'] = breakout_info

            # 计算综合得分
            impulse_score = min(abs(impulse_pct) / 0.05, 1.0)  # 5%冲动波为满分
            score = r2_h * 0.2 + r2_l * 0.2 + impulse_score * 0.3 + strength * 0.3
            pattern['score'] = float(score)

            if score > best_strength:
                best = pattern
                best_strength = score

        return best

    def detect_all_patterns(self) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        检测所有形态
        """
        return {
            'channel': self.detect_channel_enhanced(),
            'wedge': self.detect_wedge_enhanced(),
            'triangle': self.detect_triangle_enhanced(),
            'flag': self.detect_flag_enhanced(),
        }


def detect_patterns_enhanced(df: pd.DataFrame, current_price: float,
                             atr: float = None) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    便捷函数：检测所有形态
    """
    detector = PatternDetector(df, current_price, atr)
    return detector.detect_all_patterns()
