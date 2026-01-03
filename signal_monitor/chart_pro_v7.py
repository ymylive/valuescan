"""
专业图表生成模块 v7
- 订单簿深度模拟清算热力图
- 根据峰值标注主力关键位
- 资金流入流出可视化
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
    logger.warning("CCXT 未安装")

# ==================== 配置 ====================
BINANCE_FUTURES_URL = "https://fapi.binance.com"

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

FONT = {'title': 14, 'subtitle': 11, 'label': 9, 'value': 10, 'small': 8}


def get_proxies():
    proxies = {}
    try:
        from config import SOCKS5_PROXY
        if SOCKS5_PROXY:
            proxies = {'http': SOCKS5_PROXY, 'https': SOCKS5_PROXY}
    except:
        pass
    return proxies


# ==================== CCXT 数据获取 ====================

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
    exchange = get_exchange()
    if not exchange:
        return None
    
    base = symbol.upper().replace('$', '').replace('USDT', '').strip()
    ccxt_symbol = f"{base}/USDT"
    
    try:
        return exchange.fetch_ticker(ccxt_symbol)
    except Exception as e:
        logger.warning(f"Ticker获取失败: {e}")
    return None


def get_orderbook(symbol, limit=500):
    """获取订单簿深度"""
    exchange = get_exchange()
    if not exchange:
        return None
    
    base = symbol.upper().replace('$', '').replace('USDT', '').strip()
    ccxt_symbol = f"{base}/USDT"
    
    try:
        return exchange.fetch_order_book(ccxt_symbol, limit=limit)
    except Exception as e:
        logger.warning(f"订单簿获取失败: {e}")
    return None


def get_funding_rate(symbol):
    exchange = get_exchange()
    if not exchange:
        return None
    
    base = symbol.upper().replace('$', '').replace('USDT', '').strip()
    ccxt_symbol = f"{base}/USDT"
    
    try:
        return exchange.fetch_funding_rate(ccxt_symbol)
    except Exception as e:
        logger.warning(f"资金费率获取失败: {e}")
    return None


# ==================== Binance 数据 API ====================

def get_taker_volume(symbol, period='5m', limit=50):
    """获取 Taker 买卖量（资金流入流出）"""
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


def get_open_interest(symbol):
    """获取持仓量"""
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
        logger.warning(f"OI获取失败: {e}")
    return None


def get_long_short_ratio(symbol, period='5m', limit=50):
    """获取多空账户比"""
    symbol_clean = symbol.upper().replace('$', '').strip()
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    try:
        url = f"{BINANCE_FUTURES_URL}/futures/data/globalLongShortAccountRatio"
        response = requests.get(url, params={
            'symbol': symbol_clean, 'period': period, 'limit': limit
        }, proxies=get_proxies(), timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.warning(f"多空比获取失败: {e}")
    return None


# ==================== 核心算法 ====================

def analyze_orderbook_heatmap(orderbook, current_price, num_levels=80):
    """
    分析订单簿深度，模拟清算热力图
    找到主力关键位（买墙/卖墙峰值）
    """
    if not orderbook:
        return None
    
    bids = orderbook.get('bids', [])
    asks = orderbook.get('asks', [])
    
    if not bids or not asks:
        return None
    
    # 价格范围 (当前价格 ±6%)
    price_range = current_price * 0.06
    price_min = current_price - price_range
    price_max = current_price + price_range
    level_width = (price_max - price_min) / num_levels
    
    # 创建热力图数据
    heatmap = np.zeros(num_levels)
    price_levels = np.linspace(price_min, price_max, num_levels)
    
    # 买单深度累积
    for price, amount in bids:
        if price_min <= price <= price_max:
            idx = int((price - price_min) / level_width)
            if 0 <= idx < num_levels:
                heatmap[idx] += amount * price  # USDT 计价
    
    # 卖单深度累积
    for price, amount in asks:
        if price_min <= price <= price_max:
            idx = int((price - price_min) / level_width)
            if 0 <= idx < num_levels:
                heatmap[idx] += amount * price
    
    # 高斯平滑
    from scipy.ndimage import gaussian_filter1d
    heatmap_smooth = gaussian_filter1d(heatmap, sigma=2)
    
    # 归一化
    if heatmap_smooth.max() > 0:
        heatmap_norm = heatmap_smooth / heatmap_smooth.max()
    else:
        heatmap_norm = heatmap_smooth
    
    # 找主力关键位（峰值）
    key_levels = []
    for i in range(3, len(heatmap_norm) - 3):
        if heatmap_norm[i] > 0.25:  # 阈值
            is_peak = all(heatmap_norm[i] >= heatmap_norm[i+j] for j in range(-3, 4) if j != 0)
            if is_peak:
                price = price_levels[i]
                strength = heatmap_norm[i]
                
                # 判断是支撑还是阻力
                if price < current_price * 0.998:
                    level_type = 'support'
                elif price > current_price * 1.002:
                    level_type = 'resistance'
                else:
                    level_type = 'current'
                
                key_levels.append({
                    'price': price,
                    'strength': strength,
                    'type': level_type,
                    'value': heatmap[i]  # 原始值（USDT）
                })
    
    # 按强度排序
    key_levels = sorted(key_levels, key=lambda x: -x['strength'])
    
    # 分类
    supports = [l for l in key_levels if l['type'] == 'support'][:3]
    resistances = [l for l in key_levels if l['type'] == 'resistance'][:3]
    
    return {
        'heatmap': heatmap_norm,
        'price_levels': price_levels,
        'supports': supports,
        'resistances': resistances,
        'raw_heatmap': heatmap
    }


def calculate_fund_flow(taker_data):
    """计算资金流入流出"""
    if not taker_data:
        return None
    
    flows = []
    for item in taker_data:
        buy_vol = float(item.get('buyVol', 0))
        sell_vol = float(item.get('sellVol', 0))
        timestamp = int(item.get('timestamp', 0))
        
        inflow = buy_vol  # 主动买入 = 资金流入
        outflow = sell_vol  # 主动卖出 = 资金流出
        net = inflow - outflow
        
        flows.append({
            'timestamp': timestamp,
            'inflow': inflow,
            'outflow': outflow,
            'net': net,
            'ratio': buy_vol / (buy_vol + sell_vol) * 100 if (buy_vol + sell_vol) > 0 else 50
        })
    
    return flows


def format_num(num, decimals=2):
    if abs(num) >= 1e9:
        return f"{num/1e9:.{decimals}f}B"
    elif abs(num) >= 1e6:
        return f"{num/1e6:.{decimals}f}M"
    elif abs(num) >= 1e3:
        return f"{num/1e3:.{decimals}f}K"
    return f"{num:.{decimals}f}"


# ==================== 图表生成 ====================

def generate_chart_v7(symbol, interval='15m', limit=200):
    """生成专业图表 v7"""
    symbol_clean = symbol.upper().replace('$', '').strip()
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    logger.info(f"📊 生成图表 v7: {symbol_clean}")
    
    # 获取数据
    df = get_klines(symbol_clean, interval, limit)
    if df is None or df.empty:
        logger.error("❌ K线获取失败")
        return None
    
    ticker = get_ticker(symbol_clean)
    orderbook = get_orderbook(symbol_clean, 1000)
    funding = get_funding_rate(symbol_clean)
    taker_data = get_taker_volume(symbol_clean, '5m', 50)
    oi_data = get_open_interest(symbol_clean)
    ls_ratio = get_long_short_ratio(symbol_clean, '5m', 50)
    
    try:
        plt.style.use('dark_background')
        configure_matplotlib_fonts()
        plt.rcParams['axes.unicode_minus'] = False
        
        fig = plt.figure(figsize=(20, 16), facecolor=COLORS['bg'])
        
        # 布局：热力图 | K线 | 信息面板 | 资金流
        ax_heat = fig.add_axes([0.02, 0.35, 0.04, 0.55], facecolor=COLORS['bg'])
        ax_main = fig.add_axes([0.07, 0.35, 0.62, 0.55], facecolor=COLORS['bg'])
        ax_info = fig.add_axes([0.71, 0.35, 0.27, 0.55], facecolor=COLORS['panel'])
        ax_flow = fig.add_axes([0.02, 0.04, 0.96, 0.28], facecolor=COLORS['panel'])
        
        current_price = df['close'].iloc[-1]
        price_min = df['low'].min() * 0.995
        price_max = df['high'].max() * 1.005
        
        # ========== 订单簿深度热力图 ==========
        depth_data = analyze_orderbook_heatmap(orderbook, current_price, 100)
        
        # 热力图颜色
        cmap = LinearSegmentedColormap.from_list('depth', [
            '#0b0e11', '#1a237e', '#283593', '#3949ab',
            '#5c6bc0', '#7986cb', '#9fa8da', '#c5cae9',
            '#e8eaf6', '#fff59d', '#ffee58', '#ffeb3b',
            '#ffc107', '#ff9800', '#ff5722', '#f44336'
        ])
        
        if depth_data:
            heatmap = depth_data['heatmap']
            heat_levels = depth_data['price_levels']
            supports = depth_data['supports']
            resistances = depth_data['resistances']
            
            # 绘制热力图
            for i, (intensity, price) in enumerate(zip(heatmap, heat_levels)):
                if intensity > 0.05 and price_min <= price <= price_max:
                    bar_height = (price_max - price_min) / len(heat_levels) * 0.95
                    ax_heat.barh(price, intensity, height=bar_height, 
                                color=cmap(intensity), alpha=0.9)
            
            ax_heat.set_ylim(price_min, price_max)
            ax_heat.set_xlim(0, 1.2)
            ax_heat.axis('off')
        else:
            supports, resistances = [], []
            ax_heat.axis('off')
        
        # ========== K线图 + 主力关键位标注 ==========
        
        # 绘制支撑位（主力买墙）
        for i, sup in enumerate(supports[:3]):
            price = sup['price']
            strength = sup['strength']
            if price_min <= price <= price_max:
                # 线宽根据强度变化
                lw = 1 + strength * 2
                ax_main.axhline(y=price, color=COLORS['up'], linewidth=lw, 
                               linestyle='-', alpha=0.7)
                # 标注
                ax_main.text(len(df) + 2, price, f"S{i+1} ${price:,.0f}", 
                            fontsize=8, color=COLORS['up'], va='center',
                            bbox=dict(boxstyle='round,pad=0.2', facecolor=COLORS['bg'], 
                                     edgecolor=COLORS['up'], alpha=0.8))
        
        # 绘制阻力位（主力卖墙）
        for i, res in enumerate(resistances[:3]):
            price = res['price']
            strength = res['strength']
            if price_min <= price <= price_max:
                lw = 1 + strength * 2
                ax_main.axhline(y=price, color=COLORS['down'], linewidth=lw,
                               linestyle='-', alpha=0.7)
                ax_main.text(len(df) + 2, price, f"R{i+1} ${price:,.0f}",
                            fontsize=8, color=COLORS['down'], va='center',
                            bbox=dict(boxstyle='round,pad=0.2', facecolor=COLORS['bg'],
                                     edgecolor=COLORS['down'], alpha=0.8))
        
        # 绘制K线
        for i, (_, row) in enumerate(df.iterrows()):
            is_up = row['close'] >= row['open']
            color = COLORS['up'] if is_up else COLORS['down']
            ax_main.plot([i, i], [row['low'], row['high']], color=color, linewidth=0.8)
            
            body_bottom = min(row['open'], row['close'])
            body_height = max(abs(row['close'] - row['open']), (price_max - price_min) * 0.0003)
            rect = mpatches.Rectangle((i - 0.35, body_bottom), 0.7, body_height,
                                       facecolor=color, edgecolor=color, alpha=0.95)
            ax_main.add_patch(rect)
        
        # 当前价格线
        ax_main.axhline(y=current_price, color=COLORS['yellow'], linewidth=2.5, alpha=0.95)
        ax_main.text(len(df) + 2, current_price, f"${current_price:,.2f}",
                    fontsize=9, fontweight='bold', color=COLORS['bg'], va='center',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['yellow']))
        
        ax_main.set_xlim(-1, len(df) + 15)
        ax_main.set_ylim(price_min, price_max)
        ax_main.set_ylabel('价格 (USDT)', color=COLORS['text_dim'], fontsize=FONT['label'])
        ax_main.tick_params(colors=COLORS['text_dim'], labelsize=8)
        ax_main.grid(True, color=COLORS['grid'], alpha=0.3, axis='y')
        for spine in ax_main.spines.values():
            spine.set_visible(False)
        plt.setp(ax_main.get_xticklabels(), visible=False)
        
        # ========== 右侧信息面板 ==========
        ax_info.set_xlim(0, 1)
        ax_info.set_ylim(0, 1)
        ax_info.axis('off')
        
        y = 0.96
        lh = 0.038
        
        # 价格
        ax_info.text(0.5, y, f'${current_price:,.2f}', fontsize=20, fontweight='bold',
                    color=COLORS['yellow'], transform=ax_info.transAxes, ha='center')
        y -= 0.05
        
        if ticker:
            pct = ticker.get('percentage', 0)
            change_color = COLORS['up'] if pct >= 0 else COLORS['down']
            ax_info.text(0.5, y, f'{pct:+.2f}%', fontsize=14, fontweight='bold',
                        color=change_color, transform=ax_info.transAxes, ha='center')
        y -= 0.045
        
        ax_info.axhline(y=y, xmin=0.05, xmax=0.95, color=COLORS['grid'], linewidth=0.5)
        y -= 0.025
        
        # 主力关键位
        ax_info.text(0.5, y, '主力关键位 (订单簿峰值)', fontsize=FONT['subtitle'], fontweight='bold',
                    color=COLORS['cyan'], transform=ax_info.transAxes, ha='center')
        y -= lh
        
        ax_info.text(0.5, y, '支撑位 (买墙)', fontsize=FONT['small'], 
                    color=COLORS['up'], transform=ax_info.transAxes, ha='center')
        y -= lh * 0.8
        
        for i, sup in enumerate(supports[:3]):
            ax_info.text(0.08, y, f'S{i+1}:', fontsize=FONT['label'], color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.45, y, f'${sup["price"]:,.0f}', fontsize=FONT['value'], fontweight='bold',
                        color=COLORS['up'], transform=ax_info.transAxes, ha='right')
            ax_info.text(0.92, y, f'{format_num(sup["value"])}', fontsize=FONT['small'],
                        color=COLORS['text_dim'], transform=ax_info.transAxes, ha='right')
            y -= lh * 0.8
        
        if not supports:
            ax_info.text(0.5, y, '无明显买墙', fontsize=FONT['small'],
                        color=COLORS['text_dim'], transform=ax_info.transAxes, ha='center')
            y -= lh * 0.8
        
        y -= 0.01
        ax_info.text(0.5, y, '阻力位 (卖墙)', fontsize=FONT['small'],
                    color=COLORS['down'], transform=ax_info.transAxes, ha='center')
        y -= lh * 0.8
        
        for i, res in enumerate(resistances[:3]):
            ax_info.text(0.08, y, f'R{i+1}:', fontsize=FONT['label'], color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.45, y, f'${res["price"]:,.0f}', fontsize=FONT['value'], fontweight='bold',
                        color=COLORS['down'], transform=ax_info.transAxes, ha='right')
            ax_info.text(0.92, y, f'{format_num(res["value"])}', fontsize=FONT['small'],
                        color=COLORS['text_dim'], transform=ax_info.transAxes, ha='right')
            y -= lh * 0.8
        
        if not resistances:
            ax_info.text(0.5, y, '无明显卖墙', fontsize=FONT['small'],
                        color=COLORS['text_dim'], transform=ax_info.transAxes, ha='center')
            y -= lh * 0.8
        
        y -= 0.02
        ax_info.axhline(y=y, xmin=0.05, xmax=0.95, color=COLORS['grid'], linewidth=0.5)
        y -= 0.025
        
        # 市场数据
        ax_info.text(0.5, y, '市场数据', fontsize=FONT['subtitle'], fontweight='bold',
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
        
        if oi_data:
            oi = float(oi_data.get('openInterest', 0))
            ax_info.text(0.08, y, '持仓量:', fontsize=FONT['label'], color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.92, y, format_num(oi),
                        fontsize=FONT['value'], color=COLORS['purple'],
                        transform=ax_info.transAxes, ha='right')
            y -= lh
        
        if ls_ratio and len(ls_ratio) > 0:
            latest = ls_ratio[0]
            long_ratio = float(latest.get('longAccount', 0.5)) * 100
            ratio_color = COLORS['up'] if long_ratio > 50 else COLORS['down']
            ax_info.text(0.08, y, '多头账户:', fontsize=FONT['label'], color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.92, y, f'{long_ratio:.1f}%',
                        fontsize=FONT['value'], color=ratio_color,
                        transform=ax_info.transAxes, ha='right', fontweight='bold')
        
        # ========== 底部：资金流入流出 ==========
        ax_flow.set_xlim(0, 1)
        ax_flow.set_ylim(0, 1)
        ax_flow.axis('off')
        
        ax_flow.text(0.5, 0.95, '资金流入/流出 (Taker 买卖量)', fontsize=FONT['subtitle'], fontweight='bold',
                    color=COLORS['text'], transform=ax_flow.transAxes, ha='center')
        
        fund_flows = calculate_fund_flow(taker_data)
        
        if fund_flows and len(fund_flows) > 0:
            # 取最近的数据
            recent_flows = fund_flows[:20]
            
            # 计算汇总
            total_inflow = sum(f['inflow'] for f in recent_flows)
            total_outflow = sum(f['outflow'] for f in recent_flows)
            net_flow = total_inflow - total_outflow
            inflow_pct = total_inflow / (total_inflow + total_outflow) * 100 if (total_inflow + total_outflow) > 0 else 50
            
            # 左侧：汇总数据
            ax_flow.text(0.15, 0.82, '资金汇总 (近期)', fontsize=FONT['label'], fontweight='bold',
                        color=COLORS['text'], transform=ax_flow.transAxes, ha='center')
            
            ax_flow.text(0.05, 0.70, '流入:', fontsize=FONT['label'], color=COLORS['text_dim'],
                        transform=ax_flow.transAxes)
            ax_flow.text(0.25, 0.70, format_num(total_inflow), fontsize=FONT['value'], fontweight='bold',
                        color=COLORS['up'], transform=ax_flow.transAxes, ha='right')
            
            ax_flow.text(0.05, 0.58, '流出:', fontsize=FONT['label'], color=COLORS['text_dim'],
                        transform=ax_flow.transAxes)
            ax_flow.text(0.25, 0.58, format_num(total_outflow), fontsize=FONT['value'], fontweight='bold',
                        color=COLORS['down'], transform=ax_flow.transAxes, ha='right')
            
            ax_flow.text(0.05, 0.46, '净流入:', fontsize=FONT['label'], color=COLORS['text_dim'],
                        transform=ax_flow.transAxes)
            net_color = COLORS['up'] if net_flow >= 0 else COLORS['down']
            ax_flow.text(0.25, 0.46, format_num(net_flow), fontsize=FONT['value'], fontweight='bold',
                        color=net_color, transform=ax_flow.transAxes, ha='right')
            
            # 流入占比进度条
            ax_flow.text(0.05, 0.32, '流入占比:', fontsize=FONT['small'], color=COLORS['text_dim'],
                        transform=ax_flow.transAxes)
            bar_left = 0.05
            bar_width = 0.2
            ax_flow.barh(0.24, inflow_pct / 100 * bar_width, height=0.06, left=bar_left,
                        color=COLORS['up'], alpha=0.8, transform=ax_flow.transAxes)
            ax_flow.barh(0.24, (1 - inflow_pct / 100) * bar_width, height=0.06,
                        left=bar_left + inflow_pct / 100 * bar_width,
                        color=COLORS['down'], alpha=0.8, transform=ax_flow.transAxes)
            ax_flow.text(0.26, 0.24, f'{inflow_pct:.1f}%', fontsize=FONT['small'],
                        color=COLORS['up'] if inflow_pct > 50 else COLORS['down'],
                        transform=ax_flow.transAxes, va='center')
            
            # 右侧：柱状图 (资金流历史)
            ax_flow.text(0.60, 0.82, '资金流历史', fontsize=FONT['label'], fontweight='bold',
                        color=COLORS['text'], transform=ax_flow.transAxes, ha='center')
            
            # 绘制柱状图
            bar_area_left = 0.35
            bar_area_width = 0.60
            bar_area_bottom = 0.12
            bar_area_height = 0.60
            
            n_bars = min(len(recent_flows), 15)
            bar_width_each = bar_area_width / n_bars * 0.8
            bar_gap = bar_area_width / n_bars * 0.2
            
            max_val = max(max(f['inflow'] for f in recent_flows[:n_bars]),
                         max(f['outflow'] for f in recent_flows[:n_bars]))
            
            for i, flow in enumerate(recent_flows[:n_bars]):
                x = bar_area_left + i * (bar_width_each + bar_gap)
                
                # 流入（向上）
                inflow_height = (flow['inflow'] / max_val) * bar_area_height * 0.45 if max_val > 0 else 0
                ax_flow.bar(x + bar_width_each/2, inflow_height, width=bar_width_each,
                           bottom=bar_area_bottom + bar_area_height * 0.5,
                           color=COLORS['up'], alpha=0.8, transform=ax_flow.transAxes)
                
                # 流出（向下）
                outflow_height = (flow['outflow'] / max_val) * bar_area_height * 0.45 if max_val > 0 else 0
                ax_flow.bar(x + bar_width_each/2, -outflow_height, width=bar_width_each,
                           bottom=bar_area_bottom + bar_area_height * 0.5,
                           color=COLORS['down'], alpha=0.8, transform=ax_flow.transAxes)
            
            # 中线
            ax_flow.plot([bar_area_left, bar_area_left + bar_area_width],
                        [bar_area_bottom + bar_area_height * 0.5, bar_area_bottom + bar_area_height * 0.5],
                        color=COLORS['grid'], linewidth=1, transform=ax_flow.transAxes)
            
            # 图例
            ax_flow.text(0.35, 0.05, '流入', fontsize=FONT['small'], color=COLORS['up'],
                        transform=ax_flow.transAxes)
            ax_flow.text(0.45, 0.05, '|', fontsize=FONT['small'], color=COLORS['grid'],
                        transform=ax_flow.transAxes)
            ax_flow.text(0.48, 0.05, '流出', fontsize=FONT['small'], color=COLORS['down'],
                        transform=ax_flow.transAxes)
            ax_flow.text(0.85, 0.05, '← 新   旧 →', fontsize=FONT['small'], color=COLORS['text_dim'],
                        transform=ax_flow.transAxes, ha='right')
        
        # ========== 标题 ==========
        interval_map = {'5m': '5分钟', '15m': '15分钟', '1h': '1小时', '4h': '4小时'}
        fig.text(0.02, 0.96, f"{symbol_clean}  ·  {interval_map.get(interval, interval)}",
                fontsize=FONT['title'], fontweight='bold', color=COLORS['text'])
        
        # 热力图图例
        gradient = np.linspace(0, 1, 100).reshape(1, -1)
        ax_legend = fig.add_axes([0.25, 0.935, 0.10, 0.012])
        ax_legend.imshow(gradient, aspect='auto', cmap=cmap)
        ax_legend.set_xticks([0, 99])
        ax_legend.set_xticklabels(['低', '高'], fontsize=7, color=COLORS['text_dim'])
        ax_legend.set_yticks([])
        ax_legend.set_title('订单簿深度', fontsize=FONT['small'], color=COLORS['text_dim'], pad=2)
        for spine in ax_legend.spines.values():
            spine.set_visible(False)
        
        # 数据源
        fig.text(0.98, 0.96, 'CCXT + Binance API (Free)', fontsize=FONT['small'],
                color=COLORS['text_dim'], ha='right')
        
        # 水印
        fig.text(0.45, 0.55, 'NOFX', fontsize=30, color=COLORS['yellow'],
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
        logger.info(f"✅ 图表 v7 生成成功: {symbol_clean} ({size_kb:.1f} KB)")
        
        return image_data
        
    except Exception as e:
        logger.exception(f"❌ 图表生成失败: {e}")
        return None


def test_chart_v7(symbol='BTC'):
    import os
    logger.info(f"🧪 测试图表 v7: {symbol}")
    
    image_data = generate_chart_v7(symbol, interval='15m', limit=200)
    
    if image_data:
        os.makedirs('output', exist_ok=True)
        output_path = f'output/chart_v7_{symbol}.png'
        with open(output_path, 'wb') as f:
            f.write(image_data)
        logger.info(f"✅ 图片已保存: {output_path}")
        return True
    return False


if __name__ == '__main__':
    test_chart_v7('BTC')
    test_chart_v7('ETH')
