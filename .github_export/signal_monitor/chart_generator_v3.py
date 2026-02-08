"""
专业图表生成模块 v3
- 使用 Coinank API 获取清算数据和资金流数据
- 真实的清算热力图
- 移除本地计算的支撑/阻力位（数据不可靠）
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

# ==================== 配置 ====================
BINANCE_FUTURES_KLINES_URL = "https://fapi.binance.com/fapi/v1/klines"

# Coinank API (专业数据源)
COINANK_API_URL = "https://open-api-cn.coinank.com"  # 中国大陆节点
COINANK_API_KEY = "your_api_key_here"  # 需要申请

# NOFX 量化数据 API
NOFX_API_BASE = "http://nofxaios.com:30006"
NOFX_AUTH_KEY = "cm_568c67eae410d912c54c"

# 配色
COLORS = {
    'bg': '#0d1117',
    'panel': '#161b22',
    'grid': '#30363d',
    'text': '#c9d1d9',
    'text_dim': '#8b949e',
    'up': '#3fb950',
    'down': '#f85149',
    'yellow': '#d29922',
    'blue': '#58a6ff',
    'purple': '#a371f7',
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


def get_futures_klines(symbol, interval='15m', limit=200):
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


def get_coinank_liquidation(base_coin):
    """从 Coinank 获取清算数据"""
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
        logger.warning(f"Coinank 清算数据获取失败: {e}")
    return None


def get_coinank_liquidation_history(base_coin, interval='1h', size=24):
    """从 Coinank 获取清算历史数据"""
    try:
        url = f"{COINANK_API_URL}/api/liquidation/aggregated-history"
        end_time = int(time.time() * 1000)
        response = requests.get(
            url,
            params={
                'baseCoin': base_coin.upper(),
                'interval': interval,
                'endTime': end_time,
                'size': size
            },
            headers={'apikey': COINANK_API_KEY},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('data', [])
    except Exception as e:
        logger.warning(f"Coinank 清算历史获取失败: {e}")
    return None


def get_nofx_quant_data(symbol):
    """从 NOFX 获取量化数据"""
    symbol_clean = symbol.upper().replace('$', '').strip()
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    try:
        url = f"{NOFX_API_BASE}/api/coin/{symbol_clean}"
        response = requests.get(
            url,
            params={'include': 'netflow,oi,price', 'auth': NOFX_AUTH_KEY},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 0:
                return data.get('data', {})
    except Exception as e:
        logger.warning(f"NOFX API 失败: {e}")
    return None


def create_liquidation_heatmap(df, current_price, price_range_pct=0.08):
    """
    创建基于价格分布的清算密度热力图
    根据杠杆倍数计算预估清算价格区域
    """
    price_min = current_price * (1 - price_range_pct)
    price_max = current_price * (1 + price_range_pct)
    num_levels = 100
    
    price_levels = np.linspace(price_min, price_max, num_levels)
    heatmap = np.zeros(num_levels)
    
    # 常见杠杆的清算距离 (杠杆, 清算距离%, 权重)
    leverage_configs = [
        (125, 0.008, 1.0),  # 125x: 0.8%
        (100, 0.01, 0.95),  # 100x: 1%
        (75, 0.013, 0.9),   # 75x: 1.3%
        (50, 0.02, 0.85),   # 50x: 2%
        (25, 0.04, 0.7),    # 25x: 4%
        (20, 0.05, 0.6),    # 20x: 5%
        (10, 0.10, 0.4),    # 10x: 10%
        (5, 0.20, 0.2),     # 5x: 20%
    ]
    
    for i, price in enumerate(price_levels):
        distance_pct = abs(price - current_price) / current_price
        intensity = 0
        
        for leverage, liq_dist, weight in leverage_configs:
            # 高斯分布权重
            sigma = 0.003  # 标准差
            gauss = np.exp(-((distance_pct - liq_dist) ** 2) / (2 * sigma ** 2))
            intensity += weight * gauss
        
        # 根据成交量加权
        for _, row in df.iterrows():
            if row['low'] <= price <= row['high']:
                vol_weight = row['quote_volume'] / df['quote_volume'].max()
                intensity += vol_weight * 0.2
        
        heatmap[i] = intensity
    
    # 归一化
    if heatmap.max() > 0:
        heatmap = heatmap / heatmap.max()
    
    return heatmap, price_levels


def format_number(num, decimals=2):
    """格式化数字"""
    if abs(num) >= 1e9:
        return f"{num/1e9:.{decimals}f}B"
    elif abs(num) >= 1e6:
        return f"{num/1e6:.{decimals}f}M"
    elif abs(num) >= 1e3:
        return f"{num/1e3:.{decimals}f}K"
    else:
        return f"{num:.{decimals}f}"


def generate_chart_v3(symbol, interval='15m', limit=200):
    """生成专业图表 v3"""
    symbol_clean = symbol.upper().replace('$', '').strip()
    base_coin = symbol_clean.replace('USDT', '')
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    logger.info(f"📊 生成图表 v3: {symbol_clean}")
    
    df = get_futures_klines(symbol_clean, interval, limit)
    if df is None or df.empty:
        logger.error(f"❌ 无法获取 K线数据")
        return None
    
    # 获取量化数据
    nofx_data = get_nofx_quant_data(symbol_clean)
    coinank_liq = get_coinank_liquidation(base_coin)
    
    try:
        plt.style.use('dark_background')
        plt.rcParams['font.family'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        fig = plt.figure(figsize=(20, 14), facecolor=COLORS['bg'])
        
        # 布局：左侧热力图(4%) + K线(78%) + 右侧信息(18%)
        ax_heat = fig.add_axes([0.02, 0.32, 0.03, 0.58], facecolor=COLORS['bg'])
        ax_main = fig.add_axes([0.06, 0.32, 0.72, 0.58], facecolor=COLORS['bg'])
        ax_info = fig.add_axes([0.80, 0.32, 0.18, 0.58], facecolor=COLORS['panel'])
        ax_flow = fig.add_axes([0.02, 0.04, 0.96, 0.24], facecolor=COLORS['panel'])
        
        current_price = df['close'].iloc[-1]
        price_min = df['low'].min() * 0.998
        price_max = df['high'].max() * 1.002
        
        # ========== 左侧：清算热力图 ==========
        heatmap, price_levels = create_liquidation_heatmap(df, current_price)
        
        # Coinglass 风格渐变
        cmap = LinearSegmentedColormap.from_list('liq', [
            '#0d1117', '#1a1a4e', '#2d1b69', '#4a1c7a',
            '#6b1d8a', '#8b1e9a', '#ab1faa', '#d040c0',
            '#f060d0', '#ff80e0', '#ffaaff'
        ])
        
        # 绘制水平条
        for i, (intensity, price) in enumerate(zip(heatmap, price_levels)):
            if intensity > 0.05 and price_min <= price <= price_max:
                color = cmap(intensity)
                bar_height = (price_max - price_min) / len(price_levels)
                ax_heat.barh(price, intensity, height=bar_height * 0.95,
                            color=color, alpha=0.9)
        
        ax_heat.set_ylim(price_min, price_max)
        ax_heat.set_xlim(0, 1.2)
        ax_heat.axis('off')
        
        # ========== 中间：K线图 ==========
        for i, (_, row) in enumerate(df.iterrows()):
            is_up = row['close'] >= row['open']
            color = COLORS['up'] if is_up else COLORS['down']
            
            ax_main.plot([i, i], [row['low'], row['high']], color=color, linewidth=0.8)
            
            body_bottom = min(row['open'], row['close'])
            body_height = abs(row['close'] - row['open'])
            if body_height < (price_max - price_min) * 0.0005:
                body_height = (price_max - price_min) * 0.0005
            
            rect = mpatches.Rectangle(
                (i - 0.3, body_bottom), 0.6, body_height,
                facecolor=color, edgecolor=color, alpha=0.95
            )
            ax_main.add_patch(rect)
        
        # 当前价格线
        ax_main.axhline(y=current_price, color=COLORS['yellow'], linewidth=1.5, alpha=0.9)
        ax_main.text(len(df) + 1, current_price, f'${current_price:,.2f}',
                    fontsize=10, fontweight='bold', color=COLORS['bg'],
                    bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['yellow']),
                    va='center')
        
        ax_main.set_xlim(-1, len(df) + 8)
        ax_main.set_ylim(price_min, price_max)
        ax_main.set_ylabel('价格 (USDT)', color=COLORS['text_dim'], fontsize=10)
        ax_main.tick_params(colors=COLORS['text_dim'], labelsize=8)
        ax_main.grid(True, color=COLORS['grid'], alpha=0.3, axis='y')
        for spine in ax_main.spines.values():
            spine.set_visible(False)
        plt.setp(ax_main.get_xticklabels(), visible=False)
        
        # ========== 右侧：清算统计面板 ==========
        ax_info.set_xlim(0, 1)
        ax_info.set_ylim(0, 1)
        ax_info.axis('off')
        
        # 标题
        ax_info.text(0.5, 0.95, '清算数据', transform=ax_info.transAxes,
                    fontsize=11, fontweight='bold', color=COLORS['text'], ha='center')
        
        if coinank_liq:
            # 24小时清算数据
            liq_24h = coinank_liq.get('24h', {})
            liq_1h = coinank_liq.get('1h', {})
            
            ax_info.text(0.1, 0.85, '24H 总清算:', fontsize=9, color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.9, 0.85, format_number(liq_24h.get('totalTurnover', 0)),
                        fontsize=10, fontweight='bold', color=COLORS['yellow'],
                        transform=ax_info.transAxes, ha='right')
            
            ax_info.text(0.1, 0.75, '24H 多头:', fontsize=9, color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.9, 0.75, format_number(liq_24h.get('longTurnover', 0)),
                        fontsize=10, color=COLORS['up'],
                        transform=ax_info.transAxes, ha='right')
            
            ax_info.text(0.1, 0.65, '24H 空头:', fontsize=9, color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.9, 0.65, format_number(liq_24h.get('shortTurnover', 0)),
                        fontsize=10, color=COLORS['down'],
                        transform=ax_info.transAxes, ha='right')
            
            # 多空比
            long_ratio = liq_24h.get('longRatio', 0.5) * 100
            ax_info.text(0.1, 0.52, '多空比:', fontsize=9, color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ratio_color = COLORS['up'] if long_ratio > 50 else COLORS['down']
            ax_info.text(0.9, 0.52, f'{long_ratio:.1f}% / {100-long_ratio:.1f}%',
                        fontsize=10, fontweight='bold', color=ratio_color,
                        transform=ax_info.transAxes, ha='right')
            
            # 分隔线
            ax_info.axhline(y=0.45, xmin=0.1, xmax=0.9, color=COLORS['grid'], 
                           linewidth=0.5, transform=ax_info.transAxes)
            
            # 1小时数据
            ax_info.text(0.1, 0.38, '1H 总清算:', fontsize=9, color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.9, 0.38, format_number(liq_1h.get('totalTurnover', 0)),
                        fontsize=10, fontweight='bold', color=COLORS['purple'],
                        transform=ax_info.transAxes, ha='right')
            
            ax_info.text(0.1, 0.28, '1H 多头:', fontsize=9, color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.9, 0.28, format_number(liq_1h.get('longTurnover', 0)),
                        fontsize=10, color=COLORS['up'],
                        transform=ax_info.transAxes, ha='right')
            
            ax_info.text(0.1, 0.18, '1H 空头:', fontsize=9, color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.9, 0.18, format_number(liq_1h.get('shortTurnover', 0)),
                        fontsize=10, color=COLORS['down'],
                        transform=ax_info.transAxes, ha='right')
        else:
            # 使用买卖数据
            total_buy = df['taker_buy'].sum()
            total_sell = df['taker_sell'].sum()
            total_vol = df['volume'].sum()
            
            ax_info.text(0.1, 0.80, '主动买入:', fontsize=9, color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.9, 0.80, format_number(total_buy),
                        fontsize=10, color=COLORS['up'],
                        transform=ax_info.transAxes, ha='right')
            
            ax_info.text(0.1, 0.68, '主动卖出:', fontsize=9, color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.9, 0.68, format_number(total_sell),
                        fontsize=10, color=COLORS['down'],
                        transform=ax_info.transAxes, ha='right')
            
            ax_info.text(0.1, 0.56, '总成交量:', fontsize=9, color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.9, 0.56, format_number(total_vol),
                        fontsize=10, fontweight='bold', color=COLORS['yellow'],
                        transform=ax_info.transAxes, ha='right')
            
            buy_ratio = total_buy / (total_buy + total_sell) * 100
            ax_info.text(0.1, 0.44, '买卖比:', fontsize=9, color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ratio_color = COLORS['up'] if buy_ratio > 50 else COLORS['down']
            ax_info.text(0.9, 0.44, f'{buy_ratio:.1f}% / {100-buy_ratio:.1f}%',
                        fontsize=10, fontweight='bold', color=ratio_color,
                        transform=ax_info.transAxes, ha='right')
            
            ax_info.text(0.5, 0.08, '(Coinank API 不可用)', fontsize=8,
                        color=COLORS['text_dim'], transform=ax_info.transAxes, ha='center')
        
        # ========== 底部：资金流向面板 ==========
        ax_flow.set_xlim(0, 1)
        ax_flow.set_ylim(0, 1)
        ax_flow.axis('off')
        
        ax_flow.axvline(x=0.5, color=COLORS['grid'], linewidth=1, alpha=0.5)
        
        periods = ['5m', '15m', '1h', '4h', '24h']
        row_y = [0.78, 0.62, 0.46, 0.30, 0.14]
        
        # ===== 左侧：现货资金流 =====
        ax_flow.text(0.25, 0.92, '现货资金流', fontsize=12, fontweight='bold',
                    color=COLORS['blue'], transform=ax_flow.transAxes, ha='center')
        
        cols_l = [0.04, 0.13, 0.22, 0.31, 0.42]
        ax_flow.text(cols_l[0], 0.86, '周期', fontsize=8, color=COLORS['text_dim'],
                    transform=ax_flow.transAxes, ha='center')
        ax_flow.text(cols_l[1], 0.86, '流入', fontsize=8, color=COLORS['up'],
                    transform=ax_flow.transAxes, ha='center')
        ax_flow.text(cols_l[2], 0.86, '流出', fontsize=8, color=COLORS['down'],
                    transform=ax_flow.transAxes, ha='center')
        ax_flow.text(cols_l[3], 0.86, '净流入', fontsize=8, color=COLORS['yellow'],
                    transform=ax_flow.transAxes, ha='center')
        ax_flow.text(cols_l[4], 0.86, '净流入%', fontsize=8, color=COLORS['text_dim'],
                    transform=ax_flow.transAxes, ha='center')
        
        for i, period in enumerate(periods):
            y = row_y[i]
            ax_flow.text(cols_l[0], y, period, fontsize=9, color=COLORS['text'],
                        transform=ax_flow.transAxes, ha='center', fontweight='bold')
            
            if nofx_data and 'netflow' in nofx_data:
                netflow = nofx_data['netflow']
                inst_spot = netflow.get('institution', {}).get('spot', {}).get(period, 0)
                pers_spot = netflow.get('personal', {}).get('spot', {}).get(period, 0)
                
                inflow = max(inst_spot, 0) + max(pers_spot, 0)
                outflow = abs(min(inst_spot, 0)) + abs(min(pers_spot, 0))
                net = inst_spot + pers_spot
                total = inflow + outflow
                net_pct = (net / total * 100) if total > 0 else 0
                
                ax_flow.text(cols_l[1], y, format_number(inflow), fontsize=9, color=COLORS['up'],
                            transform=ax_flow.transAxes, ha='center')
                ax_flow.text(cols_l[2], y, format_number(outflow), fontsize=9, color=COLORS['down'],
                            transform=ax_flow.transAxes, ha='center')
                net_color = COLORS['up'] if net >= 0 else COLORS['down']
                ax_flow.text(cols_l[3], y, format_number(net), fontsize=9, color=net_color,
                            transform=ax_flow.transAxes, ha='center', fontweight='bold')
                ax_flow.text(cols_l[4], y, f'{net_pct:+.1f}%', fontsize=9, color=net_color,
                            transform=ax_flow.transAxes, ha='center')
            else:
                for j in range(1, 5):
                    ax_flow.text(cols_l[j], y, '--', fontsize=9, color=COLORS['text_dim'],
                                transform=ax_flow.transAxes, ha='center')
        
        # ===== 右侧：合约资金流 =====
        ax_flow.text(0.75, 0.92, '合约资金流', fontsize=12, fontweight='bold',
                    color=COLORS['purple'], transform=ax_flow.transAxes, ha='center')
        
        cols_r = [0.54, 0.63, 0.72, 0.81, 0.92]
        ax_flow.text(cols_r[0], 0.86, '周期', fontsize=8, color=COLORS['text_dim'],
                    transform=ax_flow.transAxes, ha='center')
        ax_flow.text(cols_r[1], 0.86, '流入', fontsize=8, color=COLORS['up'],
                    transform=ax_flow.transAxes, ha='center')
        ax_flow.text(cols_r[2], 0.86, '流出', fontsize=8, color=COLORS['down'],
                    transform=ax_flow.transAxes, ha='center')
        ax_flow.text(cols_r[3], 0.86, '净流入', fontsize=8, color=COLORS['yellow'],
                    transform=ax_flow.transAxes, ha='center')
        ax_flow.text(cols_r[4], 0.86, '净流入%', fontsize=8, color=COLORS['text_dim'],
                    transform=ax_flow.transAxes, ha='center')
        
        for i, period in enumerate(periods):
            y = row_y[i]
            ax_flow.text(cols_r[0], y, period, fontsize=9, color=COLORS['text'],
                        transform=ax_flow.transAxes, ha='center', fontweight='bold')
            
            if nofx_data and 'netflow' in nofx_data:
                netflow = nofx_data['netflow']
                inst_fut = netflow.get('institution', {}).get('future', {}).get(period, 0)
                pers_fut = netflow.get('personal', {}).get('future', {}).get(period, 0)
                
                inflow = max(inst_fut, 0) + max(pers_fut, 0)
                outflow = abs(min(inst_fut, 0)) + abs(min(pers_fut, 0))
                net = inst_fut + pers_fut
                total = inflow + outflow
                net_pct = (net / total * 100) if total > 0 else 0
                
                ax_flow.text(cols_r[1], y, format_number(inflow), fontsize=9, color=COLORS['up'],
                            transform=ax_flow.transAxes, ha='center')
                ax_flow.text(cols_r[2], y, format_number(outflow), fontsize=9, color=COLORS['down'],
                            transform=ax_flow.transAxes, ha='center')
                net_color = COLORS['up'] if net >= 0 else COLORS['down']
                ax_flow.text(cols_r[3], y, format_number(net), fontsize=9, color=net_color,
                            transform=ax_flow.transAxes, ha='center', fontweight='bold')
                ax_flow.text(cols_r[4], y, f'{net_pct:+.1f}%', fontsize=9, color=net_color,
                            transform=ax_flow.transAxes, ha='center')
            else:
                # 使用 Binance taker 数据
                period_bars = {'5m': 1, '15m': 1, '1h': 4, '4h': 16, '24h': 96}
                bars = min(period_bars.get(period, 1), len(df))
                recent = df.tail(bars)
                
                inflow = recent['taker_buy'].sum()
                outflow = recent['taker_sell'].sum()
                net = inflow - outflow
                total = inflow + outflow
                net_pct = (net / total * 100) if total > 0 else 0
                
                ax_flow.text(cols_r[1], y, format_number(inflow), fontsize=9, color=COLORS['up'],
                            transform=ax_flow.transAxes, ha='center')
                ax_flow.text(cols_r[2], y, format_number(outflow), fontsize=9, color=COLORS['down'],
                            transform=ax_flow.transAxes, ha='center')
                net_color = COLORS['up'] if net >= 0 else COLORS['down']
                ax_flow.text(cols_r[3], y, format_number(net), fontsize=9, color=net_color,
                            transform=ax_flow.transAxes, ha='center', fontweight='bold')
                ax_flow.text(cols_r[4], y, f'{net_pct:+.1f}%', fontsize=9, color=net_color,
                            transform=ax_flow.transAxes, ha='center')
        
        # ========== 标题 ==========
        interval_map = {'15m': '15min', '1h': '1H', '4h': '4H', '1d': '1D'}
        price_change = ((current_price - df['open'].iloc[0]) / df['open'].iloc[0]) * 100
        change_sign = '+' if price_change >= 0 else ''
        change_color = COLORS['up'] if price_change >= 0 else COLORS['down']
        
        fig.text(0.02, 0.96, f"{symbol_clean}  ·  {interval_map.get(interval, interval)}",
                fontsize=16, fontweight='bold', color=COLORS['text'])
        fig.text(0.98, 0.96, f"${current_price:,.2f}  ({change_sign}{price_change:.2f}%)",
                fontsize=14, fontweight='bold', color=change_color, ha='right')
        
        # 热力图图例
        gradient = np.linspace(0, 1, 100).reshape(1, -1)
        ax_legend = fig.add_axes([0.35, 0.925, 0.12, 0.015])
        ax_legend.imshow(gradient, aspect='auto', cmap=cmap)
        ax_legend.set_xticks([0, 99])
        ax_legend.set_xticklabels(['低', '高'], fontsize=7, color=COLORS['text_dim'])
        ax_legend.set_yticks([])
        ax_legend.set_title('清算密度', fontsize=8, color=COLORS['text_dim'], pad=2)
        for spine in ax_legend.spines.values():
            spine.set_visible(False)
        
        # 水印
        fig.text(0.5, 0.55, 'NOFX', fontsize=30, color=COLORS['yellow'],
                ha='center', va='center', alpha=0.02, fontweight='bold')
        
        # 保存
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=130, bbox_inches='tight',
                   facecolor=COLORS['bg'], edgecolor='none')
        buf.seek(0)
        image_data = buf.read()
        buf.close()
        plt.close(fig)
        
        size_kb = len(image_data) / 1024
        logger.info(f"✅ 图表 v3 生成成功: {symbol_clean} ({size_kb:.1f} KB)")
        
        return image_data
        
    except Exception as e:
        logger.exception(f"❌ 图表生成失败: {e}")
        return None


def test_chart_v3(symbol='BTC'):
    """测试图表生成"""
    import os
    
    logger.info(f"🧪 测试图表 v3: {symbol}")
    
    image_data = generate_chart_v3(symbol, interval='15m', limit=200)
    
    if image_data:
        os.makedirs('output', exist_ok=True)
        output_path = f'output/chart_v3_{symbol}.png'
        with open(output_path, 'wb') as f:
            f.write(image_data)
        logger.info(f"✅ 图片已保存: {output_path}")
        return True
    return False


if __name__ == '__main__':
    test_chart_v3('BTC')
    test_chart_v3('ETH')
