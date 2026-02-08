"""
专业图表生成模块 v2
- Coinglass 风格清算热力图（水平条状）
- 支撑/阻力位标签不被遮挡
- 资金流入流出可视化（进度条 + 数值）
- 接入 NOFX 量化数据接口
"""

import io
import os
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
from datetime import datetime
from logger import logger
from chart_fonts import configure_matplotlib_fonts

# ==================== 配置 ====================
BINANCE_FUTURES_KLINES_URL = "https://fapi.binance.com/fapi/v1/klines"
NOFX_API_BASE = os.getenv("NOFX_API_BASE", "https://nofxai.com/data").strip().rstrip("/")
NOFX_AUTH_KEY = (os.getenv("NOFX_API_TOKEN") or os.getenv("NOFX_AUTH_KEY") or "").strip()

# Coinglass 风格配色
COLORS = {
    'bg': '#131722',
    'panel': '#1e222d',
    'grid': '#363a45',
    'text': '#d1d4dc',
    'text_dim': '#787b86',
    'up': '#26a69a',
    'down': '#ef5350',
    'yellow': '#f7931a',
    'blue': '#2962ff',
    'purple': '#7b1fa2',
}


def get_proxies():
    """获取代理配置"""
    proxies = {}
    try:
        from config import HTTP_PROXY, SOCKS5_PROXY
        if SOCKS5_PROXY:
            proxies = {'http': SOCKS5_PROXY, 'https': SOCKS5_PROXY}
        elif HTTP_PROXY:
            proxies = {'http': HTTP_PROXY, 'https': HTTP_PROXY}
    except ImportError:
        pass
    return proxies


def _build_source_headers():
    headers = {"Accept": "application/json"}
    if NOFX_AUTH_KEY:
        headers["Authorization"] = f"Bearer {NOFX_AUTH_KEY}"
    return headers


def get_futures_klines(symbol, interval='15m', limit=100):
    """获取合约K线数据"""
    symbol_clean = symbol.upper().replace('$', '').strip()
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    try:
        response = requests.get(
            BINANCE_FUTURES_KLINES_URL,
            params={'symbol': symbol_clean, 'interval': interval, 'limit': limit},
            proxies=get_proxies(),
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume', 'taker_buy_base', 'quote_volume']:
                df[col] = df[col].astype(float)
            
            df['taker_buy'] = df['taker_buy_base']
            df['taker_sell'] = df['volume'] - df['taker_buy_base']
            
            return df
    except Exception as e:
        logger.warning(f"获取K线失败: {e}")
    return None


def get_nofx_quant_data(symbol):
    """Fetch external quant data for netflow/oi/price."""
    symbol_clean = symbol.upper().replace('$', '').strip()
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    try:
        url = f"{NOFX_API_BASE}/api/coin/{symbol_clean}"
        response = requests.get(
            url,
            params={'include': 'netflow,oi,price'},
            headers=_build_source_headers(),
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 0:
                return data.get('data', {})
    except Exception:
        logger.warning("Data source request failed.")
    return None


def find_support_resistance(df, num_levels=3):
    """
    计算支撑位和阻力位
    使用多种方法：局部极值 + 成交量密集区 + 关键价格水平
    """
    current_price = df['close'].iloc[-1]
    
    # 1. 找出所有局部高低点（使用更大的窗口）
    highs = []
    lows = []
    window = 5
    
    for i in range(window, len(df) - window):
        # 局部高点
        if df['high'].iloc[i] == df['high'].iloc[i-window:i+window+1].max():
            highs.append((df['high'].iloc[i], df['volume'].iloc[i], i))
        # 局部低点
        if df['low'].iloc[i] == df['low'].iloc[i-window:i+window+1].min():
            lows.append((df['low'].iloc[i], df['volume'].iloc[i], i))
    
    # 2. 合并相近的价格水平（±0.5%）
    def merge_levels(levels, threshold=0.005):
        if not levels:
            return []
        
        levels = sorted(levels, key=lambda x: x[0])
        merged = []
        current_group = [levels[0]]
        
        for level in levels[1:]:
            if (level[0] - current_group[-1][0]) / current_group[-1][0] < threshold:
                current_group.append(level)
            else:
                # 取成交量加权平均价
                total_vol = sum(l[1] for l in current_group)
                avg_price = sum(l[0] * l[1] for l in current_group) / total_vol if total_vol > 0 else current_group[0][0]
                merged.append((avg_price, total_vol))
                current_group = [level]
        
        if current_group:
            total_vol = sum(l[1] for l in current_group)
            avg_price = sum(l[0] * l[1] for l in current_group) / total_vol if total_vol > 0 else current_group[0][0]
            merged.append((avg_price, total_vol))
        
        return merged
    
    merged_highs = merge_levels(highs)
    merged_lows = merge_levels(lows)
    
    # 3. 筛选支撑位（低于当前价格）和阻力位（高于当前价格）
    supports = [(p, v) for p, v in merged_lows if p < current_price * 0.999]
    resistances = [(p, v) for p, v in merged_highs if p > current_price * 1.001]
    
    # 4. 按距离当前价格排序（越近越重要），并考虑成交量
    supports = sorted(supports, key=lambda x: (-x[1], current_price - x[0]))[:num_levels]
    resistances = sorted(resistances, key=lambda x: (-x[1], x[0] - current_price))[:num_levels]
    
    # 5. 按价格从高到低排序
    supports = sorted([p for p, v in supports], reverse=True)
    resistances = sorted([p for p, v in resistances])
    
    return supports, resistances


def create_coinglass_heatmap(df, price_min, price_max, num_levels=60):
    """
    创建 Coinglass 风格清算热力图（水平条状）
    """
    price_levels = np.linspace(price_min, price_max, num_levels)
    heatmap = np.zeros(num_levels)
    
    current_price = df['close'].iloc[-1]
    
    # 杠杆清算距离
    leverages = [100, 75, 50, 25, 10, 5]
    liq_distances = [1/lev for lev in leverages]
    
    for i, price in enumerate(price_levels):
        distance_pct = abs(price - current_price) / current_price
        intensity = 0
        
        for liq_dist in liq_distances:
            if abs(distance_pct - liq_dist) < 0.008:
                intensity += 1.0
            elif abs(distance_pct - liq_dist) < 0.015:
                intensity += 0.5
        
        # 成交量密集区额外加权
        for _, row in df.iterrows():
            if row['low'] <= price <= row['high']:
                vol_weight = row['quote_volume'] / df['quote_volume'].max()
                intensity += vol_weight * 0.3
        
        heatmap[i] = intensity
    
    # 归一化
    if heatmap.max() > 0:
        heatmap = heatmap / heatmap.max()
    
    return heatmap, price_levels


def format_number(num, decimals=2):
    """格式化数字显示"""
    if abs(num) >= 1e9:
        return f"{num/1e9:.{decimals}f}B"
    elif abs(num) >= 1e6:
        return f"{num/1e6:.{decimals}f}M"
    elif abs(num) >= 1e3:
        return f"{num/1e3:.{decimals}f}K"
    else:
        return f"{num:.{decimals}f}"


def generate_chart_v2(symbol, interval='15m', limit=150):
    """生成专业图表 v2"""
    symbol_clean = symbol.upper().replace('$', '').strip()
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    logger.info(f"📊 生成图表 v2: {symbol_clean}")
    
    df = get_futures_klines(symbol_clean, interval, limit)
    if df is None or df.empty:
        logger.error(f"❌ 无法获取 K线数据")
        return None
    
    nofx_data = get_nofx_quant_data(symbol_clean)
    
    try:
        plt.style.use('dark_background')
        configure_matplotlib_fonts()
        
        # 创建图表 - 左侧热力图 + 中间K线 + 右侧标签 + 底部资金流
        fig = plt.figure(figsize=(18, 14), facecolor=COLORS['bg'])
        
        # 布局：热力图(5%) + K线(75%) + 标签区(10%) + 留白(10%)
        ax_heat = fig.add_axes([0.02, 0.35, 0.04, 0.55], facecolor=COLORS['bg'])
        ax_main = fig.add_axes([0.08, 0.35, 0.72, 0.55], facecolor=COLORS['bg'])
        ax_labels = fig.add_axes([0.82, 0.35, 0.16, 0.55], facecolor=COLORS['bg'])
        ax_flow = fig.add_axes([0.02, 0.04, 0.96, 0.26], facecolor=COLORS['panel'])
        
        current_price = df['close'].iloc[-1]
        price_min = df['low'].min() * 0.995
        price_max = df['high'].max() * 1.005
        
        # ========== 左侧：Coinglass 风格热力图 ==========
        heatmap, price_levels = create_coinglass_heatmap(df, price_min, price_max, num_levels=80)
        
        # 颜色映射：深紫 -> 青色 -> 黄色 -> 红色
        cmap = LinearSegmentedColormap.from_list('coinglass', [
            '#1a1a2e', '#16213e', '#0f3460', '#1a508b', 
            '#25b09b', '#97d700', '#ffd93d', '#ff6b35', '#ff0000'
        ])
        
        # 绘制水平条状热力图
        for i, (intensity, price) in enumerate(zip(heatmap, price_levels)):
            if intensity > 0.1:
                color = cmap(intensity)
                bar_height = (price_max - price_min) / len(price_levels)
                ax_heat.barh(price, intensity, height=bar_height * 0.9, 
                            color=color, alpha=0.9, left=0)
        
        ax_heat.set_ylim(price_min, price_max)
        ax_heat.set_xlim(0, 1.2)
        ax_heat.axis('off')
        
        # ========== 中间：K线图 ==========
        supports, resistances = find_support_resistance(df)
        
        # 绘制支撑/阻力区域（淡色背景）
        for sup in supports:
            ax_main.axhspan(sup * 0.998, sup * 1.002, color=COLORS['up'], alpha=0.1)
            ax_main.axhline(y=sup, color=COLORS['up'], linewidth=1, linestyle='--', alpha=0.6)
        
        for res in resistances:
            ax_main.axhspan(res * 0.998, res * 1.002, color=COLORS['down'], alpha=0.1)
            ax_main.axhline(y=res, color=COLORS['down'], linewidth=1, linestyle='--', alpha=0.6)
        
        # 绘制K线
        for i, (_, row) in enumerate(df.iterrows()):
            is_up = row['close'] >= row['open']
            color = COLORS['up'] if is_up else COLORS['down']
            
            ax_main.plot([i, i], [row['low'], row['high']], color=color, linewidth=1)
            
            body_bottom = min(row['open'], row['close'])
            body_height = abs(row['close'] - row['open'])
            if body_height < (price_max - price_min) * 0.001:
                body_height = (price_max - price_min) * 0.001
            
            rect = mpatches.Rectangle(
                (i - 0.35, body_bottom), 0.7, body_height,
                facecolor=color, edgecolor=color, alpha=0.95
            )
            ax_main.add_patch(rect)
        
        # 当前价格线
        ax_main.axhline(y=current_price, color=COLORS['yellow'], linewidth=2, alpha=0.95)
        
        ax_main.set_xlim(-1, len(df) + 1)
        ax_main.set_ylim(price_min, price_max)
        ax_main.set_ylabel('Price (USDT)', color=COLORS['text_dim'], fontsize=10)
        ax_main.tick_params(colors=COLORS['text_dim'], labelsize=9)
        ax_main.grid(True, color=COLORS['grid'], alpha=0.2, axis='y')
        for spine in ax_main.spines.values():
            spine.set_visible(False)
        plt.setp(ax_main.get_xticklabels(), visible=False)
        
        # ========== 右侧：价格标签区 ==========
        ax_labels.set_xlim(0, 1)
        ax_labels.set_ylim(price_min, price_max)
        ax_labels.axis('off')
        
        # 当前价格标签
        ax_labels.annotate(
            f'${current_price:,.2f}',
            xy=(0, current_price), xytext=(0.1, current_price),
            fontsize=11, fontweight='bold', color=COLORS['bg'],
            bbox=dict(boxstyle='round,pad=0.4', facecolor=COLORS['yellow'], edgecolor='none'),
            va='center', ha='left'
        )
        
        # 支撑位标签
        for i, sup in enumerate(supports):
            ax_labels.annotate(
                f'S{i+1} ${sup:,.0f}',
                xy=(0, sup), xytext=(0.1, sup),
                fontsize=9, fontweight='bold', color=COLORS['up'],
                bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['bg'], 
                         edgecolor=COLORS['up'], linewidth=1),
                va='center', ha='left'
            )
        
        # 阻力位标签
        for i, res in enumerate(resistances):
            ax_labels.annotate(
                f'R{i+1} ${res:,.0f}',
                xy=(0, res), xytext=(0.1, res),
                fontsize=9, fontweight='bold', color=COLORS['down'],
                bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['bg'],
                         edgecolor=COLORS['down'], linewidth=1),
                va='center', ha='left'
            )
        
        # ========== 底部：资金流向面板 ==========
        ax_flow.set_xlim(0, 1)
        ax_flow.set_ylim(0, 1)
        ax_flow.axis('off')
        
        # 分隔线
        ax_flow.axvline(x=0.5, color=COLORS['grid'], linewidth=1, alpha=0.5)
        
        periods = ['5m', '15m', '1h', '4h', '24h']
        
        # ===== 左半部分：现货资金流 =====
        ax_flow.text(0.25, 0.94, 'SPOT FUND FLOW', transform=ax_flow.transAxes,
                    fontsize=12, fontweight='bold', color=COLORS['blue'], ha='center')
        
        # 表头
        cols_spot = [0.04, 0.12, 0.20, 0.28, 0.38, 0.46]
        ax_flow.text(cols_spot[0], 0.82, 'Time', fontsize=8, color=COLORS['text_dim'], 
                    transform=ax_flow.transAxes, ha='center')
        ax_flow.text(cols_spot[1], 0.82, 'Inflow', fontsize=8, color=COLORS['up'],
                    transform=ax_flow.transAxes, ha='center')
        ax_flow.text(cols_spot[2], 0.82, 'Outflow', fontsize=8, color=COLORS['down'],
                    transform=ax_flow.transAxes, ha='center')
        ax_flow.text(cols_spot[3], 0.82, 'Net', fontsize=8, color=COLORS['yellow'],
                    transform=ax_flow.transAxes, ha='center')
        ax_flow.text(cols_spot[4], 0.82, 'Net%', fontsize=8, color=COLORS['text_dim'],
                    transform=ax_flow.transAxes, ha='center')
        
        row_heights = [0.68, 0.54, 0.40, 0.26, 0.12]
        
        # 计算现货资金流数据
        for i, period in enumerate(periods):
            y = row_heights[i]
            ax_flow.text(cols_spot[0], y, period, fontsize=9, color=COLORS['text'],
                        transform=ax_flow.transAxes, ha='center', fontweight='bold')
            
            if nofx_data and 'netflow' in nofx_data:
                netflow = nofx_data['netflow']
                
                # 现货数据：机构 + 散户
                inst_spot = netflow.get('institution', {}).get('spot', {}).get(period, 0)
                pers_spot = netflow.get('personal', {}).get('spot', {}).get(period, 0)
                
                # 正数 = 流入，负数 = 流出
                # 流入 = 所有正数之和
                inflow = (inst_spot if inst_spot > 0 else 0) + (pers_spot if pers_spot > 0 else 0)
                # 流出 = 所有负数绝对值之和
                outflow = abs(inst_spot if inst_spot < 0 else 0) + abs(pers_spot if pers_spot < 0 else 0)
                # 净流入 = 流入 - 流出 = 总和
                net = inst_spot + pers_spot
                # 净流入变化率
                total_flow = inflow + outflow
                net_pct = (net / total_flow * 100) if total_flow > 0 else 0
                
                ax_flow.text(cols_spot[1], y, format_number(inflow), fontsize=9, color=COLORS['up'],
                            transform=ax_flow.transAxes, ha='center')
                ax_flow.text(cols_spot[2], y, format_number(outflow), fontsize=9, color=COLORS['down'],
                            transform=ax_flow.transAxes, ha='center')
                
                net_color = COLORS['up'] if net >= 0 else COLORS['down']
                ax_flow.text(cols_spot[3], y, format_number(net), fontsize=9, 
                            color=net_color, transform=ax_flow.transAxes, ha='center', fontweight='bold')
                ax_flow.text(cols_spot[4], y, f'{net_pct:+.1f}%', fontsize=9,
                            color=net_color, transform=ax_flow.transAxes, ha='center')
            else:
                # 无数据
                for j in range(1, 5):
                    ax_flow.text(cols_spot[j], y, '--', fontsize=9,
                                color=COLORS['text_dim'], transform=ax_flow.transAxes, ha='center')
        
        # ===== 右半部分：合约资金流 =====
        ax_flow.text(0.75, 0.94, 'FUTURES FUND FLOW', transform=ax_flow.transAxes,
                    fontsize=12, fontweight='bold', color=COLORS['purple'], ha='center')
        
        cols_fut = [0.54, 0.62, 0.70, 0.78, 0.88, 0.96]
        ax_flow.text(cols_fut[0], 0.82, 'Time', fontsize=8, color=COLORS['text_dim'],
                    transform=ax_flow.transAxes, ha='center')
        ax_flow.text(cols_fut[1], 0.82, 'Inflow', fontsize=8, color=COLORS['up'],
                    transform=ax_flow.transAxes, ha='center')
        ax_flow.text(cols_fut[2], 0.82, 'Outflow', fontsize=8, color=COLORS['down'],
                    transform=ax_flow.transAxes, ha='center')
        ax_flow.text(cols_fut[3], 0.82, 'Net', fontsize=8, color=COLORS['yellow'],
                    transform=ax_flow.transAxes, ha='center')
        ax_flow.text(cols_fut[4], 0.82, 'Net%', fontsize=8, color=COLORS['text_dim'],
                    transform=ax_flow.transAxes, ha='center')
        
        # 计算合约资金流数据
        for i, period in enumerate(periods):
            y = row_heights[i]
            ax_flow.text(cols_fut[0], y, period, fontsize=9, color=COLORS['text'],
                        transform=ax_flow.transAxes, ha='center', fontweight='bold')
            
            if nofx_data and 'netflow' in nofx_data:
                netflow = nofx_data['netflow']
                
                # 合约数据：机构 + 散户
                inst_fut = netflow.get('institution', {}).get('future', {}).get(period, 0)
                pers_fut = netflow.get('personal', {}).get('future', {}).get(period, 0)
                
                # 正数 = 流入，负数 = 流出
                inflow = (inst_fut if inst_fut > 0 else 0) + (pers_fut if pers_fut > 0 else 0)
                outflow = abs(inst_fut if inst_fut < 0 else 0) + abs(pers_fut if pers_fut < 0 else 0)
                net = inst_fut + pers_fut
                total_flow = inflow + outflow
                net_pct = (net / total_flow * 100) if total_flow > 0 else 0
                
                ax_flow.text(cols_fut[1], y, format_number(inflow), fontsize=9, color=COLORS['up'],
                            transform=ax_flow.transAxes, ha='center')
                ax_flow.text(cols_fut[2], y, format_number(outflow), fontsize=9, color=COLORS['down'],
                            transform=ax_flow.transAxes, ha='center')
                
                net_color = COLORS['up'] if net >= 0 else COLORS['down']
                ax_flow.text(cols_fut[3], y, format_number(net), fontsize=9,
                            color=net_color, transform=ax_flow.transAxes, ha='center', fontweight='bold')
                ax_flow.text(cols_fut[4], y, f'{net_pct:+.1f}%', fontsize=9,
                            color=net_color, transform=ax_flow.transAxes, ha='center')
            else:
                # 使用 Binance taker buy/sell 数据估算
                # 根据时间周期计算对应的K线数量
                period_bars = {'5m': 1, '15m': 1, '1h': 4, '4h': 16, '24h': 96}
                bars = min(period_bars.get(period, 1), len(df))
                
                recent_df = df.tail(bars)
                inflow = recent_df['taker_buy'].sum()
                outflow = recent_df['taker_sell'].sum()
                net = inflow - outflow
                total_flow = inflow + outflow
                net_pct = (net / total_flow * 100) if total_flow > 0 else 0
                
                ax_flow.text(cols_fut[1], y, format_number(inflow), fontsize=9, color=COLORS['up'],
                            transform=ax_flow.transAxes, ha='center')
                ax_flow.text(cols_fut[2], y, format_number(outflow), fontsize=9, color=COLORS['down'],
                            transform=ax_flow.transAxes, ha='center')
                
                net_color = COLORS['up'] if net >= 0 else COLORS['down']
                ax_flow.text(cols_fut[3], y, format_number(net), fontsize=9,
                            color=net_color, transform=ax_flow.transAxes, ha='center', fontweight='bold')
                ax_flow.text(cols_fut[4], y, f'{net_pct:+.1f}%', fontsize=9,
                            color=net_color, transform=ax_flow.transAxes, ha='center')
        
        # ========== 标题 ==========
        interval_map = {'15m': '15min', '1h': '1H', '4h': '4H', '1d': '1D'}
        price_change = ((current_price - df['open'].iloc[0]) / df['open'].iloc[0]) * 100
        change_sign = '+' if price_change >= 0 else ''
        change_color = COLORS['up'] if price_change >= 0 else COLORS['down']
        
        fig.text(0.02, 0.96, f"{symbol_clean}  ·  {interval_map.get(interval, interval)}",
                fontsize=16, fontweight='bold', color=COLORS['text'])
        fig.text(0.98, 0.96, f"${current_price:,.2f}  ({change_sign}{price_change:.2f}%)",
                fontsize=14, fontweight='bold', color=change_color, ha='right')
        
        # 图例
        fig.text(0.02, 0.925, '━ Support', fontsize=9, color=COLORS['up'])
        fig.text(0.10, 0.925, '━ Resistance', fontsize=9, color=COLORS['down'])
        fig.text(0.20, 0.925, '━ Current', fontsize=9, color=COLORS['yellow'])
        fig.text(0.30, 0.925, '█ Liquidation Density', fontsize=9, color='#25b09b')
        
        # 热力图图例
        gradient = np.linspace(0, 1, 100).reshape(1, -1)
        ax_legend = fig.add_axes([0.50, 0.92, 0.15, 0.015])
        ax_legend.imshow(gradient, aspect='auto', cmap=cmap)
        ax_legend.set_xticks([0, 99])
        ax_legend.set_xticklabels(['Low', 'High'], fontsize=7, color=COLORS['text_dim'])
        ax_legend.set_yticks([])
        for spine in ax_legend.spines.values():
            spine.set_visible(False)
        
        # 水印
        fig.text(0.5, 0.55, 'Signal', fontsize=30, color=COLORS['yellow'],
                ha='center', va='center', alpha=0.015, fontweight='bold')
        
        # 保存
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=140, bbox_inches='tight',
                   facecolor=COLORS['bg'], edgecolor='none')
        buf.seek(0)
        image_data = buf.read()
        buf.close()
        plt.close(fig)
        
        size_kb = len(image_data) / 1024
        logger.info(f"✅ 图表 v2 生成成功: {symbol_clean} ({size_kb:.1f} KB)")
        
        return image_data
        
    except Exception as e:
        logger.exception(f"❌ 图表生成失败: {e}")
        return None


def send_chart_v2_to_telegram(symbol, interval='15m', caption=None):
    """发送图表到 Telegram"""
    from telegram import send_telegram_photo
    
    chart_data = generate_chart_v2(symbol, interval=interval)
    if not chart_data:
        return False
    
    if caption is None:
        symbol_clean = symbol.upper().replace('$', '').strip()
        if not symbol_clean.endswith('USDT'):
            symbol_clean = f"{symbol_clean}USDT"
        caption = f"<b>{symbol_clean}</b> | 15min | Liquidation + Fund Flow"
    
    return send_telegram_photo(chart_data, caption=caption)


def test_chart_v2(symbol='BTC'):
    """测试图表生成"""
    import os
    
    logger.info(f"🧪 测试图表 v2: {symbol}")
    
    image_data = generate_chart_v2(symbol, interval='15m', limit=150)
    
    if image_data:
        os.makedirs('output', exist_ok=True)
        output_path = f'output/chart_v2_{symbol}.png'
        with open(output_path, 'wb') as f:
            f.write(image_data)
        logger.info(f"✅ 图片已保存: {output_path}")
        return True
    return False


if __name__ == '__main__':
    test_chart_v2('BTC')
    test_chart_v2('ETH')
