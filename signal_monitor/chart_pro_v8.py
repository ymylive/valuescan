"""
专业图表生成模块 v8
- Coinank 专业清算数据 API
- 资金流具体数值显示
- 高级简约界面设计
"""

import io
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
from scipy.ndimage import gaussian_filter1d
from datetime import datetime
import time
from logger import logger
from chart_fonts import configure_matplotlib_fonts

try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False

# ==================== 配置 ====================
BINANCE_FUTURES_URL = "https://fapi.binance.com"
COINANK_API_URL = "https://open-api-cn.coinank.com"
COINANK_API_KEY = ""  # 可选，有 key 数据更全

# 高级配色 (简约深色主题)
COLORS = {
    'bg': '#0d1117',
    'panel': '#161b22',
    'grid': '#21262d',
    'text': '#f0f6fc',
    'text_dim': '#8b949e',
    'up': '#3fb950',
    'down': '#f85149',
    'yellow': '#d29922',
    'blue': '#58a6ff',
    'purple': '#a371f7',
    'cyan': '#39c5cf',
    'orange': '#db6d28',
}

FONT = {'title': 16, 'subtitle': 12, 'label': 10, 'value': 11, 'small': 9}


def get_proxies():
    proxies = {}
    try:
        from config import SOCKS5_PROXY
        if SOCKS5_PROXY:
            proxies = {'http': SOCKS5_PROXY, 'https': SOCKS5_PROXY}
    except:
        pass
    return proxies


# ==================== CCXT ====================

def get_exchange():
    if not CCXT_AVAILABLE:
        return None
    try:
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        proxies = get_proxies()
        if proxies:
            exchange.proxies = proxies
        return exchange
    except Exception as e:
        logger.warning(f"交易所初始化失败: {e}")
    return None


def get_klines(symbol, timeframe='15m', limit=200):
    exchange = get_exchange()
    if not exchange:
        return None
    
    base = symbol.upper().replace('$', '').replace('USDT', '').strip()
    try:
        ohlcv = exchange.fetch_ohlcv(f"{base}/USDT", timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        logger.warning(f"K线获取失败: {e}")
    return None


def get_ticker(symbol):
    exchange = get_exchange()
    if not exchange:
        return None
    base = symbol.upper().replace('$', '').replace('USDT', '').strip()
    try:
        return exchange.fetch_ticker(f"{base}/USDT")
    except Exception as e:
        logger.warning(f"Ticker获取失败: {e}")
    return None


def get_orderbook(symbol, limit=500):
    exchange = get_exchange()
    if not exchange:
        return None
    base = symbol.upper().replace('$', '').replace('USDT', '').strip()
    try:
        return exchange.fetch_order_book(f"{base}/USDT", limit=limit)
    except Exception as e:
        logger.warning(f"订单簿获取失败: {e}")
    return None


def get_funding_rate(symbol):
    exchange = get_exchange()
    if not exchange:
        return None
    base = symbol.upper().replace('$', '').replace('USDT', '').strip()
    try:
        return exchange.fetch_funding_rate(f"{base}/USDT")
    except Exception as e:
        logger.warning(f"资金费率获取失败: {e}")
    return None


# ==================== Coinank 清算数据 ====================

def get_coinank_liquidation(base_coin):
    """获取 Coinank 清算统计数据"""
    try:
        headers = {}
        if COINANK_API_KEY:
            headers['apikey'] = COINANK_API_KEY
        
        url = f"{COINANK_API_URL}/api/liquidation/allExchange/intervals"
        response = requests.get(url, params={'baseCoin': base_coin.upper()},
                               headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('data', {})
    except Exception as e:
        logger.warning(f"Coinank清算数据获取失败: {e}")
    return None


def get_coinank_liquidation_history(base_coin, interval='1h', size=24):
    """获取 Coinank 清算历史数据"""
    try:
        headers = {}
        if COINANK_API_KEY:
            headers['apikey'] = COINANK_API_KEY
        
        url = f"{COINANK_API_URL}/api/liquidation/aggregated-history"
        response = requests.get(url, params={
            'baseCoin': base_coin.upper(),
            'interval': interval,
            'size': size
        }, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('data', [])
    except Exception as e:
        logger.warning(f"Coinank清算历史获取失败: {e}")
    return None


# ==================== Binance 数据 ====================

def get_taker_volume(symbol, period='5m', limit=50):
    symbol_clean = symbol.upper().replace('$', '').strip()
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    try:
        url = f"{BINANCE_FUTURES_URL}/futures/data/takerlongshortRatio"
        response = requests.get(url, params={
            'symbol': symbol_clean, 'period': period, 'limit': limit
        }, proxies=get_proxies(), timeout=10)
        
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.warning(f"Taker数据获取失败: {e}")
    return None


def get_open_interest_hist(symbol, period='5m', limit=50):
    """获取持仓量历史"""
    symbol_clean = symbol.upper().replace('$', '').strip()
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    try:
        url = f"{BINANCE_FUTURES_URL}/futures/data/openInterestHist"
        response = requests.get(url, params={
            'symbol': symbol_clean, 'period': period, 'limit': limit
        }, proxies=get_proxies(), timeout=10)
        
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.warning(f"OI历史获取失败: {e}")
    return None


# ==================== 核心算法 ====================

def analyze_orderbook_heatmap(orderbook, current_price, num_levels=60):
    """分析订单簿深度，模拟清算热力图"""
    if not orderbook:
        return None
    
    bids = orderbook.get('bids', [])
    asks = orderbook.get('asks', [])
    
    if not bids or not asks:
        return None
    
    price_range = current_price * 0.05
    price_min = current_price - price_range
    price_max = current_price + price_range
    level_width = (price_max - price_min) / num_levels
    
    heatmap = np.zeros(num_levels)
    price_levels = np.linspace(price_min, price_max, num_levels)
    
    for price, amount in bids:
        if price_min <= price <= price_max:
            idx = int((price - price_min) / level_width)
            if 0 <= idx < num_levels:
                heatmap[idx] += amount * price
    
    for price, amount in asks:
        if price_min <= price <= price_max:
            idx = int((price - price_min) / level_width)
            if 0 <= idx < num_levels:
                heatmap[idx] += amount * price
    
    heatmap_smooth = gaussian_filter1d(heatmap, sigma=1.5)
    
    if heatmap_smooth.max() > 0:
        heatmap_norm = heatmap_smooth / heatmap_smooth.max()
    else:
        heatmap_norm = heatmap_smooth
    
    # 找主力关键位
    key_levels = []
    for i in range(2, len(heatmap_norm) - 2):
        if heatmap_norm[i] > 0.3:
            is_peak = all(heatmap_norm[i] >= heatmap_norm[i+j] for j in range(-2, 3) if j != 0)
            if is_peak:
                price = price_levels[i]
                if price < current_price * 0.998:
                    level_type = 'support'
                elif price > current_price * 1.002:
                    level_type = 'resistance'
                else:
                    continue
                
                key_levels.append({
                    'price': price,
                    'strength': heatmap_norm[i],
                    'type': level_type,
                    'value': heatmap[i]
                })
    
    key_levels = sorted(key_levels, key=lambda x: -x['strength'])
    supports = [l for l in key_levels if l['type'] == 'support'][:2]
    resistances = [l for l in key_levels if l['type'] == 'resistance'][:2]
    
    return {
        'heatmap': heatmap_norm,
        'price_levels': price_levels,
        'supports': supports,
        'resistances': resistances
    }


def format_num(num, decimals=2):
    if abs(num) >= 1e9:
        return f"${num/1e9:.{decimals}f}B"
    elif abs(num) >= 1e6:
        return f"${num/1e6:.{decimals}f}M"
    elif abs(num) >= 1e3:
        return f"${num/1e3:.{decimals}f}K"
    return f"${num:.{decimals}f}"


def format_pct(num):
    return f"{num:+.2f}%" if num >= 0 else f"{num:.2f}%"


# ==================== 图表生成 ====================

def generate_chart_v8(symbol, interval='15m', limit=200):
    """生成专业图表 v8 - 高级简约风格"""
    symbol_clean = symbol.upper().replace('$', '').strip()
    base_coin = symbol_clean.replace('USDT', '')
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    logger.info(f"📊 生成图表 v8: {symbol_clean}")
    
    # 获取数据
    df = get_klines(symbol_clean, interval, limit)
    if df is None or df.empty:
        logger.error("❌ K线获取失败")
        return None
    
    ticker = get_ticker(symbol_clean)
    orderbook = get_orderbook(symbol_clean, 1000)
    funding = get_funding_rate(symbol_clean)
    taker_data = get_taker_volume(symbol_clean, '5m', 30)
    coinank_liq = get_coinank_liquidation(base_coin)
    liq_history = get_coinank_liquidation_history(base_coin, '1h', 24)
    
    try:
        plt.style.use('dark_background')
        configure_matplotlib_fonts()
        plt.rcParams['axes.unicode_minus'] = False
        
        fig = plt.figure(figsize=(22, 14), facecolor=COLORS['bg'])
        
        # 简约布局
        ax_heat = fig.add_axes([0.02, 0.22, 0.025, 0.68], facecolor=COLORS['bg'])
        ax_main = fig.add_axes([0.055, 0.22, 0.60, 0.68], facecolor=COLORS['bg'])
        ax_info = fig.add_axes([0.67, 0.22, 0.31, 0.68], facecolor=COLORS['panel'])
        ax_flow = fig.add_axes([0.02, 0.03, 0.96, 0.16], facecolor=COLORS['panel'])
        
        current_price = df['close'].iloc[-1]
        price_min = df['low'].min() * 0.996
        price_max = df['high'].max() * 1.004
        
        # ========== 热力图 ==========
        depth_data = analyze_orderbook_heatmap(orderbook, current_price, 80)
        
        cmap = LinearSegmentedColormap.from_list('heat', [
            COLORS['bg'], '#1a237e', '#303f9f', '#3f51b5',
            '#7986cb', '#9fa8da', '#c5cae9', '#fff59d',
            '#ffee58', '#ffc107', '#ff9800', '#ff5722', '#f44336'
        ])
        
        if depth_data:
            heatmap = depth_data['heatmap']
            heat_levels = depth_data['price_levels']
            supports = depth_data['supports']
            resistances = depth_data['resistances']
            
            for i, (intensity, price) in enumerate(zip(heatmap, heat_levels)):
                if intensity > 0.08 and price_min <= price <= price_max:
                    bar_height = (price_max - price_min) / len(heat_levels)
                    ax_heat.barh(price, intensity, height=bar_height,
                                color=cmap(intensity), alpha=0.95)
            
            ax_heat.set_ylim(price_min, price_max)
            ax_heat.set_xlim(0, 1.1)
            ax_heat.axis('off')
        else:
            supports, resistances = [], []
            ax_heat.axis('off')
        
        # ========== K线图 ==========
        for i, sup in enumerate(supports[:2]):
            price = sup['price']
            if price_min <= price <= price_max:
                ax_main.axhline(y=price, color=COLORS['up'], linewidth=1.5, alpha=0.6)
        
        for i, res in enumerate(resistances[:2]):
            price = res['price']
            if price_min <= res['price'] <= price_max:
                ax_main.axhline(y=price, color=COLORS['down'], linewidth=1.5, alpha=0.6)
        
        for i, (_, row) in enumerate(df.iterrows()):
            is_up = row['close'] >= row['open']
            color = COLORS['up'] if is_up else COLORS['down']
            ax_main.plot([i, i], [row['low'], row['high']], color=color, linewidth=0.7)
            
            body_bottom = min(row['open'], row['close'])
            body_height = max(abs(row['close'] - row['open']), (price_max - price_min) * 0.0002)
            rect = mpatches.Rectangle((i - 0.35, body_bottom), 0.7, body_height,
                                       facecolor=color, edgecolor=color, alpha=0.9)
            ax_main.add_patch(rect)
        
        ax_main.axhline(y=current_price, color=COLORS['yellow'], linewidth=2)
        
        ax_main.set_xlim(-1, len(df) + 1)
        ax_main.set_ylim(price_min, price_max)
        ax_main.tick_params(colors=COLORS['text_dim'], labelsize=9)
        ax_main.grid(True, color=COLORS['grid'], alpha=0.4, axis='y', linestyle='-', linewidth=0.5)
        ax_main.set_facecolor(COLORS['bg'])
        for spine in ax_main.spines.values():
            spine.set_visible(False)
        plt.setp(ax_main.get_xticklabels(), visible=False)
        
        # ========== 右侧信息面板 ==========
        ax_info.set_xlim(0, 1)
        ax_info.set_ylim(0, 1)
        ax_info.axis('off')
        
        y = 0.96
        
        # 价格区域
        ax_info.text(0.5, y, f'${current_price:,.2f}', fontsize=24, fontweight='bold',
                    color=COLORS['text'], transform=ax_info.transAxes, ha='center')
        y -= 0.055
        
        if ticker:
            pct = ticker.get('percentage', 0)
            change_color = COLORS['up'] if pct >= 0 else COLORS['down']
            ax_info.text(0.5, y, format_pct(pct), fontsize=16, fontweight='bold',
                        color=change_color, transform=ax_info.transAxes, ha='center')
        y -= 0.06
        
        # 分隔线
        ax_info.plot([0.05, 0.95], [y, y], color=COLORS['grid'], linewidth=1, 
                    transform=ax_info.transAxes)
        y -= 0.04
        
        # 清算数据 (Coinank)
        ax_info.text(0.5, y, '清算数据', fontsize=FONT['subtitle'], fontweight='bold',
                    color=COLORS['cyan'], transform=ax_info.transAxes, ha='center')
        y -= 0.045
        
        if coinank_liq:
            h24 = coinank_liq.get('24h', {})
            h1 = coinank_liq.get('1h', {})
            
            # 24H 清算
            total_24h = h24.get('totalTurnover', 0)
            long_24h = h24.get('longTurnover', 0)
            short_24h = h24.get('shortTurnover', 0)
            
            ax_info.text(0.05, y, '24H 总清算', fontsize=FONT['label'], color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.95, y, format_num(total_24h), fontsize=FONT['value'], fontweight='bold',
                        color=COLORS['yellow'], transform=ax_info.transAxes, ha='right')
            y -= 0.038
            
            ax_info.text(0.05, y, '  多头爆仓', fontsize=FONT['small'], color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.95, y, format_num(long_24h), fontsize=FONT['label'],
                        color=COLORS['up'], transform=ax_info.transAxes, ha='right')
            y -= 0.035
            
            ax_info.text(0.05, y, '  空头爆仓', fontsize=FONT['small'], color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.95, y, format_num(short_24h), fontsize=FONT['label'],
                        color=COLORS['down'], transform=ax_info.transAxes, ha='right')
            y -= 0.04
            
            # 1H 清算
            total_1h = h1.get('totalTurnover', 0)
            ax_info.text(0.05, y, '1H 总清算', fontsize=FONT['label'], color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.95, y, format_num(total_1h), fontsize=FONT['value'], fontweight='bold',
                        color=COLORS['purple'], transform=ax_info.transAxes, ha='right')
        else:
            ax_info.text(0.5, y, '数据加载中...', fontsize=FONT['small'],
                        color=COLORS['text_dim'], transform=ax_info.transAxes, ha='center')
        
        y -= 0.05
        ax_info.plot([0.05, 0.95], [y, y], color=COLORS['grid'], linewidth=1,
                    transform=ax_info.transAxes)
        y -= 0.04
        
        # 主力关键位
        ax_info.text(0.5, y, '主力关键位', fontsize=FONT['subtitle'], fontweight='bold',
                    color=COLORS['blue'], transform=ax_info.transAxes, ha='center')
        y -= 0.045
        
        for i, sup in enumerate(supports[:2]):
            ax_info.text(0.05, y, f'支撑 S{i+1}', fontsize=FONT['label'], color=COLORS['up'],
                        transform=ax_info.transAxes)
            ax_info.text(0.95, y, f'${sup["price"]:,.0f}', fontsize=FONT['value'], fontweight='bold',
                        color=COLORS['up'], transform=ax_info.transAxes, ha='right')
            y -= 0.038
        
        for i, res in enumerate(resistances[:2]):
            ax_info.text(0.05, y, f'阻力 R{i+1}', fontsize=FONT['label'], color=COLORS['down'],
                        transform=ax_info.transAxes)
            ax_info.text(0.95, y, f'${res["price"]:,.0f}', fontsize=FONT['value'], fontweight='bold',
                        color=COLORS['down'], transform=ax_info.transAxes, ha='right')
            y -= 0.038
        
        y -= 0.02
        ax_info.plot([0.05, 0.95], [y, y], color=COLORS['grid'], linewidth=1,
                    transform=ax_info.transAxes)
        y -= 0.04
        
        # 市场数据
        ax_info.text(0.5, y, '市场数据', fontsize=FONT['subtitle'], fontweight='bold',
                    color=COLORS['orange'], transform=ax_info.transAxes, ha='center')
        y -= 0.045
        
        if ticker:
            ax_info.text(0.05, y, '24H 成交额', fontsize=FONT['label'], color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.95, y, format_num(ticker.get('quoteVolume', 0)),
                        fontsize=FONT['value'], color=COLORS['text'],
                        transform=ax_info.transAxes, ha='right')
            y -= 0.038
        
        if funding:
            rate = funding.get('fundingRate', 0)
            rate_pct = rate * 100 if rate else 0
            rate_color = COLORS['up'] if rate_pct >= 0 else COLORS['down']
            ax_info.text(0.05, y, '资金费率', fontsize=FONT['label'], color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.95, y, f'{rate_pct:+.4f}%', fontsize=FONT['value'], fontweight='bold',
                        color=rate_color, transform=ax_info.transAxes, ha='right')
        
        # ========== 底部资金流 ==========
        ax_flow.set_xlim(0, 1)
        ax_flow.set_ylim(0, 1)
        ax_flow.axis('off')
        
        if taker_data and len(taker_data) > 0:
            # 计算资金流
            total_buy = sum(float(t.get('buyVol', 0)) for t in taker_data[:20])
            total_sell = sum(float(t.get('sellVol', 0)) for t in taker_data[:20])
            net_flow = total_buy - total_sell
            buy_pct = total_buy / (total_buy + total_sell) * 100 if (total_buy + total_sell) > 0 else 50
            
            # 左侧：资金流数据
            ax_flow.text(0.12, 0.85, '资金流向 (Taker)', fontsize=FONT['subtitle'], fontweight='bold',
                        color=COLORS['text'], transform=ax_flow.transAxes, ha='center')
            
            ax_flow.text(0.02, 0.60, '流入 (主动买入)', fontsize=FONT['label'], color=COLORS['up'],
                        transform=ax_flow.transAxes)
            ax_flow.text(0.22, 0.60, format_num(total_buy), fontsize=FONT['value'], fontweight='bold',
                        color=COLORS['up'], transform=ax_flow.transAxes, ha='right')
            
            ax_flow.text(0.02, 0.38, '流出 (主动卖出)', fontsize=FONT['label'], color=COLORS['down'],
                        transform=ax_flow.transAxes)
            ax_flow.text(0.22, 0.38, format_num(total_sell), fontsize=FONT['value'], fontweight='bold',
                        color=COLORS['down'], transform=ax_flow.transAxes, ha='right')
            
            net_color = COLORS['up'] if net_flow >= 0 else COLORS['down']
            ax_flow.text(0.02, 0.16, '净流入', fontsize=FONT['label'], color=COLORS['text_dim'],
                        transform=ax_flow.transAxes)
            ax_flow.text(0.22, 0.16, format_num(net_flow), fontsize=FONT['value'], fontweight='bold',
                        color=net_color, transform=ax_flow.transAxes, ha='right')
            
            # 中间：进度条
            bar_left = 0.28
            bar_width = 0.25
            bar_y = 0.50
            
            ax_flow.barh(bar_y, buy_pct / 100 * bar_width, height=0.25, left=bar_left,
                        color=COLORS['up'], alpha=0.9, transform=ax_flow.transAxes)
            ax_flow.barh(bar_y, (1 - buy_pct / 100) * bar_width, height=0.25,
                        left=bar_left + buy_pct / 100 * bar_width,
                        color=COLORS['down'], alpha=0.9, transform=ax_flow.transAxes)
            
            ax_flow.text(bar_left + bar_width / 2, 0.85, f'买入 {buy_pct:.1f}%',
                        fontsize=FONT['label'], color=COLORS['up'] if buy_pct > 50 else COLORS['down'],
                        transform=ax_flow.transAxes, ha='center', fontweight='bold')
            
            # 右侧：清算历史柱状图
            if liq_history and len(liq_history) > 0:
                ax_flow.text(0.72, 0.85, '清算历史 (24H)', fontsize=FONT['subtitle'], fontweight='bold',
                            color=COLORS['text'], transform=ax_flow.transAxes, ha='center')
                
                n_bars = min(len(liq_history), 12)
                bar_area_left = 0.58
                bar_area_width = 0.38
                bar_width_each = bar_area_width / n_bars * 0.7
                
                max_val = max(d.get('all', {}).get('longTurnover', 0) + d.get('all', {}).get('shortTurnover', 0) 
                             for d in liq_history[:n_bars])
                
                for i, data in enumerate(reversed(liq_history[:n_bars])):
                    x = bar_area_left + i * (bar_area_width / n_bars)
                    long_val = data.get('all', {}).get('longTurnover', 0)
                    short_val = data.get('all', {}).get('shortTurnover', 0)
                    
                    if max_val > 0:
                        long_h = (long_val / max_val) * 0.55
                        short_h = (short_val / max_val) * 0.55
                        
                        ax_flow.bar(x + bar_width_each/2, long_h, width=bar_width_each,
                                   bottom=0.15, color=COLORS['up'], alpha=0.8,
                                   transform=ax_flow.transAxes)
                        ax_flow.bar(x + bar_width_each/2, short_h, width=bar_width_each,
                                   bottom=0.15 + long_h, color=COLORS['down'], alpha=0.8,
                                   transform=ax_flow.transAxes)
        
        # ========== 标题 ==========
        interval_map = {'5m': '5分钟', '15m': '15分钟', '1h': '1小时', '4h': '4小时'}
        fig.text(0.02, 0.95, f"{symbol_clean}", fontsize=FONT['title'], fontweight='bold',
                color=COLORS['text'])
        fig.text(0.12, 0.95, f"·  {interval_map.get(interval, interval)}", fontsize=FONT['subtitle'],
                color=COLORS['text_dim'])
        
        # 数据源
        fig.text(0.98, 0.95, 'CCXT + Coinank', fontsize=FONT['small'],
                color=COLORS['text_dim'], ha='right')
        
        # 保存
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=140, bbox_inches='tight',
                   facecolor=COLORS['bg'], edgecolor='none', pad_inches=0.1)
        buf.seek(0)
        image_data = buf.read()
        buf.close()
        plt.close(fig)
        
        size_kb = len(image_data) / 1024
        logger.info(f"✅ 图表 v8 生成成功: {symbol_clean} ({size_kb:.1f} KB)")
        
        return image_data
        
    except Exception as e:
        logger.exception(f"❌ 图表生成失败: {e}")
        return None


def test_chart_v8(symbol='BTC'):
    import os
    logger.info(f"🧪 测试图表 v8: {symbol}")
    
    image_data = generate_chart_v8(symbol, interval='15m', limit=200)
    
    if image_data:
        os.makedirs('output', exist_ok=True)
        output_path = f'output/chart_v8_{symbol}.png'
        with open(output_path, 'wb') as f:
            f.write(image_data)
        logger.info(f"✅ 图片已保存: {output_path}")
        return True
    return False


if __name__ == '__main__':
    test_chart_v8('BTC')
    test_chart_v8('ETH')
