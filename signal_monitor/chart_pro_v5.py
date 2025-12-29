"""
专业图表生成模块 v5
数据源：
- CCXT: 交易所K线、订单簿、资金费率
- CoinGecko: 市场数据、资金流向
- Binance Futures: Taker买卖数据
"""

import io
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

try:
    from pycoingecko import CoinGeckoAPI
    COINGECKO_AVAILABLE = True
except ImportError:
    COINGECKO_AVAILABLE = False
    logger.warning("PyCoingecko 未安装")

# ==================== 配色方案 ====================
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

# 字体配置
FONT = {'title': 14, 'subtitle': 11, 'label': 9, 'value': 10, 'small': 8}

# 币种ID映射 (CoinGecko)
COINGECKO_IDS = {
    'BTC': 'bitcoin', 'ETH': 'ethereum', 'BNB': 'binancecoin',
    'SOL': 'solana', 'XRP': 'ripple', 'DOGE': 'dogecoin',
    'ADA': 'cardano', 'AVAX': 'avalanche-2', 'DOT': 'polkadot',
    'MATIC': 'matic-network', 'LINK': 'chainlink', 'UNI': 'uniswap',
    'ATOM': 'cosmos', 'LTC': 'litecoin', 'ETC': 'ethereum-classic',
    'FIL': 'filecoin', 'APT': 'aptos', 'ARB': 'arbitrum',
    'OP': 'optimism', 'INJ': 'injective-protocol', 'SUI': 'sui',
    'NEAR': 'near', 'ICP': 'internet-computer', 'TRX': 'tron',
}


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

def get_ccxt_exchange(exchange_id='binance'):
    """获取 CCXT 交易所实例"""
    if not CCXT_AVAILABLE:
        return None
    
    try:
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        
        # 配置代理
        proxies = get_proxies()
        if proxies:
            exchange.proxies = proxies
        
        return exchange
    except Exception as e:
        logger.warning(f"CCXT 交易所初始化失败: {e}")
    return None


def get_ccxt_ohlcv(symbol, timeframe='15m', limit=200):
    """使用 CCXT 获取 K线数据"""
    exchange = get_ccxt_exchange('binance')
    if not exchange:
        return None
    
    symbol_clean = symbol.upper().replace('$', '').strip()
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    ccxt_symbol = f"{symbol_clean.replace('USDT', '')}/USDT"
    
    try:
        ohlcv = exchange.fetch_ohlcv(ccxt_symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        logger.warning(f"CCXT K线获取失败: {e}")
    return None


def get_ccxt_ticker(symbol):
    """使用 CCXT 获取 Ticker 数据"""
    exchange = get_ccxt_exchange('binance')
    if not exchange:
        return None
    
    symbol_clean = symbol.upper().replace('$', '').strip()
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    ccxt_symbol = f"{symbol_clean.replace('USDT', '')}/USDT"
    
    try:
        ticker = exchange.fetch_ticker(ccxt_symbol)
        return ticker
    except Exception as e:
        logger.warning(f"CCXT Ticker 获取失败: {e}")
    return None


def get_ccxt_funding_rate(symbol):
    """使用 CCXT 获取资金费率"""
    exchange = get_ccxt_exchange('binance')
    if not exchange:
        return None
    
    symbol_clean = symbol.upper().replace('$', '').strip()
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    ccxt_symbol = f"{symbol_clean.replace('USDT', '')}/USDT"
    
    try:
        funding = exchange.fetch_funding_rate(ccxt_symbol)
        return funding
    except Exception as e:
        logger.warning(f"CCXT 资金费率获取失败: {e}")
    return None


def get_ccxt_orderbook(symbol, limit=20):
    """使用 CCXT 获取订单簿"""
    exchange = get_ccxt_exchange('binance')
    if not exchange:
        return None
    
    symbol_clean = symbol.upper().replace('$', '').strip()
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    ccxt_symbol = f"{symbol_clean.replace('USDT', '')}/USDT"
    
    try:
        orderbook = exchange.fetch_order_book(ccxt_symbol, limit=limit)
        return orderbook
    except Exception as e:
        logger.warning(f"CCXT 订单簿获取失败: {e}")
    return None


# ==================== CoinGecko 数据获取 ====================

def get_coingecko_market_data(coin_id):
    """使用 CoinGecko 获取市场数据"""
    if not COINGECKO_AVAILABLE:
        return None
    
    try:
        cg = CoinGeckoAPI()
        data = cg.get_coin_by_id(
            coin_id,
            localization=False,
            tickers=False,
            market_data=True,
            community_data=False,
            developer_data=False
        )
        return data.get('market_data', {})
    except Exception as e:
        logger.warning(f"CoinGecko 数据获取失败: {e}")
    return None


def get_coingecko_ohlc(coin_id, days=7):
    """使用 CoinGecko 获取 OHLC 数据"""
    if not COINGECKO_AVAILABLE:
        return None
    
    try:
        cg = CoinGeckoAPI()
        ohlc = cg.get_coin_ohlc_by_id(coin_id, vs_currency='usd', days=days)
        if ohlc:
            df = pd.DataFrame(ohlc, columns=['timestamp', 'open', 'high', 'low', 'close'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
    except Exception as e:
        logger.warning(f"CoinGecko OHLC 获取失败: {e}")
    return None


# ==================== 清算热力图算法 ====================

def calculate_liquidation_heatmap(df, current_price):
    """计算清算热力图和支撑/阻力位"""
    price_range = df['high'].max() - df['low'].min()
    price_min = current_price - price_range * 0.6
    price_max = current_price + price_range * 0.6
    
    num_levels = 100
    price_levels = np.linspace(price_min, price_max, num_levels)
    heatmap = np.zeros(num_levels)
    
    # 杠杆清算配置
    leverage_configs = [
        (125, 0.008, 1.0), (100, 0.010, 0.95), (75, 0.013, 0.90),
        (50, 0.020, 0.85), (25, 0.040, 0.70), (20, 0.050, 0.60),
        (10, 0.100, 0.40), (5, 0.200, 0.20),
    ]
    
    for i, price in enumerate(price_levels):
        distance_pct = abs(price - current_price) / current_price
        intensity = 0
        
        for leverage, liq_dist, weight in leverage_configs:
            sigma = 0.004
            gauss = np.exp(-((distance_pct - liq_dist) ** 2) / (2 * sigma ** 2))
            intensity += weight * gauss
        
        # 成交量加权
        for _, row in df.iterrows():
            if row['low'] <= price <= row['high']:
                vol_weight = row['volume'] / df['volume'].max()
                intensity += vol_weight * 0.15
        
        heatmap[i] = intensity
    
    # 归一化
    if heatmap.max() > 0:
        heatmap = heatmap / heatmap.max()
    
    # 找支撑/阻力位
    supports, resistances = [], []
    for i in range(5, len(heatmap) - 5):
        if heatmap[i] > 0.35:
            is_peak = all(heatmap[i] >= heatmap[i+j] for j in range(-3, 4) if j != 0)
            if is_peak:
                price = price_levels[i]
                if price < current_price * 0.998:
                    supports.append((price, heatmap[i]))
                elif price > current_price * 1.002:
                    resistances.append((price, heatmap[i]))
    
    supports = sorted(supports, key=lambda x: -x[1])[:3]
    resistances = sorted(resistances, key=lambda x: -x[1])[:3]
    
    return heatmap, price_levels, [p for p, _ in supports], [p for p, _ in resistances]


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

def generate_chart_v5(symbol, interval='15m', limit=200):
    """生成专业图表 v5 (CCXT + CoinGecko)"""
    symbol_clean = symbol.upper().replace('$', '').strip()
    base_coin = symbol_clean.replace('USDT', '')
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    coin_id = COINGECKO_IDS.get(base_coin, base_coin.lower())
    
    logger.info(f"📊 生成图表 v5: {symbol_clean} (CCXT + CoinGecko)")
    
    # 获取数据
    df = get_ccxt_ohlcv(symbol_clean, interval, limit)
    if df is None or df.empty:
        logger.error("❌ CCXT K线获取失败")
        return None
    
    ticker = get_ccxt_ticker(symbol_clean)
    funding = get_ccxt_funding_rate(symbol_clean)
    orderbook = get_ccxt_orderbook(symbol_clean, 10)
    cg_data = get_coingecko_market_data(coin_id)
    
    try:
        plt.style.use('dark_background')
        configure_matplotlib_fonts()
        plt.rcParams['axes.unicode_minus'] = False
        
        fig = plt.figure(figsize=(20, 14), facecolor=COLORS['bg'])
        
        # 布局
        ax_heat = fig.add_axes([0.02, 0.28, 0.03, 0.62], facecolor=COLORS['bg'])
        ax_main = fig.add_axes([0.06, 0.28, 0.66, 0.62], facecolor=COLORS['bg'])
        ax_info = fig.add_axes([0.74, 0.28, 0.24, 0.62], facecolor=COLORS['panel'])
        ax_flow = fig.add_axes([0.02, 0.02, 0.96, 0.22], facecolor=COLORS['panel'])
        
        current_price = df['close'].iloc[-1]
        price_min = df['low'].min() * 0.998
        price_max = df['high'].max() * 1.002
        
        # ========== 清算热力图 ==========
        heatmap, heat_levels, supports, resistances = calculate_liquidation_heatmap(df, current_price)
        
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
        
        # ========== K线图 + 支撑/阻力位 ==========
        for sup in supports:
            if price_min <= sup <= price_max:
                ax_main.axhline(y=sup, color=COLORS['up'], linewidth=1.5, linestyle='--', alpha=0.7)
        
        for res in resistances:
            if price_min <= res <= price_max:
                ax_main.axhline(y=res, color=COLORS['down'], linewidth=1.5, linestyle='--', alpha=0.7)
        
        for i, (_, row) in enumerate(df.iterrows()):
            is_up = row['close'] >= row['open']
            color = COLORS['up'] if is_up else COLORS['down']
            ax_main.plot([i, i], [row['low'], row['high']], color=color, linewidth=0.8)
            
            body_bottom = min(row['open'], row['close'])
            body_height = max(abs(row['close'] - row['open']), (price_max - price_min) * 0.0003)
            rect = mpatches.Rectangle((i - 0.3, body_bottom), 0.6, body_height,
                                       facecolor=color, edgecolor=color, alpha=0.95)
            ax_main.add_patch(rect)
        
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
        lh = 0.045
        
        # 价格
        ax_info.text(0.5, y, f'${current_price:,.2f}', fontsize=18, fontweight='bold',
                    color=COLORS['yellow'], transform=ax_info.transAxes, ha='center')
        y -= 0.06
        
        if ticker:
            pct = ticker.get('percentage', 0)
            change_color = COLORS['up'] if pct >= 0 else COLORS['down']
            ax_info.text(0.5, y, f'{pct:+.2f}%', fontsize=12, fontweight='bold',
                        color=change_color, transform=ax_info.transAxes, ha='center')
        y -= 0.06
        
        ax_info.axhline(y=y, xmin=0.05, xmax=0.95, color=COLORS['grid'], linewidth=0.5)
        y -= 0.03
        
        # 支撑/阻力位
        ax_info.text(0.5, y, '支撑位 (清算密集区)', fontsize=FONT['small'],
                    color=COLORS['text_dim'], transform=ax_info.transAxes, ha='center')
        y -= lh
        
        for i, sup in enumerate(supports[:3]):
            ax_info.text(0.08, y, f'S{i+1}:', fontsize=FONT['label'], color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.92, y, f'${sup:,.0f}', fontsize=FONT['value'], fontweight='bold',
                        color=COLORS['up'], transform=ax_info.transAxes, ha='right')
            y -= lh
        
        y -= 0.02
        ax_info.text(0.5, y, '阻力位 (清算密集区)', fontsize=FONT['small'],
                    color=COLORS['text_dim'], transform=ax_info.transAxes, ha='center')
        y -= lh
        
        for i, res in enumerate(resistances[:3]):
            ax_info.text(0.08, y, f'R{i+1}:', fontsize=FONT['label'], color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.92, y, f'${res:,.0f}', fontsize=FONT['value'], fontweight='bold',
                        color=COLORS['down'], transform=ax_info.transAxes, ha='right')
            y -= lh
        
        y -= 0.02
        ax_info.axhline(y=y, xmin=0.05, xmax=0.95, color=COLORS['grid'], linewidth=0.5)
        y -= 0.03
        
        # CCXT 数据
        ax_info.text(0.5, y, 'CCXT 数据', fontsize=FONT['subtitle'], fontweight='bold',
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
        y -= 0.03
        
        # CoinGecko 数据
        ax_info.text(0.5, y, 'CoinGecko 数据', fontsize=FONT['subtitle'], fontweight='bold',
                    color=COLORS['purple'], transform=ax_info.transAxes, ha='center')
        y -= lh
        
        if cg_data:
            mc = cg_data.get('market_cap', {}).get('usd', 0)
            ax_info.text(0.08, y, '市值:', fontsize=FONT['label'], color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.92, y, format_num(mc), fontsize=FONT['value'], color=COLORS['yellow'],
                        transform=ax_info.transAxes, ha='right')
            y -= lh
            
            vol = cg_data.get('total_volume', {}).get('usd', 0)
            ax_info.text(0.08, y, '24H成交量:', fontsize=FONT['label'], color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.92, y, format_num(vol), fontsize=FONT['value'], color=COLORS['text'],
                        transform=ax_info.transAxes, ha='right')
            y -= lh
            
            mc_rank = cg_data.get('market_cap_rank')
            if mc_rank:
                ax_info.text(0.08, y, '市值排名:', fontsize=FONT['label'], color=COLORS['text_dim'],
                            transform=ax_info.transAxes)
                ax_info.text(0.92, y, f'#{mc_rank}', fontsize=FONT['value'], fontweight='bold',
                            color=COLORS['yellow'], transform=ax_info.transAxes, ha='right')
                y -= lh
            
            ath = cg_data.get('ath', {}).get('usd', 0)
            ax_info.text(0.08, y, 'ATH:', fontsize=FONT['label'], color=COLORS['text_dim'],
                        transform=ax_info.transAxes)
            ax_info.text(0.92, y, f'${ath:,.0f}', fontsize=FONT['value'], color=COLORS['up'],
                        transform=ax_info.transAxes, ha='right')
        else:
            ax_info.text(0.5, y, '(数据加载中...)', fontsize=FONT['small'],
                        color=COLORS['text_dim'], transform=ax_info.transAxes, ha='center')
        
        # ========== 底部：订单簿深度 ==========
        ax_flow.set_xlim(0, 1)
        ax_flow.set_ylim(0, 1)
        ax_flow.axis('off')
        
        ax_flow.text(0.5, 0.92, '订单簿深度 (CCXT)', fontsize=FONT['subtitle'], fontweight='bold',
                    color=COLORS['text'], transform=ax_flow.transAxes, ha='center')
        
        if orderbook:
            bids = orderbook.get('bids', [])[:10]
            asks = orderbook.get('asks', [])[:10]
            
            # 买单 (左侧)
            ax_flow.text(0.25, 0.82, '买单 (Bids)', fontsize=FONT['label'], fontweight='bold',
                        color=COLORS['up'], transform=ax_flow.transAxes, ha='center')
            
            for i, bid in enumerate(bids):
                y_pos = 0.72 - i * 0.07
                price, amount = bid[0], bid[1]
                ax_flow.text(0.12, y_pos, f'${price:,.0f}', fontsize=FONT['small'],
                            color=COLORS['up'], transform=ax_flow.transAxes, ha='center')
                ax_flow.text(0.30, y_pos, f'{amount:.4f}', fontsize=FONT['small'],
                            color=COLORS['text'], transform=ax_flow.transAxes, ha='center')
                
                # 深度条
                max_amount = max(b[1] for b in bids)
                bar_width = (amount / max_amount) * 0.15
                ax_flow.barh(y_pos, bar_width, height=0.05, left=0.35,
                            color=COLORS['up'], alpha=0.5, transform=ax_flow.transAxes)
            
            # 卖单 (右侧)
            ax_flow.text(0.75, 0.82, '卖单 (Asks)', fontsize=FONT['label'], fontweight='bold',
                        color=COLORS['down'], transform=ax_flow.transAxes, ha='center')
            
            for i, ask in enumerate(asks):
                y_pos = 0.72 - i * 0.07
                price, amount = ask[0], ask[1]
                ax_flow.text(0.62, y_pos, f'${price:,.0f}', fontsize=FONT['small'],
                            color=COLORS['down'], transform=ax_flow.transAxes, ha='center')
                ax_flow.text(0.80, y_pos, f'{amount:.4f}', fontsize=FONT['small'],
                            color=COLORS['text'], transform=ax_flow.transAxes, ha='center')
                
                max_amount = max(a[1] for a in asks)
                bar_width = (amount / max_amount) * 0.15
                ax_flow.barh(y_pos, bar_width, height=0.05, left=0.85,
                            color=COLORS['down'], alpha=0.5, transform=ax_flow.transAxes)
        else:
            ax_flow.text(0.5, 0.5, '订单簿数据加载失败', fontsize=FONT['label'],
                        color=COLORS['text_dim'], transform=ax_flow.transAxes, ha='center')
        
        # ========== 标题 ==========
        interval_map = {'5m': '5分钟', '15m': '15分钟', '1h': '1小时', '4h': '4小时'}
        fig.text(0.02, 0.96, f"{symbol_clean}  ·  {interval_map.get(interval, interval)}",
                fontsize=FONT['title'], fontweight='bold', color=COLORS['text'])
        
        # 图例
        gradient = np.linspace(0, 1, 100).reshape(1, -1)
        ax_legend = fig.add_axes([0.28, 0.94, 0.10, 0.012])
        ax_legend.imshow(gradient, aspect='auto', cmap=cmap)
        ax_legend.set_xticks([0, 99])
        ax_legend.set_xticklabels(['低', '高'], fontsize=7, color=COLORS['text_dim'])
        ax_legend.set_yticks([])
        ax_legend.set_title('清算密度', fontsize=FONT['small'], color=COLORS['text_dim'], pad=2)
        for spine in ax_legend.spines.values():
            spine.set_visible(False)
        
        # 数据源标注
        fig.text(0.98, 0.96, 'CCXT + CoinGecko', fontsize=FONT['small'],
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
        logger.info(f"✅ 图表 v5 生成成功: {symbol_clean} ({size_kb:.1f} KB)")
        
        return image_data
        
    except Exception as e:
        logger.exception(f"❌ 图表生成失败: {e}")
        return None


def test_chart_v5(symbol='BTC'):
    """测试图表"""
    import os
    
    logger.info(f"🧪 测试图表 v5: {symbol}")
    
    image_data = generate_chart_v5(symbol, interval='15m', limit=200)
    
    if image_data:
        os.makedirs('output', exist_ok=True)
        output_path = f'output/chart_v5_{symbol}.png'
        with open(output_path, 'wb') as f:
            f.write(image_data)
        logger.info(f"✅ 图片已保存: {output_path}")
        return True
    return False


if __name__ == '__main__':
    test_chart_v5('BTC')
    test_chart_v5('ETH')
