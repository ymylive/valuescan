"""
专业图表生成模块 v4
- Coinank API 获取清算数据、持仓数据、资金流数据
- 根据清算热力图高峰确定支撑/阻力位
- 统一字体风格
- 专业数据源整合
"""

import io
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
from datetime import datetime
import time
from logger import logger
from chart_fonts import configure_matplotlib_fonts

# ==================== 数据源配置 ====================

# Coinank API (专业数据源)
COINANK_API_URL = "https://open-api-cn.coinank.com"
COINANK_API_KEY = ""  # 需要申请

# Binance API
BINANCE_FUTURES_KLINES_URL = "https://fapi.binance.com/fapi/v1/klines"
BINANCE_FUTURES_TICKER_URL = "https://fapi.binance.com/fapi/v1/ticker/24hr"
BINANCE_TAKER_VOLUME_URL = "https://fapi.binance.com/futures/data/takerlongshortRatio"

# 配色方案 (Coinglass 风格)
COLORS = {
    'bg': '#0b0e11',
    'panel': '#1a1d21',
    'grid': '#2a2d35',
    'text': '#eaecef',
    'text_dim': '#848e9c',
    'up': '#0ecb81',
    'down': '#f6465d',
    'yellow': '#f0b90b',
    'blue': '#1e88e5',
    'purple': '#8b5cf6',
    'cyan': '#00bcd4',
}

# 统一字体配置
FONT_CONFIG = {
    'title': {'size': 14, 'weight': 'bold'},
    'subtitle': {'size': 11, 'weight': 'bold'},
    'label': {'size': 9, 'weight': 'normal'},
    'value': {'size': 10, 'weight': 'bold'},
    'small': {'size': 8, 'weight': 'normal'},
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


# ==================== 数据获取函数 ====================

def get_binance_klines(symbol, interval='15m', limit=200):
    """获取 Binance 合约 K线数据"""
    symbol_clean = symbol.upper().replace('$', '').strip()
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    try:
        response = requests.get(
            BINANCE_FUTURES_KLINES_URL,
            params={'symbol': symbol_clean, 'interval': interval, 'limit': limit},
            proxies=get_proxies(),
            timeout=15
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


def get_binance_taker_ratio(symbol, interval='15m', limit=30):
    """获取 Binance Taker 买卖比数据"""
    symbol_clean = symbol.upper().replace('$', '').strip()
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    try:
        response = requests.get(
            BINANCE_TAKER_VOLUME_URL,
            params={'symbol': symbol_clean, 'period': interval, 'limit': limit},
            proxies=get_proxies(),
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.warning(f"获取 Taker 比率失败: {e}")
    return None


def get_coinank_liquidation_stats(base_coin):
    """获取 Coinank 清算统计数据"""
    if not COINANK_API_KEY:
        return None
    
    try:
        url = f"{COINANK_API_URL}/api/liquidation/allExchange/intervals"
        response = requests.get(
            url,
            params={'baseCoin': base_coin.upper()},
            headers={'apikey': COINANK_API_KEY},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('data', {})
    except Exception as e:
        logger.warning(f"Coinank 清算数据失败: {e}")
    return None


def get_coinank_instrument_info(symbol):
    """获取 Coinank 交易对详细信息"""
    if not COINANK_API_KEY:
        return None
    
    try:
        url = f"{COINANK_API_URL}/api/instruments/getLastPrice"
        response = requests.get(
            url,
            params={'symbol': symbol, 'exchange': 'Binance', 'productType': 'SWAP'},
            headers={'apikey': COINANK_API_KEY},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('data', {})
    except Exception as e:
        logger.warning(f"Coinank 交易对信息失败: {e}")
    return None


# ==================== 清算热力图算法 ====================

def calculate_liquidation_levels(df, current_price):
    """
    计算清算价格分布
    基于不同杠杆倍数的清算价格
    返回：(heatmap, price_levels, support_levels, resistance_levels)
    """
    price_range = df['high'].max() - df['low'].min()
    price_min = current_price - price_range * 0.6
    price_max = current_price + price_range * 0.6
    
    num_levels = 120
    price_levels = np.linspace(price_min, price_max, num_levels)
    heatmap = np.zeros(num_levels)
    
    # 杠杆配置：(杠杆倍数, 清算距离百分比, 强度权重)
    leverage_configs = [
        (125, 0.008, 1.0),
        (100, 0.010, 0.95),
        (75, 0.013, 0.90),
        (50, 0.020, 0.85),
        (25, 0.040, 0.70),
        (20, 0.050, 0.60),
        (10, 0.100, 0.40),
        (5, 0.200, 0.20),
        (3, 0.333, 0.10),
    ]
    
    # 计算每个价格水平的清算密度
    for i, price in enumerate(price_levels):
        distance_pct = abs(price - current_price) / current_price
        intensity = 0
        
        for leverage, liq_dist, weight in leverage_configs:
            # 高斯分布
            sigma = 0.004
            gauss = np.exp(-((distance_pct - liq_dist) ** 2) / (2 * sigma ** 2))
            intensity += weight * gauss
        
        # 成交量加权
        for _, row in df.iterrows():
            if row['low'] <= price <= row['high']:
                vol_weight = row['quote_volume'] / df['quote_volume'].max()
                intensity += vol_weight * 0.15
        
        heatmap[i] = intensity
    
    # 归一化
    if heatmap.max() > 0:
        heatmap = heatmap / heatmap.max()
    
    # 根据热力图高峰确定支撑位和阻力位
    supports = []
    resistances = []
    
    # 找到热力图的局部最大值
    for i in range(5, len(heatmap) - 5):
        if heatmap[i] > 0.4:  # 阈值
            is_peak = True
            for j in range(-3, 4):
                if j != 0 and heatmap[i] < heatmap[i + j]:
                    is_peak = False
                    break
            
            if is_peak:
                price = price_levels[i]
                if price < current_price * 0.998:
                    supports.append((price, heatmap[i]))
                elif price > current_price * 1.002:
                    resistances.append((price, heatmap[i]))
    
    # 按强度排序，取前3个
    supports = sorted(supports, key=lambda x: -x[1])[:3]
    resistances = sorted(resistances, key=lambda x: -x[1])[:3]
    
    # 按价格排序
    supports = sorted([p for p, _ in supports], reverse=True)
    resistances = sorted([p for p, _ in resistances])
    
    return heatmap, price_levels, supports, resistances


def format_number(num, decimals=2):
    """格式化数字（带单位）"""
    if abs(num) >= 1e9:
        return f"{num/1e9:.{decimals}f}B"
    elif abs(num) >= 1e6:
        return f"{num/1e6:.{decimals}f}M"
    elif abs(num) >= 1e3:
        return f"{num/1e3:.{decimals}f}K"
    else:
        return f"{num:.{decimals}f}"


# ==================== 图表生成 ====================

def generate_pro_chart_v4(symbol, interval='15m', limit=200):
    """生成专业图表 v4"""
    symbol_clean = symbol.upper().replace('$', '').strip()
    base_coin = symbol_clean.replace('USDT', '')
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    logger.info(f"📊 生成专业图表 v4: {symbol_clean}")
    
    # 获取数据
    df = get_binance_klines(symbol_clean, interval, limit)
    if df is None or df.empty:
        logger.error("❌ 无法获取 K线数据")
        return None
    
    taker_data = get_binance_taker_ratio(symbol_clean, interval)
    coinank_liq = get_coinank_liquidation_stats(base_coin)
    coinank_info = get_coinank_instrument_info(symbol_clean)
    
    try:
        # 配置字体
        plt.style.use('dark_background')
        configure_matplotlib_fonts()
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['font.size'] = 9
        
        fig = plt.figure(figsize=(20, 14), facecolor=COLORS['bg'])
        
        # 布局
        ax_heat = fig.add_axes([0.02, 0.30, 0.03, 0.60], facecolor=COLORS['bg'])
        ax_main = fig.add_axes([0.06, 0.30, 0.68, 0.60], facecolor=COLORS['bg'])
        ax_info = fig.add_axes([0.76, 0.30, 0.22, 0.60], facecolor=COLORS['panel'])
        ax_flow = fig.add_axes([0.02, 0.02, 0.96, 0.24], facecolor=COLORS['panel'])
        
        current_price = df['close'].iloc[-1]
        price_min = df['low'].min() * 0.998
        price_max = df['high'].max() * 1.002
        
        # ========== 计算清算热力图和支撑/阻力位 ==========
        heatmap, heat_levels, supports, resistances = calculate_liquidation_levels(df, current_price)
        
        # ========== 左侧：清算热力图 ==========
        cmap = LinearSegmentedColormap.from_list('liq', [
            '#0b0e11', '#1a1a4e', '#2d1b69', '#4a1c7a',
            '#6b1d8a', '#8b2e9a', '#ab3faa', '#d050c0',
            '#f070d0', '#ff90e0', '#ffb0ff'
        ])
        
        for i, (intensity, price) in enumerate(zip(heatmap, heat_levels)):
            if intensity > 0.08 and price_min <= price <= price_max:
                bar_height = (price_max - price_min) / len(heat_levels) * 0.95
                ax_heat.barh(price, intensity, height=bar_height, color=cmap(intensity), alpha=0.9)
        
        ax_heat.set_ylim(price_min, price_max)
        ax_heat.set_xlim(0, 1.2)
        ax_heat.axis('off')
        
        # ========== 中间：K线图 + 支撑/阻力位 ==========
        
        # 绘制支撑位（从热力图高峰得出）
        for i, sup in enumerate(supports):
            if price_min <= sup <= price_max:
                ax_main.axhline(y=sup, color=COLORS['up'], linewidth=1.5, linestyle='--', alpha=0.7)
                ax_main.fill_between([0, len(df)], sup * 0.999, sup * 1.001, 
                                    color=COLORS['up'], alpha=0.1)
        
        # 绘制阻力位
        for i, res in enumerate(resistances):
            if price_min <= res <= price_max:
                ax_main.axhline(y=res, color=COLORS['down'], linewidth=1.5, linestyle='--', alpha=0.7)
                ax_main.fill_between([0, len(df)], res * 0.999, res * 1.001,
                                    color=COLORS['down'], alpha=0.1)
        
        # 绘制K线
        for i, (_, row) in enumerate(df.iterrows()):
            is_up = row['close'] >= row['open']
            color = COLORS['up'] if is_up else COLORS['down']
            
            ax_main.plot([i, i], [row['low'], row['high']], color=color, linewidth=0.8)
            
            body_bottom = min(row['open'], row['close'])
            body_height = abs(row['close'] - row['open'])
            if body_height < (price_max - price_min) * 0.0003:
                body_height = (price_max - price_min) * 0.0003
            
            rect = mpatches.Rectangle(
                (i - 0.3, body_bottom), 0.6, body_height,
                facecolor=color, edgecolor=color, alpha=0.95
            )
            ax_main.add_patch(rect)
        
        # 当前价格线
        ax_main.axhline(y=current_price, color=COLORS['yellow'], linewidth=2, alpha=0.95)
        
        ax_main.set_xlim(-1, len(df) + 1)
        ax_main.set_ylim(price_min, price_max)
        ax_main.set_ylabel('价格 (USDT)', color=COLORS['text_dim'], fontsize=FONT_CONFIG['label']['size'])
        ax_main.tick_params(colors=COLORS['text_dim'], labelsize=8)
        ax_main.grid(True, color=COLORS['grid'], alpha=0.3, axis='y')
        for spine in ax_main.spines.values():
            spine.set_visible(False)
        plt.setp(ax_main.get_xticklabels(), visible=False)
        
        # ========== 右侧：数据面板 ==========
        ax_info.set_xlim(0, 1)
        ax_info.set_ylim(0, 1)
        ax_info.axis('off')
        
        y_pos = 0.95
        line_height = 0.055
        
        # 当前价格
        ax_info.text(0.5, y_pos, f'${current_price:,.2f}', 
                    fontsize=16, fontweight='bold', color=COLORS['yellow'],
                    transform=ax_info.transAxes, ha='center')
        y_pos -= 0.08
        
        price_change = ((current_price - df['open'].iloc[0]) / df['open'].iloc[0]) * 100
        change_color = COLORS['up'] if price_change >= 0 else COLORS['down']
        ax_info.text(0.5, y_pos, f'{price_change:+.2f}%',
                    fontsize=12, fontweight='bold', color=change_color,
                    transform=ax_info.transAxes, ha='center')
        y_pos -= 0.07
        
        ax_info.axhline(y=y_pos, xmin=0.1, xmax=0.9, color=COLORS['grid'], linewidth=0.5)
        y_pos -= 0.04
        
        # 支撑位
        ax_info.text(0.5, y_pos, '支撑位 (清算密集区)', fontsize=FONT_CONFIG['small']['size'],
                    color=COLORS['text_dim'], transform=ax_info.transAxes, ha='center')
        y_pos -= line_height
        
        for i, sup in enumerate(supports[:3]):
            ax_info.text(0.1, y_pos, f'S{i+1}:', fontsize=FONT_CONFIG['label']['size'],
                        color=COLORS['text_dim'], transform=ax_info.transAxes)
            ax_info.text(0.9, y_pos, f'${sup:,.0f}', fontsize=FONT_CONFIG['value']['size'],
                        color=COLORS['up'], transform=ax_info.transAxes, ha='right', fontweight='bold')
            y_pos -= line_height
        
        if not supports:
            ax_info.text(0.5, y_pos, '无明显支撑位', fontsize=FONT_CONFIG['small']['size'],
                        color=COLORS['text_dim'], transform=ax_info.transAxes, ha='center')
            y_pos -= line_height
        
        y_pos -= 0.02
        
        # 阻力位
        ax_info.text(0.5, y_pos, '阻力位 (清算密集区)', fontsize=FONT_CONFIG['small']['size'],
                    color=COLORS['text_dim'], transform=ax_info.transAxes, ha='center')
        y_pos -= line_height
        
        for i, res in enumerate(resistances[:3]):
            ax_info.text(0.1, y_pos, f'R{i+1}:', fontsize=FONT_CONFIG['label']['size'],
                        color=COLORS['text_dim'], transform=ax_info.transAxes)
            ax_info.text(0.9, y_pos, f'${res:,.0f}', fontsize=FONT_CONFIG['value']['size'],
                        color=COLORS['down'], transform=ax_info.transAxes, ha='right', fontweight='bold')
            y_pos -= line_height
        
        if not resistances:
            ax_info.text(0.5, y_pos, '无明显阻力位', fontsize=FONT_CONFIG['small']['size'],
                        color=COLORS['text_dim'], transform=ax_info.transAxes, ha='center')
            y_pos -= line_height
        
        y_pos -= 0.03
        ax_info.axhline(y=y_pos, xmin=0.1, xmax=0.9, color=COLORS['grid'], linewidth=0.5)
        y_pos -= 0.04
        
        # 清算数据
        ax_info.text(0.5, y_pos, '清算数据', fontsize=FONT_CONFIG['subtitle']['size'],
                    color=COLORS['text'], transform=ax_info.transAxes, ha='center', fontweight='bold')
        y_pos -= line_height
        
        if coinank_liq:
            liq_24h = coinank_liq.get('24h', {})
            liq_1h = coinank_liq.get('1h', {})
            
            ax_info.text(0.1, y_pos, '24H 总清算:', fontsize=FONT_CONFIG['label']['size'],
                        color=COLORS['text_dim'], transform=ax_info.transAxes)
            ax_info.text(0.9, y_pos, format_number(liq_24h.get('totalTurnover', 0)),
                        fontsize=FONT_CONFIG['value']['size'], color=COLORS['yellow'],
                        transform=ax_info.transAxes, ha='right', fontweight='bold')
            y_pos -= line_height
            
            ax_info.text(0.1, y_pos, '24H 多头:', fontsize=FONT_CONFIG['label']['size'],
                        color=COLORS['text_dim'], transform=ax_info.transAxes)
            ax_info.text(0.9, y_pos, format_number(liq_24h.get('longTurnover', 0)),
                        fontsize=FONT_CONFIG['value']['size'], color=COLORS['up'],
                        transform=ax_info.transAxes, ha='right')
            y_pos -= line_height
            
            ax_info.text(0.1, y_pos, '24H 空头:', fontsize=FONT_CONFIG['label']['size'],
                        color=COLORS['text_dim'], transform=ax_info.transAxes)
            ax_info.text(0.9, y_pos, format_number(liq_24h.get('shortTurnover', 0)),
                        fontsize=FONT_CONFIG['value']['size'], color=COLORS['down'],
                        transform=ax_info.transAxes, ha='right')
        elif coinank_info:
            ax_info.text(0.1, y_pos, '24H 多头:', fontsize=FONT_CONFIG['label']['size'],
                        color=COLORS['text_dim'], transform=ax_info.transAxes)
            ax_info.text(0.9, y_pos, format_number(coinank_info.get('liqLong24h', 0)),
                        fontsize=FONT_CONFIG['value']['size'], color=COLORS['up'],
                        transform=ax_info.transAxes, ha='right')
            y_pos -= line_height
            
            ax_info.text(0.1, y_pos, '24H 空头:', fontsize=FONT_CONFIG['label']['size'],
                        color=COLORS['text_dim'], transform=ax_info.transAxes)
            ax_info.text(0.9, y_pos, format_number(coinank_info.get('liqShort24h', 0)),
                        fontsize=FONT_CONFIG['value']['size'], color=COLORS['down'],
                        transform=ax_info.transAxes, ha='right')
        else:
            # 使用 Binance 买卖数据
            total_buy = df['taker_buy'].sum()
            total_sell = df['taker_sell'].sum()
            buy_ratio = total_buy / (total_buy + total_sell) * 100 if (total_buy + total_sell) > 0 else 50
            
            ax_info.text(0.1, y_pos, '主动买入:', fontsize=FONT_CONFIG['label']['size'],
                        color=COLORS['text_dim'], transform=ax_info.transAxes)
            ax_info.text(0.9, y_pos, format_number(total_buy),
                        fontsize=FONT_CONFIG['value']['size'], color=COLORS['up'],
                        transform=ax_info.transAxes, ha='right')
            y_pos -= line_height
            
            ax_info.text(0.1, y_pos, '主动卖出:', fontsize=FONT_CONFIG['label']['size'],
                        color=COLORS['text_dim'], transform=ax_info.transAxes)
            ax_info.text(0.9, y_pos, format_number(total_sell),
                        fontsize=FONT_CONFIG['value']['size'], color=COLORS['down'],
                        transform=ax_info.transAxes, ha='right')
            y_pos -= line_height
            
            ax_info.text(0.1, y_pos, '买卖比:', fontsize=FONT_CONFIG['label']['size'],
                        color=COLORS['text_dim'], transform=ax_info.transAxes)
            ratio_color = COLORS['up'] if buy_ratio > 50 else COLORS['down']
            ax_info.text(0.9, y_pos, f'{buy_ratio:.1f}% / {100-buy_ratio:.1f}%',
                        fontsize=FONT_CONFIG['value']['size'], color=ratio_color,
                        transform=ax_info.transAxes, ha='right', fontweight='bold')
        
        # ========== 底部：资金流向表格 ==========
        ax_flow.set_xlim(0, 1)
        ax_flow.set_ylim(0, 1)
        ax_flow.axis('off')
        
        ax_flow.axvline(x=0.5, color=COLORS['grid'], linewidth=1, alpha=0.5)
        
        periods = ['5m', '15m', '1h', '4h', '24h']
        row_y = [0.78, 0.62, 0.46, 0.30, 0.14]
        
        # ===== 左侧：买卖力量分析 =====
        ax_flow.text(0.25, 0.92, '买卖力量分析 (Binance Taker)', 
                    fontsize=FONT_CONFIG['subtitle']['size'], fontweight='bold',
                    color=COLORS['blue'], transform=ax_flow.transAxes, ha='center')
        
        cols_l = [0.04, 0.12, 0.20, 0.28, 0.38, 0.46]
        ax_flow.text(cols_l[0], 0.86, '周期', fontsize=FONT_CONFIG['small']['size'],
                    color=COLORS['text_dim'], transform=ax_flow.transAxes, ha='center')
        ax_flow.text(cols_l[1], 0.86, '买入量', fontsize=FONT_CONFIG['small']['size'],
                    color=COLORS['up'], transform=ax_flow.transAxes, ha='center')
        ax_flow.text(cols_l[2], 0.86, '卖出量', fontsize=FONT_CONFIG['small']['size'],
                    color=COLORS['down'], transform=ax_flow.transAxes, ha='center')
        ax_flow.text(cols_l[3], 0.86, '净买入', fontsize=FONT_CONFIG['small']['size'],
                    color=COLORS['yellow'], transform=ax_flow.transAxes, ha='center')
        ax_flow.text(cols_l[4], 0.86, '买入占比', fontsize=FONT_CONFIG['small']['size'],
                    color=COLORS['text_dim'], transform=ax_flow.transAxes, ha='center')
        
        # 计算各周期的买卖数据
        period_bars = {'5m': 1, '15m': 1, '1h': 4, '4h': 16, '24h': 96}
        
        for i, period in enumerate(periods):
            y = row_y[i]
            bars = min(period_bars.get(period, 1), len(df))
            recent = df.tail(bars)
            
            buy_vol = recent['taker_buy'].sum()
            sell_vol = recent['taker_sell'].sum()
            net = buy_vol - sell_vol
            total = buy_vol + sell_vol
            buy_pct = (buy_vol / total * 100) if total > 0 else 50
            
            ax_flow.text(cols_l[0], y, period, fontsize=FONT_CONFIG['label']['size'],
                        color=COLORS['text'], transform=ax_flow.transAxes, ha='center', fontweight='bold')
            ax_flow.text(cols_l[1], y, format_number(buy_vol), fontsize=FONT_CONFIG['label']['size'],
                        color=COLORS['up'], transform=ax_flow.transAxes, ha='center')
            ax_flow.text(cols_l[2], y, format_number(sell_vol), fontsize=FONT_CONFIG['label']['size'],
                        color=COLORS['down'], transform=ax_flow.transAxes, ha='center')
            
            net_color = COLORS['up'] if net >= 0 else COLORS['down']
            ax_flow.text(cols_l[3], y, format_number(net), fontsize=FONT_CONFIG['label']['size'],
                        color=net_color, transform=ax_flow.transAxes, ha='center', fontweight='bold')
            
            pct_color = COLORS['up'] if buy_pct > 50 else COLORS['down']
            ax_flow.text(cols_l[4], y, f'{buy_pct:.1f}%', fontsize=FONT_CONFIG['label']['size'],
                        color=pct_color, transform=ax_flow.transAxes, ha='center')
            
            # 进度条
            bar_width = 0.04
            bar_left = cols_l[5]
            ax_flow.barh(y, buy_pct / 100 * bar_width, height=0.06, left=bar_left,
                        color=COLORS['up'], alpha=0.8, transform=ax_flow.transAxes)
            ax_flow.barh(y, (1 - buy_pct / 100) * bar_width, height=0.06,
                        left=bar_left + buy_pct / 100 * bar_width,
                        color=COLORS['down'], alpha=0.8, transform=ax_flow.transAxes)
        
        # ===== 右侧：持仓数据 =====
        ax_flow.text(0.75, 0.92, '合约数据 (Binance)', 
                    fontsize=FONT_CONFIG['subtitle']['size'], fontweight='bold',
                    color=COLORS['purple'], transform=ax_flow.transAxes, ha='center')
        
        cols_r = [0.54, 0.64, 0.74, 0.84, 0.94]
        ax_flow.text(cols_r[0], 0.86, '周期', fontsize=FONT_CONFIG['small']['size'],
                    color=COLORS['text_dim'], transform=ax_flow.transAxes, ha='center')
        ax_flow.text(cols_r[1], 0.86, '成交额', fontsize=FONT_CONFIG['small']['size'],
                    color=COLORS['text'], transform=ax_flow.transAxes, ha='center')
        ax_flow.text(cols_r[2], 0.86, '成交笔数', fontsize=FONT_CONFIG['small']['size'],
                    color=COLORS['text'], transform=ax_flow.transAxes, ha='center')
        ax_flow.text(cols_r[3], 0.86, '均价', fontsize=FONT_CONFIG['small']['size'],
                    color=COLORS['text'], transform=ax_flow.transAxes, ha='center')
        ax_flow.text(cols_r[4], 0.86, '波动', fontsize=FONT_CONFIG['small']['size'],
                    color=COLORS['text_dim'], transform=ax_flow.transAxes, ha='center')
        
        for i, period in enumerate(periods):
            y = row_y[i]
            bars = min(period_bars.get(period, 1), len(df))
            recent = df.tail(bars)
            
            quote_vol = recent['quote_volume'].sum()
            trades = recent['trades'].sum()
            avg_price = recent['close'].mean()
            volatility = (recent['high'].max() - recent['low'].min()) / avg_price * 100
            
            ax_flow.text(cols_r[0], y, period, fontsize=FONT_CONFIG['label']['size'],
                        color=COLORS['text'], transform=ax_flow.transAxes, ha='center', fontweight='bold')
            ax_flow.text(cols_r[1], y, format_number(quote_vol), fontsize=FONT_CONFIG['label']['size'],
                        color=COLORS['cyan'], transform=ax_flow.transAxes, ha='center')
            ax_flow.text(cols_r[2], y, format_number(trades), fontsize=FONT_CONFIG['label']['size'],
                        color=COLORS['text'], transform=ax_flow.transAxes, ha='center')
            ax_flow.text(cols_r[3], y, f'${avg_price:,.0f}', fontsize=FONT_CONFIG['label']['size'],
                        color=COLORS['text'], transform=ax_flow.transAxes, ha='center')
            
            vol_color = COLORS['yellow'] if volatility > 1 else COLORS['text_dim']
            ax_flow.text(cols_r[4], y, f'{volatility:.2f}%', fontsize=FONT_CONFIG['label']['size'],
                        color=vol_color, transform=ax_flow.transAxes, ha='center')
        
        # ========== 标题 ==========
        interval_map = {'5m': '5分钟', '15m': '15分钟', '1h': '1小时', '4h': '4小时', '1d': '日线'}
        
        fig.text(0.02, 0.96, f"{symbol_clean}  ·  {interval_map.get(interval, interval)}",
                fontsize=FONT_CONFIG['title']['size'], fontweight='bold', color=COLORS['text'])
        
        # 热力图图例
        gradient = np.linspace(0, 1, 100).reshape(1, -1)
        ax_legend = fig.add_axes([0.30, 0.935, 0.10, 0.012])
        ax_legend.imshow(gradient, aspect='auto', cmap=cmap)
        ax_legend.set_xticks([0, 99])
        ax_legend.set_xticklabels(['低', '高'], fontsize=7, color=COLORS['text_dim'])
        ax_legend.set_yticks([])
        ax_legend.set_title('清算密度', fontsize=FONT_CONFIG['small']['size'], 
                           color=COLORS['text_dim'], pad=2)
        for spine in ax_legend.spines.values():
            spine.set_visible(False)
        
        # 数据源标注
        fig.text(0.98, 0.96, 'Binance Futures', fontsize=FONT_CONFIG['small']['size'],
                color=COLORS['text_dim'], ha='right')
        
        # 水印
        fig.text(0.5, 0.55, 'NOFX', fontsize=28, color=COLORS['yellow'],
                ha='center', va='center', alpha=0.015, fontweight='bold')
        
        # 保存
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=130, bbox_inches='tight',
                   facecolor=COLORS['bg'], edgecolor='none')
        buf.seek(0)
        image_data = buf.read()
        buf.close()
        plt.close(fig)
        
        size_kb = len(image_data) / 1024
        logger.info(f"✅ 专业图表 v4 生成成功: {symbol_clean} ({size_kb:.1f} KB)")
        
        return image_data
        
    except Exception as e:
        logger.exception(f"❌ 图表生成失败: {e}")
        return None


def test_chart_v4(symbol='BTC'):
    """测试图表"""
    import os
    
    logger.info(f"🧪 测试专业图表 v4: {symbol}")
    
    image_data = generate_pro_chart_v4(symbol, interval='15m', limit=200)
    
    if image_data:
        os.makedirs('output', exist_ok=True)
        output_path = f'output/chart_pro_v4_{symbol}.png'
        with open(output_path, 'wb') as f:
            f.write(image_data)
        logger.info(f"✅ 图片已保存: {output_path}")
        return True
    return False


if __name__ == '__main__':
    test_chart_v4('BTC')
    test_chart_v4('ETH')
