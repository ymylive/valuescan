"""
专业图表生成模块 v6
数据源：
- CCXT: 币安 K线、订单簿深度、Ticker
- CryptoQuant API: 主力资金流向 (链上数据)
- 订单簿深度热力图: 替代清算热力图，显示真实买卖墙
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

try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    logger.warning("CCXT 未安装，请执行: pip install ccxt")

# ==================== 配置 ====================

# 注意: CryptoQuant API 需要 $99/月起，不推荐
# 使用 Binance 免费数据替代：Taker 买卖量 + Open Interest
BINANCE_FUTURES_URL = "https://fapi.binance.com"

# 配色方案
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
    'orange': '#ff9800',
}

# 字体配置
FONT = {'title': 14, 'subtitle': 11, 'label': 9, 'value': 10, 'small': 8}


def get_proxies():
    """获取代理配置"""
    proxies = {}
    try:
        from config import SOCKS5_PROXY
        if SOCKS5_PROXY:
            proxies = {'http': SOCKS5_PROXY, 'https': SOCKS5_PROXY}
    except:
        pass
    return proxies


# ==================== CCXT 数据获取 ====================

def get_binance_exchange():
    """获取币安交易所实例"""
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
        logger.warning(f"币安交易所初始化失败: {e}")
    return None


def get_klines(symbol, timeframe='15m', limit=200):
    """获取 K线数据"""
    exchange = get_binance_exchange()
    if not exchange:
        return None
    
    symbol_clean = symbol.upper().replace('$', '').strip()
    base = symbol_clean.replace('USDT', '')
    ccxt_symbol = f"{base}/USDT"
    
    try:
        ohlcv = exchange.fetch_ohlcv(ccxt_symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        logger.warning(f"K线获取失败: {e}")
    return None


def get_ticker(symbol):
    """获取 Ticker 数据"""
    exchange = get_binance_exchange()
    if not exchange:
        return None
    
    symbol_clean = symbol.upper().replace('$', '').strip()
    base = symbol_clean.replace('USDT', '')
    ccxt_symbol = f"{base}/USDT"
    
    try:
        return exchange.fetch_ticker(ccxt_symbol)
    except Exception as e:
        logger.warning(f"Ticker 获取失败: {e}")
    return None


def get_orderbook(symbol, limit=100):
    """
    获取订单簿深度数据
    这是替代清算热力图的核心数据源
    """
    exchange = get_binance_exchange()
    if not exchange:
        return None
    
    symbol_clean = symbol.upper().replace('$', '').strip()
    base = symbol_clean.replace('USDT', '')
    ccxt_symbol = f"{base}/USDT"
    
    try:
        orderbook = exchange.fetch_order_book(ccxt_symbol, limit=limit)
        return orderbook
    except Exception as e:
        logger.warning(f"订单簿获取失败: {e}")
    return None


def get_funding_rate(symbol):
    """获取资金费率"""
    exchange = get_binance_exchange()
    if not exchange:
        return None
    
    symbol_clean = symbol.upper().replace('$', '').strip()
    base = symbol_clean.replace('USDT', '')
    ccxt_symbol = f"{base}/USDT"
    
    try:
        return exchange.fetch_funding_rate(ccxt_symbol)
    except Exception as e:
        logger.warning(f"资金费率获取失败: {e}")
    return None


# ==================== Binance 免费数据 API ====================

def get_binance_taker_volume(symbol, period='5m', limit=30):
    """
    获取 Binance Taker 买卖量比例（免费）
    替代 CryptoQuant 的主力资金流向
    """
    symbol_clean = symbol.upper().replace('$', '').strip()
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    try:
        url = f"{BINANCE_FUTURES_URL}/futures/data/takerlongshortRatio"
        response = requests.get(url, params={
            'symbol': symbol_clean,
            'period': period,
            'limit': limit
        }, proxies=get_proxies(), timeout=10)
        
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.warning(f"Binance Taker 数据获取失败: {e}")
    return None


def get_binance_open_interest(symbol):
    """
    获取 Binance 持仓量数据（免费）
    """
    symbol_clean = symbol.upper().replace('$', '').strip()
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    try:
        url = f"{BINANCE_FUTURES_URL}/fapi/v1/openInterest"
        response = requests.get(url, params={'symbol': symbol_clean},
                               proxies=get_proxies(), timeout=10)
        
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.warning(f"Binance OI 数据获取失败: {e}")
    return None


def get_binance_long_short_ratio(symbol, period='5m', limit=30):
    """
    获取 Binance 多空持仓人数比（免费）
    """
    symbol_clean = symbol.upper().replace('$', '').strip()
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    try:
        url = f"{BINANCE_FUTURES_URL}/futures/data/globalLongShortAccountRatio"
        response = requests.get(url, params={
            'symbol': symbol_clean,
            'period': period,
            'limit': limit
        }, proxies=get_proxies(), timeout=10)
        
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.warning(f"Binance 多空比获取失败: {e}")
    return None


# ==================== 订单簿深度分析 ====================

def analyze_orderbook_depth(orderbook, current_price, num_levels=50):
    """
    分析订单簿深度，生成"热力图"数据
    返回：买墙、卖墙、支撑位、阻力位
    """
    if not orderbook:
        return None, None, [], []
    
    bids = orderbook.get('bids', [])  # 买单 [[price, amount], ...]
    asks = orderbook.get('asks', [])  # 卖单 [[price, amount], ...]
    
    if not bids or not asks:
        return None, None, [], []
    
    # 价格范围 (当前价格 ±5%)
    price_range = current_price * 0.05
    price_min = current_price - price_range
    price_max = current_price + price_range
    
    # 创建价格区间
    price_levels = np.linspace(price_min, price_max, num_levels)
    level_width = (price_max - price_min) / num_levels
    
    # 买单深度 (绿色)
    bid_depth = np.zeros(num_levels)
    for price, amount in bids:
        if price_min <= price <= price_max:
            idx = int((price - price_min) / level_width)
            if 0 <= idx < num_levels:
                bid_depth[idx] += amount * price  # 以 USDT 计价
    
    # 卖单深度 (红色)
    ask_depth = np.zeros(num_levels)
    for price, amount in asks:
        if price_min <= price <= price_max:
            idx = int((price - price_min) / level_width)
            if 0 <= idx < num_levels:
                ask_depth[idx] += amount * price
    
    # 归一化
    max_depth = max(bid_depth.max(), ask_depth.max())
    if max_depth > 0:
        bid_depth = bid_depth / max_depth
        ask_depth = ask_depth / max_depth
    
    # 找买墙（支撑位）- 买单深度峰值
    supports = []
    for i in range(2, len(bid_depth) - 2):
        if bid_depth[i] > 0.3:  # 阈值
            is_peak = all(bid_depth[i] >= bid_depth[i+j] for j in range(-2, 3) if j != 0)
            if is_peak:
                price = price_levels[i]
                if price < current_price * 0.998:
                    supports.append((price, bid_depth[i]))
    
    # 找卖墙（阻力位）- 卖单深度峰值
    resistances = []
    for i in range(2, len(ask_depth) - 2):
        if ask_depth[i] > 0.3:
            is_peak = all(ask_depth[i] >= ask_depth[i+j] for j in range(-2, 3) if j != 0)
            if is_peak:
                price = price_levels[i]
                if price > current_price * 1.002:
                    resistances.append((price, ask_depth[i]))
    
    # 按深度排序，取前3
    supports = sorted(supports, key=lambda x: -x[1])[:3]
    resistances = sorted(resistances, key=lambda x: -x[1])[:3]
    
    return (bid_depth, ask_depth, price_levels, 
            [p for p, _ in supports], [p for p, _ in resistances])


def format_num(num, decimals=2):
    """格式化数字"""
    if abs(num) >= 1e9:
        return f"{num/1e9:.{decimals}f}B"
    elif abs(num) >= 1e6:
        return f"{num/1e6:.{decimals}f}M"
    elif abs(num) >= 1e3:
        return f"{num/1e3:.{decimals}f}K"
    return f"{num:.{decimals}f}"


# ==================== 图表生成 ====================

def generate_chart_v6(symbol, interval='15m', limit=200):
    """
    生成专业图表 v6
    - 数据源: CCXT (币安)
    - 主力资金: CryptoQuant API
    - 热力图: 订单簿深度（买卖墙）
    """
    symbol_clean = symbol.upper().replace('$', '').strip()
    base_coin = symbol_clean.replace('USDT', '')
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    logger.info(f"📊 生成图表 v6: {symbol_clean}")
    
    # 获取数据
    df = get_klines(symbol_clean, interval, limit)
    if df is None or df.empty:
        logger.error("❌ K线获取失败")
        return None
    
    ticker = get_ticker(symbol_clean)
    orderbook = get_orderbook(symbol_clean, 500)  # 获取更多深度
    funding = get_funding_rate(symbol_clean)
    taker_data = get_binance_taker_volume(symbol_clean)
    oi_data = get_binance_open_interest(symbol_clean)
    ls_ratio = get_binance_long_short_ratio(symbol_clean)
    
    try:
        plt.style.use('dark_background')
        configure_matplotlib_fonts()
        plt.rcParams['axes.unicode_minus'] = False
        
        fig = plt.figure(figsize=(20, 14), facecolor=COLORS['bg'])
        
        # 布局
        ax_depth = fig.add_axes([0.02, 0.28, 0.04, 0.62], facecolor=COLORS['bg'])
        ax_main = fig.add_axes([0.07, 0.28, 0.64, 0.62], facecolor=COLORS['bg'])
        ax_info = fig.add_axes([0.73, 0.28, 0.25, 0.62], facecolor=COLORS['panel'])
        ax_flow = fig.add_axes([0.02, 0.02, 0.96, 0.22], facecolor=COLORS['panel'])
        
        current_price = df['close'].iloc[-1]
        price_min = df['low'].min() * 0.998
        price_max = df['high'].max() * 1.002
        
        # ========== 订单簿深度热力图 ==========
        depth_result = analyze_orderbook_depth(orderbook, current_price, 60)
        
        if depth_result and depth_result[0] is not None:
            bid_depth, ask_depth, depth_levels, supports, resistances = depth_result
            
            # 绘制买单深度（绿色，左侧）
            for i, (depth, price) in enumerate(zip(bid_depth, depth_levels)):
                if depth > 0.05 and price_min <= price <= price_max:
                    bar_height = (price_max - price_min) / len(depth_levels) * 0.9
                    # 深度越大，颜色越深
                    alpha = min(0.9, 0.3 + depth * 0.6)
                    ax_depth.barh(price, depth, height=bar_height, 
                                 color=COLORS['up'], alpha=alpha)
            
            # 绘制卖单深度（红色，右侧用负值表示）
            for i, (depth, price) in enumerate(zip(ask_depth, depth_levels)):
                if depth > 0.05 and price_min <= price <= price_max:
                    bar_height = (price_max - price_min) / len(depth_levels) * 0.9
                    alpha = min(0.9, 0.3 + depth * 0.6)
                    ax_depth.barh(price, -depth, height=bar_height,
                                 color=COLORS['down'], alpha=alpha)
            
            ax_depth.set_ylim(price_min, price_max)
            ax_depth.set_xlim(-1.2, 1.2)
            ax_depth.axvline(x=0, color=COLORS['grid'], linewidth=0.5)
            ax_depth.axis('off')
        else:
            supports, resistances = [], []
            ax_depth.axis('off')
        
        # ========== K线图 + 买卖墙标注 ==========
        
        # 绘制支撑位（买墙）
        for sup in supports:
            if price_min <= sup <= price_max:
                ax_main.axhline(y=sup, color=COLORS['up'], linewidth=2, linestyle='-', alpha=0.6)
                ax_main.fill_between([0, len(df)], sup * 0.999, sup * 1.001,
                                    color=COLORS['up'], alpha=0.15)
        
        # 绘制阻力位（卖墙）
        for res in resistances:
            if price_min <= res <= price_max:
                ax_main.axhline(y=res, color=COLORS['down'], linewidth=2, linestyle='-', alpha=0.6)
                ax_main.fill_between([0, len(df)], res * 0.999, res * 1.001,
                                    color=COLORS['down'], alpha=0.15)
        
        # 绘制K线
        for i, (_, row) in enumerate(df.iterrows()):
            is_up = row['close'] >= row['open']
            color = COLORS['up'] if is_up else COLORS['down']
            ax_main.plot([i, i], [row['low'], row['high']], color=color, linewidth=0.8)
            
            body_bottom = min(row['open'], row['close'])
            body_height = max(abs(row['close'] - row['open']), (price_max - price_min) * 0.0003)
            rect = mpatches.Rectangle((i - 0.3, body_bottom), 0.6, body_height,
                                       facecolor=color, edgecolor=color, alpha=0.95)
            ax_main.add_patch(rect)
        
        # 当前价格线
        ax_main.axhline(y=current_price, color=COLORS['yellow'], linewidth=2, alpha=0.95)
        
        ax_main.set_xlim(-1, len(df) + 1)
        ax_main.set_ylim(price_min, price_max)
        ax_main.set_ylabel('价格 (USDT)', color=COLORS['text_dim'], fontsize=FONT['label'])
        ax_main.tick_params(colors=COLORS['text_dim'], labelsize=8)
        ax_main.grid(True, color=COLORS['grid'], alpha=0.3, axis='y')
        for spine in ax_main.spines.values():
            spine.set_visible(False)
        plt.setp(ax_main.get_xticklabels(), visible=False)
        
        # ========== 右侧数据面板 ==========
        ax_info.set_xlim(0, 1)
        ax_info.set_ylim(0, 1)
        ax_info.axis('off')
        
        y = 0.96
        lh = 0.042
        
        # 价格
        ax_info.text(0.5, y, f'${current_price:,.2f}', fontsize=18, fontweight='bold',
                    color=COLORS['yellow'], transform=ax_info.transAxes, ha='center')
        y -= 0.055
        
        if ticker:
            pct = ticker.get('percentage', 0)
            change_color = COLORS['up'] if pct >= 0 else COLORS['down']
            ax_info.text(0.5, y, f'{pct:+.2f}%', fontsize=12, fontweight='bold',
                        color=change_color, transform=ax_info.transAxes, ha='center')
        y -= 0.05
        
        ax_info.axhline(y=y, xmin=0.05, xmax=0.95, color=COLORS['grid'], linewidth=0.5)
        y -= 0.025
        
        # 买墙（支撑位）
        ax_info.text(0.5, y, '买墙 (支撑位)', fontsize=FONT['subtitle'], fontweight='bold',
                    color=COLORS['up'], transform=ax_info.transAxes, ha='center')
        y -= lh
        
        if supports:
            for i, sup in enumerate(supports[:3]):
                ax_info.text(0.08, y, f'S{i+1}:', fontsize=FONT['label'], color=COLORS['text_dim'],
                            transform=ax_info.transAxes)
                ax_info.text(0.92, y, f'${sup:,.0f}', fontsize=FONT['value'], fontweight='bold',
                            color=COLORS['up'], transform=ax_info.transAxes, ha='right')
                y -= lh
        else:
            ax_info.text(0.5, y, '无明显买墙', fontsize=FONT['small'],
                        color=COLORS['text_dim'], transform=ax_info.transAxes, ha='center')
            y -= lh
        
        y -= 0.015
        
        # 卖墙（阻力位）
        ax_info.text(0.5, y, '卖墙 (阻力位)', fontsize=FONT['subtitle'], fontweight='bold',
                    color=COLORS['down'], transform=ax_info.transAxes, ha='center')
        y -= lh
        
        if resistances:
            for i, res in enumerate(resistances[:3]):
                ax_info.text(0.08, y, f'R{i+1}:', fontsize=FONT['label'], color=COLORS['text_dim'],
                            transform=ax_info.transAxes)
                ax_info.text(0.92, y, f'${res:,.0f}', fontsize=FONT['value'], fontweight='bold',
                            color=COLORS['down'], transform=ax_info.transAxes, ha='right')
                y -= lh
        else:
            ax_info.text(0.5, y, '无明显卖墙', fontsize=FONT['small'],
                        color=COLORS['text_dim'], transform=ax_info.transAxes, ha='center')
            y -= lh
        
        y -= 0.02
        ax_info.axhline(y=y, xmin=0.05, xmax=0.95, color=COLORS['grid'], linewidth=0.5)
        y -= 0.025
        
        # 交易数据 (CCXT)
        ax_info.text(0.5, y, '交易数据 (Binance)', fontsize=FONT['subtitle'], fontweight='bold',
                    color=COLORS['blue'], transform=ax_info.transAxes, ha='center')
        y -= lh
        
        if ticker:
            ax_info.text(0.08, y, '24H成交额:', fontsize=FONT['label'], color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.92, y, format_num(ticker.get('quoteVolume', 0)),
                        fontsize=FONT['value'], color=COLORS['cyan'],
                        transform=ax_info.transAxes, ha='right')
            y -= lh
            
            ax_info.text(0.08, y, '24H最高:', fontsize=FONT['label'], color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.92, y, f"${ticker.get('high', 0):,.0f}",
                        fontsize=FONT['value'], color=COLORS['up'],
                        transform=ax_info.transAxes, ha='right')
            y -= lh
            
            ax_info.text(0.08, y, '24H最低:', fontsize=FONT['label'], color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.92, y, f"${ticker.get('low', 0):,.0f}",
                        fontsize=FONT['value'], color=COLORS['down'],
                        transform=ax_info.transAxes, ha='right')
            y -= lh
        
        if funding:
            rate = funding.get('fundingRate', 0)
            rate_pct = rate * 100 if rate else 0
            rate_color = COLORS['up'] if rate_pct >= 0 else COLORS['down']
            ax_info.text(0.08, y, '资金费率:', fontsize=FONT['label'], color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.92, y, f'{rate_pct:+.4f}%', fontsize=FONT['value'],
                        color=rate_color, transform=ax_info.transAxes, ha='right', fontweight='bold')
            y -= lh
        
        y -= 0.02
        ax_info.axhline(y=y, xmin=0.05, xmax=0.95, color=COLORS['grid'], linewidth=0.5)
        y -= 0.025
        
        # Binance 免费数据
        ax_info.text(0.5, y, '市场情绪 (Binance)', fontsize=FONT['subtitle'], fontweight='bold',
                    color=COLORS['purple'], transform=ax_info.transAxes, ha='center')
        y -= lh
        
        if oi_data:
            oi = float(oi_data.get('openInterest', 0))
            ax_info.text(0.08, y, '持仓量:', fontsize=FONT['label'], color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.92, y, format_num(oi),
                        fontsize=FONT['value'], color=COLORS['cyan'],
                        transform=ax_info.transAxes, ha='right')
            y -= lh
        
        if taker_data and len(taker_data) > 0:
            latest = taker_data[0]
            buy_ratio = float(latest.get('buyVol', 0)) / (float(latest.get('buyVol', 0)) + float(latest.get('sellVol', 1))) * 100
            ratio_color = COLORS['up'] if buy_ratio > 50 else COLORS['down']
            ax_info.text(0.08, y, 'Taker买入占比:', fontsize=FONT['label'], color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.92, y, f'{buy_ratio:.1f}%',
                        fontsize=FONT['value'], color=ratio_color,
                        transform=ax_info.transAxes, ha='right', fontweight='bold')
            y -= lh
        
        if ls_ratio and len(ls_ratio) > 0:
            latest = ls_ratio[0]
            long_ratio = float(latest.get('longAccount', 0.5)) * 100
            ratio_color = COLORS['up'] if long_ratio > 50 else COLORS['down']
            ax_info.text(0.08, y, '多头账户占比:', fontsize=FONT['label'], color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.92, y, f'{long_ratio:.1f}%',
                        fontsize=FONT['value'], color=ratio_color,
                        transform=ax_info.transAxes, ha='right', fontweight='bold')
        
        # ========== 底部：订单簿可视化 ==========
        ax_flow.set_xlim(0, 1)
        ax_flow.set_ylim(0, 1)
        ax_flow.axis('off')
        
        ax_flow.text(0.5, 0.92, '订单簿深度 (实时买卖墙)', fontsize=FONT['subtitle'], fontweight='bold',
                    color=COLORS['text'], transform=ax_flow.transAxes, ha='center')
        
        if orderbook:
            bids = orderbook.get('bids', [])[:15]
            asks = orderbook.get('asks', [])[:15]
            
            # 计算累计深度
            bid_cumsum = []
            ask_cumsum = []
            bid_total = 0
            ask_total = 0
            
            for price, amount in bids:
                bid_total += amount * price
                bid_cumsum.append((price, bid_total))
            
            for price, amount in asks:
                ask_total += amount * price
                ask_cumsum.append((price, ask_total))
            
            max_cumsum = max(bid_total, ask_total) if bid_total > 0 or ask_total > 0 else 1
            
            # 买单表格（左侧）
            ax_flow.text(0.22, 0.82, '买单 (Bids)', fontsize=FONT['label'], fontweight='bold',
                        color=COLORS['up'], transform=ax_flow.transAxes, ha='center')
            
            cols_bid = [0.06, 0.18, 0.30, 0.42]
            ax_flow.text(cols_bid[0], 0.76, '价格', fontsize=FONT['small'],
                        color=COLORS['text_dim'], transform=ax_flow.transAxes, ha='center')
            ax_flow.text(cols_bid[1], 0.76, '数量', fontsize=FONT['small'],
                        color=COLORS['text_dim'], transform=ax_flow.transAxes, ha='center')
            ax_flow.text(cols_bid[2], 0.76, '金额', fontsize=FONT['small'],
                        color=COLORS['text_dim'], transform=ax_flow.transAxes, ha='center')
            ax_flow.text(cols_bid[3], 0.76, '累计', fontsize=FONT['small'],
                        color=COLORS['text_dim'], transform=ax_flow.transAxes, ha='center')
            
            for i, ((price, cumsum), (p, amount)) in enumerate(zip(bid_cumsum[:10], bids[:10])):
                y_pos = 0.68 - i * 0.065
                ax_flow.text(cols_bid[0], y_pos, f'${price:,.0f}', fontsize=FONT['small'],
                            color=COLORS['up'], transform=ax_flow.transAxes, ha='center')
                ax_flow.text(cols_bid[1], y_pos, f'{amount:.4f}', fontsize=FONT['small'],
                            color=COLORS['text'], transform=ax_flow.transAxes, ha='center')
                ax_flow.text(cols_bid[2], y_pos, format_num(amount * price), fontsize=FONT['small'],
                            color=COLORS['text'], transform=ax_flow.transAxes, ha='center')
                ax_flow.text(cols_bid[3], y_pos, format_num(cumsum), fontsize=FONT['small'],
                            color=COLORS['cyan'], transform=ax_flow.transAxes, ha='center')
            
            # 卖单表格（右侧）
            ax_flow.text(0.72, 0.82, '卖单 (Asks)', fontsize=FONT['label'], fontweight='bold',
                        color=COLORS['down'], transform=ax_flow.transAxes, ha='center')
            
            cols_ask = [0.56, 0.68, 0.80, 0.92]
            ax_flow.text(cols_ask[0], 0.76, '价格', fontsize=FONT['small'],
                        color=COLORS['text_dim'], transform=ax_flow.transAxes, ha='center')
            ax_flow.text(cols_ask[1], 0.76, '数量', fontsize=FONT['small'],
                        color=COLORS['text_dim'], transform=ax_flow.transAxes, ha='center')
            ax_flow.text(cols_ask[2], 0.76, '金额', fontsize=FONT['small'],
                        color=COLORS['text_dim'], transform=ax_flow.transAxes, ha='center')
            ax_flow.text(cols_ask[3], 0.76, '累计', fontsize=FONT['small'],
                        color=COLORS['text_dim'], transform=ax_flow.transAxes, ha='center')
            
            for i, ((price, cumsum), (p, amount)) in enumerate(zip(ask_cumsum[:10], asks[:10])):
                y_pos = 0.68 - i * 0.065
                ax_flow.text(cols_ask[0], y_pos, f'${price:,.0f}', fontsize=FONT['small'],
                            color=COLORS['down'], transform=ax_flow.transAxes, ha='center')
                ax_flow.text(cols_ask[1], y_pos, f'{amount:.4f}', fontsize=FONT['small'],
                            color=COLORS['text'], transform=ax_flow.transAxes, ha='center')
                ax_flow.text(cols_ask[2], y_pos, format_num(amount * price), fontsize=FONT['small'],
                            color=COLORS['text'], transform=ax_flow.transAxes, ha='center')
                ax_flow.text(cols_ask[3], y_pos, format_num(cumsum), fontsize=FONT['small'],
                            color=COLORS['orange'], transform=ax_flow.transAxes, ha='center')
            
            # 总深度对比
            ax_flow.axvline(x=0.5, color=COLORS['grid'], linewidth=1, alpha=0.5)
            
            bid_pct = bid_total / (bid_total + ask_total) * 100 if (bid_total + ask_total) > 0 else 50
            ax_flow.text(0.25, 0.03, f'买方深度: {format_num(bid_total)} ({bid_pct:.1f}%)',
                        fontsize=FONT['label'], color=COLORS['up'],
                        transform=ax_flow.transAxes, ha='center', fontweight='bold')
            ax_flow.text(0.75, 0.03, f'卖方深度: {format_num(ask_total)} ({100-bid_pct:.1f}%)',
                        fontsize=FONT['label'], color=COLORS['down'],
                        transform=ax_flow.transAxes, ha='center', fontweight='bold')
        
        # ========== 标题 ==========
        interval_map = {'5m': '5分钟', '15m': '15分钟', '1h': '1小时', '4h': '4小时'}
        fig.text(0.02, 0.96, f"{symbol_clean}  ·  {interval_map.get(interval, interval)}",
                fontsize=FONT['title'], fontweight='bold', color=COLORS['text'])
        
        # 图例
        fig.text(0.25, 0.945, '买单深度', fontsize=FONT['small'], color=COLORS['up'])
        fig.text(0.32, 0.945, '|', fontsize=FONT['small'], color=COLORS['grid'])
        fig.text(0.34, 0.945, '卖单深度', fontsize=FONT['small'], color=COLORS['down'])
        
        # 数据源标注
        fig.text(0.98, 0.96, 'CCXT + Binance API (Free)', fontsize=FONT['small'],
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
        logger.info(f"✅ 图表 v6 生成成功: {symbol_clean} ({size_kb:.1f} KB)")
        
        return image_data
        
    except Exception as e:
        logger.exception(f"❌ 图表生成失败: {e}")
        return None


def test_chart_v6(symbol='BTC'):
    """测试图表"""
    import os
    
    logger.info(f"🧪 测试图表 v6: {symbol}")
    
    image_data = generate_chart_v6(symbol, interval='15m', limit=200)
    
    if image_data:
        os.makedirs('output', exist_ok=True)
        output_path = f'output/chart_v6_{symbol}.png'
        with open(output_path, 'wb') as f:
            f.write(image_data)
        logger.info(f"✅ 图片已保存: {output_path}")
        return True
    return False


if __name__ == '__main__':
    test_chart_v6('BTC')
    test_chart_v6('ETH')
