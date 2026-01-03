"""
专业图表生成模块 v3
- Coinglass 风格清算热力图
- NOFX 量化数据接口（机构/散户资金流向）
- 简约、设计性、实用性
"""

import io
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.collections import PolyCollection
from datetime import datetime, timedelta
from logger import logger
from chart_fonts import configure_matplotlib_fonts

# ==================== 配置 ====================
BINANCE_FUTURES_KLINES_URL = "https://fapi.binance.com/fapi/v1/klines"
NOFX_API_BASE = "http://nofxaios.com:30006"
NOFX_AUTH_KEY = "cm_568c67eae410d912c54c"

# Coinglass 风格配色
COLORS = {
    'bg': '#131722',           # 深色背景
    'panel': '#1e222d',        # 面板背景
    'grid': '#363a45',         # 网格线
    'text': '#d1d4dc',         # 主文字
    'text_dim': '#787b86',     # 次要文字
    'up': '#26a69a',           # 涨（青绿）
    'down': '#ef5350',         # 跌（红）
    'yellow': '#f7931a',       # 强调色
    'blue': '#2962ff',         # 蓝色
    'purple': '#7b1fa2',       # 紫色
    # 清算热力图渐变
    'heatmap': ['#131722', '#1a237e', '#4a148c', '#880e4f', '#b71c1c', '#ff6f00', '#ffeb3b'],
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


# ==================== 数据获取 ====================

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
            for col in ['open', 'high', 'low', 'close', 'volume', 'taker_buy_base']:
                df[col] = df[col].astype(float)
            
            # 计算买卖力量
            df['taker_buy'] = df['taker_buy_base']
            df['taker_sell'] = df['volume'] - df['taker_buy_base']
            df['delta'] = df['taker_buy'] - df['taker_sell']
            
            return df
    except Exception as e:
        logger.warning(f"获取K线失败: {e}")
    return None


def get_nofx_coin_data(symbol):
    """从 NOFX 获取币种综合数据（机构/散户资金流向）"""
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


def estimate_liquidation_heatmap(df, num_price_levels=100):
    """
    生成 Coinglass 风格的清算热力图数据
    基于价格分布和成交量估算清算密集区
    """
    current_price = df['close'].iloc[-1]
    price_range = df['high'].max() - df['low'].min()
    
    # 扩展价格范围（上下各 5%）
    price_min = df['low'].min() - price_range * 0.05
    price_max = df['high'].max() + price_range * 0.05
    
    price_levels = np.linspace(price_min, price_max, num_price_levels)
    heatmap = np.zeros((num_price_levels, len(df)))
    
    # 常见杠杆的清算距离
    leverage_configs = [
        (100, 0.01, 1.0),   # 100x: 1% 距离, 最高强度
        (50, 0.02, 0.85),   # 50x: 2%
        (25, 0.04, 0.7),    # 25x: 4%
        (10, 0.10, 0.5),    # 10x: 10%
        (5, 0.20, 0.3),     # 5x: 20%
    ]
    
    for i, (_, row) in enumerate(df.iterrows()):
        candle_mid = (row['high'] + row['low']) / 2
        candle_range = row['high'] - row['low']
        vol_weight = row['volume'] / df['volume'].max()
        
        for j, price in enumerate(price_levels):
            intensity = 0
            
            # 计算与K线中点的距离
            distance_pct = abs(price - candle_mid) / candle_mid
            
            # 检查每个杠杆档位
            for leverage, liq_dist, strength in leverage_configs:
                # 如果价格在该杠杆的清算区域附近
                if abs(distance_pct - liq_dist) < 0.008:
                    intensity += strength * vol_weight
                elif abs(distance_pct - liq_dist) < 0.015:
                    intensity += strength * vol_weight * 0.5
            
            # 在K线范围内额外增加热度
            if row['low'] <= price <= row['high']:
                intensity += vol_weight * 0.3
            
            heatmap[j, i] = intensity
    
    # 平滑处理
    from scipy.ndimage import gaussian_filter
    try:
        heatmap = gaussian_filter(heatmap, sigma=1.5)
    except:
        pass  # 如果没有 scipy，跳过平滑
    
    return heatmap, price_levels


# ==================== 图表绘制 ====================

def find_support_resistance(df, num_levels=3):
    """
    计算支撑位和阻力位
    基于价格密集成交区和关键高低点
    """
    current_price = df['close'].iloc[-1]
    
    # 收集所有关键价格点
    key_prices = []
    
    # 1. 近期高低点
    for i in range(2, len(df) - 2):
        # 局部高点
        if df['high'].iloc[i] >= df['high'].iloc[i-1] and df['high'].iloc[i] >= df['high'].iloc[i-2] and \
           df['high'].iloc[i] >= df['high'].iloc[i+1] and df['high'].iloc[i] >= df['high'].iloc[i+2]:
            key_prices.append(('R', df['high'].iloc[i], df['volume'].iloc[i]))
        # 局部低点
        if df['low'].iloc[i] <= df['low'].iloc[i-1] and df['low'].iloc[i] <= df['low'].iloc[i-2] and \
           df['low'].iloc[i] <= df['low'].iloc[i+1] and df['low'].iloc[i] <= df['low'].iloc[i+2]:
            key_prices.append(('S', df['low'].iloc[i], df['volume'].iloc[i]))
    
    # 2. 成交量加权的价格区间
    price_range = df['high'].max() - df['low'].min()
    num_bins = 20
    bins = np.linspace(df['low'].min(), df['high'].max(), num_bins + 1)
    volume_profile = np.zeros(num_bins)
    
    for _, row in df.iterrows():
        for j in range(num_bins):
            if bins[j] <= row['close'] <= bins[j+1]:
                volume_profile[j] += row['volume']
    
    # 找到成交量最大的价格区间
    top_vol_indices = np.argsort(volume_profile)[-3:]
    for idx in top_vol_indices:
        mid_price = (bins[idx] + bins[idx+1]) / 2
        level_type = 'R' if mid_price > current_price else 'S'
        key_prices.append((level_type, mid_price, volume_profile[idx]))
    
    # 分离支撑位和阻力位
    supports = [(p, v) for t, p, v in key_prices if t == 'S' and p < current_price]
    resistances = [(p, v) for t, p, v in key_prices if t == 'R' and p > current_price]
    
    # 按成交量排序，取前 num_levels 个
    supports.sort(key=lambda x: -x[1])
    resistances.sort(key=lambda x: -x[1])
    
    return [p for p, v in supports[:num_levels]], [p for p, v in resistances[:num_levels]]


def generate_pro_chart(symbol, interval='15m', limit=80):
    """
    生成专业图表
    - 上部: K线 + 支撑/阻力位
    - 下部: 主力资金流向面板（明确标注数值）
    """
    symbol_clean = symbol.upper().replace('$', '').strip()
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    logger.info(f"📊 生成专业图表: {symbol_clean}")
    
    # 获取数据
    df = get_futures_klines(symbol_clean, interval, limit)
    if df is None or df.empty:
        logger.error(f"❌ 无法获取 K线数据")
        return None
    
    nofx_data = get_nofx_coin_data(symbol_clean)
    
    try:
        plt.style.use('dark_background')
        configure_matplotlib_fonts()
        plt.rcParams['axes.unicode_minus'] = False
        
        # 创建图表
        fig = plt.figure(figsize=(16, 12), facecolor=COLORS['bg'])
        
        # 布局: K线(50%) + 资金流(25%) + 信息面板
        ax_main = fig.add_axes([0.06, 0.38, 0.88, 0.52], facecolor=COLORS['bg'])
        ax_flow = fig.add_axes([0.06, 0.06, 0.88, 0.28], facecolor=COLORS['panel'])
        
        current_price = df['close'].iloc[-1]
        price_min = df['low'].min() * 0.995
        price_max = df['high'].max() * 1.005
        
        # ========== 计算支撑/阻力位 ==========
        supports, resistances = find_support_resistance(df)
        
        # ========== 清算热力图背景（淡化） ==========
        try:
            heatmap, price_levels = estimate_liquidation_heatmap(df, num_price_levels=100)
            cmap = LinearSegmentedColormap.from_list('coinglass', COLORS['heatmap'])
            extent = [-0.5, len(df) - 0.5, price_levels[0], price_levels[-1]]
            ax_main.imshow(heatmap, aspect='auto', extent=extent, origin='lower',
                          cmap=cmap, alpha=0.5, interpolation='bilinear')
        except Exception as e:
            logger.warning(f"热力图生成失败: {e}")
        
        # ========== 绘制支撑/阻力位 ==========
        for i, sup in enumerate(supports):
            ax_main.axhline(y=sup, color=COLORS['up'], linewidth=2, 
                           linestyle='--', alpha=0.8)
            ax_main.text(len(df) + 0.5, sup, f'S{i+1} ${sup:,.0f}', 
                        fontsize=9, color=COLORS['up'], va='center', fontweight='bold')
        
        for i, res in enumerate(resistances):
            ax_main.axhline(y=res, color=COLORS['down'], linewidth=2,
                           linestyle='--', alpha=0.8)
            ax_main.text(len(df) + 0.5, res, f'R{i+1} ${res:,.0f}',
                        fontsize=9, color=COLORS['down'], va='center', fontweight='bold')
        
        # ========== K线绘制 ==========
        for i, (_, row) in enumerate(df.iterrows()):
            is_up = row['close'] >= row['open']
            color = COLORS['up'] if is_up else COLORS['down']
            
            ax_main.plot([i, i], [row['low'], row['high']], color=color, linewidth=1.2)
            
            body_bottom = min(row['open'], row['close'])
            body_height = abs(row['close'] - row['open'])
            if body_height < (price_max - price_min) * 0.001:
                body_height = (price_max - price_min) * 0.001
            
            rect = mpatches.Rectangle(
                (i - 0.35, body_bottom), 0.7, body_height,
                facecolor=color, edgecolor=color, linewidth=0.5, alpha=0.95
            )
            ax_main.add_patch(rect)
        
        # ========== 当前价格线 ==========
        ax_main.axhline(y=current_price, color=COLORS['yellow'], linewidth=2, alpha=0.95)
        ax_main.annotate(
            f'${current_price:,.2f}',
            xy=(len(df), current_price), xytext=(len(df) + 0.5, current_price),
            fontsize=11, fontweight='bold', color=COLORS['bg'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['yellow'], edgecolor='none'),
            va='center', ha='left'
        )
        
        # ========== 主力资金流向面板（表格式设计） ==========
        ax_flow.set_facecolor(COLORS['panel'])
        ax_flow.set_xlim(0, 1)
        ax_flow.set_ylim(0, 1)
        ax_flow.axis('off')
        
        # 绘制分隔线
        ax_flow.axvline(x=0.5, color=COLORS['grid'], linewidth=1, alpha=0.5)
        ax_flow.axhline(y=0.85, color=COLORS['grid'], linewidth=0.5, alpha=0.3)
        
        # ===== 左半部分：现货资金 =====
        ax_flow.text(0.25, 0.92, 'SPOT FUND FLOW', transform=ax_flow.transAxes,
                    fontsize=11, fontweight='bold', color=COLORS['blue'], ha='center')
        
        # 表头
        headers_x = [0.06, 0.14, 0.22, 0.30, 0.40]
        ax_flow.text(headers_x[0], 0.78, 'Period', transform=ax_flow.transAxes,
                    fontsize=8, color=COLORS['text_dim'], ha='center')
        ax_flow.text(headers_x[1], 0.78, 'Inflow', transform=ax_flow.transAxes,
                    fontsize=8, color=COLORS['up'], ha='center')
        ax_flow.text(headers_x[2], 0.78, 'Outflow', transform=ax_flow.transAxes,
                    fontsize=8, color=COLORS['down'], ha='center')
        ax_flow.text(headers_x[3], 0.78, 'Net', transform=ax_flow.transAxes,
                    fontsize=8, color=COLORS['yellow'], ha='center')
        ax_flow.text(headers_x[4], 0.78, 'Change', transform=ax_flow.transAxes,
                    fontsize=8, color=COLORS['text_dim'], ha='center')
        
        # 时间周期数据
        periods = ['5m', '15m', '1h', '4h', '24h']
        row_y = [0.65, 0.52, 0.39, 0.26, 0.13]
        
        if nofx_data and 'netflow' in nofx_data:
            netflow = nofx_data['netflow']
            for i, period in enumerate(periods):
                # 现货：机构 + 散户
                inst_spot = netflow.get('institution', {}).get('spot', {}).get(period, 0)
                pers_spot = netflow.get('personal', {}).get('spot', {}).get(period, 0)
                
                # 计算流入流出（正数=流入，负数=流出）
                inflow = max(inst_spot, 0) + max(pers_spot, 0)
                outflow = abs(min(inst_spot, 0)) + abs(min(pers_spot, 0))
                net = inst_spot + pers_spot
                
                # 周期
                ax_flow.text(headers_x[0], row_y[i], period, transform=ax_flow.transAxes,
                            fontsize=9, color=COLORS['text'], ha='center', fontweight='bold')
                # 流入
                ax_flow.text(headers_x[1], row_y[i], f'{inflow/1e6:.2f}M', transform=ax_flow.transAxes,
                            fontsize=9, color=COLORS['up'], ha='center')
                # 流出
                ax_flow.text(headers_x[2], row_y[i], f'{outflow/1e6:.2f}M', transform=ax_flow.transAxes,
                            fontsize=9, color=COLORS['down'], ha='center')
                # 净流入
                net_color = COLORS['up'] if net >= 0 else COLORS['down']
                ax_flow.text(headers_x[3], row_y[i], f'{net/1e6:+.2f}M', transform=ax_flow.transAxes,
                            fontsize=9, color=net_color, ha='center', fontweight='bold')
                # 变化率（模拟）
                change_pct = (net / max(abs(inflow) + abs(outflow), 1)) * 100
                change_color = COLORS['up'] if change_pct >= 0 else COLORS['down']
                ax_flow.text(headers_x[4], row_y[i], f'{change_pct:+.1f}%', transform=ax_flow.transAxes,
                            fontsize=9, color=change_color, ha='center')
        else:
            # 无数据时显示 N/A
            for i, period in enumerate(periods):
                ax_flow.text(headers_x[0], row_y[i], period, transform=ax_flow.transAxes,
                            fontsize=9, color=COLORS['text'], ha='center', fontweight='bold')
                for j in range(1, 5):
                    ax_flow.text(headers_x[j], row_y[i], '--', transform=ax_flow.transAxes,
                                fontsize=9, color=COLORS['text_dim'], ha='center')
        
        # ===== 右半部分：合约资金 =====
        ax_flow.text(0.75, 0.92, 'FUTURES FUND FLOW', transform=ax_flow.transAxes,
                    fontsize=11, fontweight='bold', color=COLORS['purple'], ha='center')
        
        # 表头
        headers_x2 = [0.56, 0.64, 0.72, 0.80, 0.90]
        ax_flow.text(headers_x2[0], 0.78, 'Period', transform=ax_flow.transAxes,
                    fontsize=8, color=COLORS['text_dim'], ha='center')
        ax_flow.text(headers_x2[1], 0.78, 'Inflow', transform=ax_flow.transAxes,
                    fontsize=8, color=COLORS['up'], ha='center')
        ax_flow.text(headers_x2[2], 0.78, 'Outflow', transform=ax_flow.transAxes,
                    fontsize=8, color=COLORS['down'], ha='center')
        ax_flow.text(headers_x2[3], 0.78, 'Net', transform=ax_flow.transAxes,
                    fontsize=8, color=COLORS['yellow'], ha='center')
        ax_flow.text(headers_x2[4], 0.78, 'Change', transform=ax_flow.transAxes,
                    fontsize=8, color=COLORS['text_dim'], ha='center')
        
        if nofx_data and 'netflow' in nofx_data:
            netflow = nofx_data['netflow']
            for i, period in enumerate(periods):
                # 合约：机构 + 散户
                inst_future = netflow.get('institution', {}).get('future', {}).get(period, 0)
                pers_future = netflow.get('personal', {}).get('future', {}).get(period, 0)
                
                inflow = max(inst_future, 0) + max(pers_future, 0)
                outflow = abs(min(inst_future, 0)) + abs(min(pers_future, 0))
                net = inst_future + pers_future
                
                ax_flow.text(headers_x2[0], row_y[i], period, transform=ax_flow.transAxes,
                            fontsize=9, color=COLORS['text'], ha='center', fontweight='bold')
                ax_flow.text(headers_x2[1], row_y[i], f'{inflow/1e6:.2f}M', transform=ax_flow.transAxes,
                            fontsize=9, color=COLORS['up'], ha='center')
                ax_flow.text(headers_x2[2], row_y[i], f'{outflow/1e6:.2f}M', transform=ax_flow.transAxes,
                            fontsize=9, color=COLORS['down'], ha='center')
                net_color = COLORS['up'] if net >= 0 else COLORS['down']
                ax_flow.text(headers_x2[3], row_y[i], f'{net/1e6:+.2f}M', transform=ax_flow.transAxes,
                            fontsize=9, color=net_color, ha='center', fontweight='bold')
                change_pct = (net / max(abs(inflow) + abs(outflow), 1)) * 100
                change_color = COLORS['up'] if change_pct >= 0 else COLORS['down']
                ax_flow.text(headers_x2[4], row_y[i], f'{change_pct:+.1f}%', transform=ax_flow.transAxes,
                            fontsize=9, color=change_color, ha='center')
        else:
            # 无数据时用买卖力量填充
            total_buy = df['taker_buy'].sum()
            total_sell = df['taker_sell'].sum()
            net_delta = total_buy - total_sell
            
            for i, period in enumerate(periods):
                ax_flow.text(headers_x2[0], row_y[i], period, transform=ax_flow.transAxes,
                            fontsize=9, color=COLORS['text'], ha='center', fontweight='bold')
                # 估算每个周期的买卖量
                period_len = {'5m': 5, '15m': 15, '1h': 60, '4h': 240, '24h': 1440}
                ratio = period_len.get(period, 60) / 1440
                est_buy = total_buy * ratio
                est_sell = total_sell * ratio
                est_net = est_buy - est_sell
                
                ax_flow.text(headers_x2[1], row_y[i], f'{est_buy:,.0f}', transform=ax_flow.transAxes,
                            fontsize=9, color=COLORS['up'], ha='center')
                ax_flow.text(headers_x2[2], row_y[i], f'{est_sell:,.0f}', transform=ax_flow.transAxes,
                            fontsize=9, color=COLORS['down'], ha='center')
                net_color = COLORS['up'] if est_net >= 0 else COLORS['down']
                ax_flow.text(headers_x2[3], row_y[i], f'{est_net:+,.0f}', transform=ax_flow.transAxes,
                            fontsize=9, color=net_color, ha='center', fontweight='bold')
                buy_pct = (est_buy / (est_buy + est_sell) * 100) - 50 if (est_buy + est_sell) > 0 else 0
                change_color = COLORS['up'] if buy_pct >= 0 else COLORS['down']
                ax_flow.text(headers_x2[4], row_y[i], f'{buy_pct:+.1f}%', transform=ax_flow.transAxes,
                            fontsize=9, color=change_color, ha='center')
        
        # ========== 样式设置 ==========
        ax_main.set_xlim(-1, len(df) + 6)
        ax_main.set_ylim(price_min, price_max)
        ax_main.set_ylabel('Price (USDT)', color=COLORS['text_dim'], fontsize=10)
        ax_main.tick_params(colors=COLORS['text_dim'], labelsize=9)
        ax_main.grid(False)
        for spine in ax_main.spines.values():
            spine.set_visible(False)
        plt.setp(ax_main.get_xticklabels(), visible=False)
        
        # ========== 标题信息 ==========
        interval_map = {'1m': '1min', '5m': '5min', '15m': '15min', '1h': '1H', '4h': '4H', '1d': '1D'}
        price_change = ((current_price - df['open'].iloc[0]) / df['open'].iloc[0]) * 100
        change_sign = '+' if price_change >= 0 else ''
        change_color = COLORS['up'] if price_change >= 0 else COLORS['down']
        
        # 主标题
        title = f"{symbol_clean}  ·  {interval_map.get(interval, interval)}  ·  Support & Resistance"
        fig.text(0.06, 0.96, title, fontsize=14, fontweight='bold', color=COLORS['text'])
        
        # 价格信息
        price_info = f"${current_price:,.2f}  ({change_sign}{price_change:.2f}%)"
        fig.text(0.94, 0.96, price_info, fontsize=13, fontweight='bold', 
                color=change_color, ha='right')
        
        # 支撑/阻力图例
        fig.text(0.06, 0.925, '━ Support', fontsize=9, color=COLORS['up'])
        fig.text(0.16, 0.925, '━ Resistance', fontsize=9, color=COLORS['down'])
        fig.text(0.28, 0.925, '━ Current Price', fontsize=9, color=COLORS['yellow'])
        
        # 水印
        fig.text(0.5, 0.55, 'NOFX', fontsize=35, color=COLORS['yellow'],
                ha='center', va='center', alpha=0.015, fontweight='bold',
                transform=fig.transFigure)
        
        # ========== 保存 ==========
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=140, bbox_inches='tight',
                   facecolor=COLORS['bg'], edgecolor='none')
        buf.seek(0)
        image_data = buf.read()
        buf.close()
        plt.close(fig)
        
        size_kb = len(image_data) / 1024
        logger.info(f"✅ 专业图表生成成功: {symbol_clean} ({size_kb:.1f} KB)")
        
        return image_data
        
    except Exception as e:
        logger.exception(f"❌ 图表生成失败: {e}")
        return None


def send_pro_chart_to_telegram(symbol, interval='15m', caption=None):
    """发送专业图表到 Telegram"""
    from telegram import send_telegram_photo
    
    chart_data = generate_pro_chart(symbol, interval=interval)
    if not chart_data:
        return False
    
    if caption is None:
        symbol_clean = symbol.upper().replace('$', '').strip()
        if not symbol_clean.endswith('USDT'):
            symbol_clean = f"{symbol_clean}USDT"
        caption = f"📊 <b>{symbol_clean}</b> | 15min | Liquidation Heatmap + Fund Flow"
    
    return send_telegram_photo(chart_data, caption=caption)


def test_pro_chart(symbol='BTC'):
    """测试专业图表"""
    import os
    
    logger.info(f"🧪 测试专业图表: {symbol}")
    
    image_data = generate_pro_chart(symbol, interval='15m', limit=80)
    
    if image_data:
        os.makedirs('output', exist_ok=True)
        output_path = f'output/pro_chart_{symbol}.png'
        with open(output_path, 'wb') as f:
            f.write(image_data)
        logger.info(f"✅ 图片已保存: {output_path}")
        return True
    return False


if __name__ == '__main__':
    test_pro_chart('BTC')
    test_pro_chart('ETH')
