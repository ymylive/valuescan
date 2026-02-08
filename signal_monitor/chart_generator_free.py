"""
免费 K线图表生成模块（增强版 v2）
使用 matplotlib + Binance API 生成美观的K线图
融合主力资金流向 + 买卖力量对比
"""

import io
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
from datetime import datetime, timedelta
from logger import logger
from chart_fonts import configure_matplotlib_fonts

# Binance API 配置
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
BINANCE_FUTURES_KLINES_URL = "https://fapi.binance.com/fapi/v1/klines"
BINANCE_TAKER_VOLUME_URL = "https://fapi.binance.com/futures/data/takerlongshortRatio"

# 颜色配置（Binance风格）
COLORS = {
    'bg': '#0B0E11',
    'card_bg': '#1E2329',
    'grid': '#2B3139',
    'text': '#EAECEF',
    'text_dim': '#848E9C',
    'up': '#0ECB81',
    'down': '#F6465D',
    'yellow': '#F0B90B',
    'blue': '#3861FB',
    'purple': '#8B5CF6',
    'orange': '#F7931A',
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


def get_klines_from_binance(symbol, interval='15m', limit=100):
    """从 Binance 获取 K线数据"""
    symbol_clean = symbol.upper().replace('$', '').strip()
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    params = {'symbol': symbol_clean, 'interval': interval, 'limit': limit}
    
    try:
        response = requests.get(BINANCE_KLINES_URL, params=params, 
                               proxies=get_proxies(), timeout=10)
        if response.status_code != 200:
            logger.error(f"❌ Binance API 错误: {response.status_code}")
            return None
        
        data = response.json()
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']:
            df[col] = df[col].astype(float)
        
        return df
    except Exception as e:
        logger.exception(f"❌ 获取 K线数据失败: {e}")
        return None


def get_futures_klines(symbol, interval='15m', limit=100):
    """获取合约K线数据（包含更多资金流信息）"""
    symbol_clean = symbol.upper().replace('$', '').strip()
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    params = {'symbol': symbol_clean, 'interval': interval, 'limit': limit}
    
    try:
        response = requests.get(BINANCE_FUTURES_KLINES_URL, params=params, 
                               proxies=get_proxies(), timeout=10)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume', 
                       'taker_buy_base', 'taker_buy_quote']:
                df[col] = df[col].astype(float)
            
            # 计算主力资金流向
            # taker_buy = 主动买入量, taker_sell = 总量 - 主动买入
            df['taker_buy'] = df['taker_buy_base']
            df['taker_sell'] = df['volume'] - df['taker_buy_base']
            df['net_flow'] = df['taker_buy'] - df['taker_sell']  # 净流入
            df['buy_ratio'] = df['taker_buy'] / df['volume'] * 100  # 买入占比
            
            return df
    except Exception as e:
        logger.warning(f"合约API失败，使用现货API: {e}")
    
    # 回退到现货API
    return get_klines_from_binance(symbol, interval, limit)


def calculate_fund_flow(df):
    """
    计算主力资金流向指标
    基于大单成交和买卖力量对比
    """
    if 'taker_buy' not in df.columns:
        # 如果没有taker数据，用价格变化估算
        df['net_flow'] = 0
        df['buy_ratio'] = 50
        for i in range(len(df)):
            if df['close'].iloc[i] > df['open'].iloc[i]:
                df.loc[df.index[i], 'net_flow'] = df['volume'].iloc[i] * 0.6
                df.loc[df.index[i], 'buy_ratio'] = 60
            else:
                df.loc[df.index[i], 'net_flow'] = -df['volume'].iloc[i] * 0.6
                df.loc[df.index[i], 'buy_ratio'] = 40
    
    # 计算累计净流入
    df['cumulative_flow'] = df['net_flow'].cumsum()
    
    # 计算资金流强度 (归一化到 -1 到 1)
    max_flow = df['net_flow'].abs().max()
    if max_flow > 0:
        df['flow_intensity'] = df['net_flow'] / max_flow
    else:
        df['flow_intensity'] = 0
    
    return df


def generate_chart_free(symbol, interval='15m', limit=80):
    """
    生成美观的K线图表（融合主力资金流向）
    
    Args:
        symbol: 交易对符号
        interval: K线周期（默认15分钟）
        limit: K线数量
    
    Returns:
        bytes: PNG 图片数据
    """
    symbol_clean = symbol.upper().replace('$', '').strip()
    if not symbol_clean.endswith('USDT'):
        symbol_clean = f"{symbol_clean}USDT"
    
    logger.info(f"📊 正在为 ${symbol_clean} 生成增强图表 v2...")
    
    # 优先获取合约K线（包含taker数据）
    df = get_futures_klines(symbol_clean, interval, limit)
    if df is None or df.empty:
        logger.error(f"❌ 无法获取 {symbol_clean} 的 K线数据")
        return None
    
    # 计算资金流向
    df = calculate_fund_flow(df)
    
    try:
        configure_matplotlib_fonts()
        plt.rcParams['axes.unicode_minus'] = False
        
        # 创建图表 - 4个区域
        fig = plt.figure(figsize=(14, 10), facecolor=COLORS['bg'])
        
        # 布局: K线(55%) + 资金流(15%) + 成交量(12%) + 买卖力量(8%)
        ax_main = fig.add_axes([0.06, 0.38, 0.88, 0.52], facecolor=COLORS['bg'])
        ax_flow = fig.add_axes([0.06, 0.24, 0.88, 0.12], facecolor=COLORS['bg'], sharex=ax_main)
        ax_vol = fig.add_axes([0.06, 0.12, 0.88, 0.10], facecolor=COLORS['bg'], sharex=ax_main)
        ax_ratio = fig.add_axes([0.06, 0.04, 0.88, 0.06], facecolor=COLORS['bg'], sharex=ax_main)
        
        price_min = df['low'].min() * 0.998
        price_max = df['high'].max() * 1.002
        current_price = df['close'].iloc[-1]
        
        # ========== 绘制K线 ==========
        width_candle = 0.7
        
        for i, (idx, row) in enumerate(df.iterrows()):
            is_up = row['close'] >= row['open']
            color = COLORS['up'] if is_up else COLORS['down']
            
            # 影线
            ax_main.plot([i, i], [row['low'], row['high']], 
                        color=color, linewidth=1.2, solid_capstyle='round')
            
            # 实体 - 使用渐变效果
            body_bottom = min(row['open'], row['close'])
            body_height = abs(row['close'] - row['open'])
            if body_height < (price_max - price_min) * 0.001:
                body_height = (price_max - price_min) * 0.001
            
            # 根据资金流强度调整透明度
            flow_alpha = 0.6 + abs(row.get('flow_intensity', 0)) * 0.4
            
            rect = mpatches.FancyBboxPatch(
                (i - width_candle/2, body_bottom),
                width_candle, body_height,
                boxstyle="round,pad=0.01,rounding_size=0.03",
                facecolor=color,
                edgecolor=color,
                linewidth=0.8,
                alpha=flow_alpha
            )
            ax_main.add_patch(rect)
        
        # ========== 当前价格线 + 标签框 ==========
        ax_main.axhline(y=current_price, color=COLORS['yellow'], 
                       linestyle='-', linewidth=1.5, alpha=0.9)
        
        # 价格标签背景框
        price_box = mpatches.FancyBboxPatch(
            (len(df) + 0.3, current_price - (price_max - price_min) * 0.015),
            4, (price_max - price_min) * 0.03,
            boxstyle="round,pad=0.02",
            facecolor=COLORS['yellow'],
            edgecolor='none',
            alpha=0.95
        )
        ax_main.add_patch(price_box)
        ax_main.text(len(df) + 2.3, current_price, f'${current_price:,.2f}',
                    color=COLORS['bg'], fontsize=9, fontweight='bold',
                    va='center', ha='center')
        
        # ========== 主力资金流向图 ==========
        flow_colors = [COLORS['up'] if x >= 0 else COLORS['down'] for x in df['net_flow']]
        ax_flow.bar(range(len(df)), df['net_flow'], width=width_candle, 
                   color=flow_colors, alpha=0.8)
        
        # 零线
        ax_flow.axhline(y=0, color=COLORS['text_dim'], linewidth=0.5, alpha=0.5)
        
        # 累计资金流曲线
        ax_flow_twin = ax_flow.twinx()
        ax_flow_twin.plot(range(len(df)), df['cumulative_flow'], 
                         color=COLORS['purple'], linewidth=2, alpha=0.9)
        ax_flow_twin.fill_between(range(len(df)), 0, df['cumulative_flow'],
                                  color=COLORS['purple'], alpha=0.15)
        ax_flow_twin.set_ylabel('Cum.', color=COLORS['purple'], fontsize=8)
        ax_flow_twin.tick_params(colors=COLORS['purple'], labelsize=7)
        ax_flow_twin.spines['right'].set_color(COLORS['purple'])
        ax_flow_twin.spines['right'].set_alpha(0.5)
        
        # ========== 成交量柱状图 ==========
        for i, (idx, row) in enumerate(df.iterrows()):
            color = COLORS['up'] if row['close'] >= row['open'] else COLORS['down']
            ax_vol.bar(i, row['volume'], width=width_candle, color=color, alpha=0.7)
        
        # ========== 买卖力量对比条 ==========
        for i, (idx, row) in enumerate(df.iterrows()):
            buy_ratio = row.get('buy_ratio', 50)
            sell_ratio = 100 - buy_ratio
            
            # 买入部分（绿色，从左开始）
            ax_ratio.barh(0, buy_ratio, left=i - 0.4, height=0.8,
                         color=COLORS['up'], alpha=0.8)
            # 卖出部分（红色，从买入结束开始）
            ax_ratio.barh(0, -sell_ratio, left=i + 0.4, height=0.8,
                         color=COLORS['down'], alpha=0.8)
        
        # 50%参考线
        ax_ratio.axhline(y=0, color=COLORS['text_dim'], linewidth=0.3, alpha=0.3)
        
        # ========== 样式设置 ==========
        for ax in [ax_main, ax_flow, ax_vol, ax_ratio]:
            ax.set_xlim(-1, len(df) + 5)
            ax.tick_params(colors=COLORS['text_dim'], labelsize=8)
            ax.grid(True, color=COLORS['grid'], alpha=0.2, linestyle='-', linewidth=0.5)
            for spine in ax.spines.values():
                spine.set_color(COLORS['grid'])
                spine.set_alpha(0.3)
            ax.set_facecolor(COLORS['bg'])
        
        ax_main.set_ylim(price_min, price_max)
        ax_main.set_ylabel('Price', color=COLORS['text_dim'], fontsize=9)
        ax_flow.set_ylabel('Net Flow', color=COLORS['text_dim'], fontsize=8)
        ax_vol.set_ylabel('Vol', color=COLORS['text_dim'], fontsize=8)
        ax_ratio.set_ylabel('B/S', color=COLORS['text_dim'], fontsize=7)
        
        # 隐藏中间图的x轴标签
        for ax in [ax_main, ax_flow, ax_vol]:
            plt.setp(ax.get_xticklabels(), visible=False)
        
        # X轴时间标签（只在底部显示）
        tick_positions = np.linspace(0, len(df)-1, min(10, len(df))).astype(int)
        tick_labels = [df.iloc[i]['timestamp'].strftime('%H:%M') for i in tick_positions]
        ax_ratio.set_xticks(tick_positions)
        ax_ratio.set_xticklabels(tick_labels, color=COLORS['text_dim'], fontsize=7)
        ax_ratio.set_ylim(-60, 60)
        ax_ratio.set_yticks([])
        
        # ========== 标题 ==========
        interval_map = {'1m': '1min', '5m': '5min', '15m': '15min', '1h': '1H', '4h': '4H', '1d': '1D'}
        interval_text = interval_map.get(interval, interval)
        
        price_change = ((current_price - df['open'].iloc[0]) / df['open'].iloc[0]) * 100
        change_sign = '+' if price_change >= 0 else ''
        change_color = COLORS['up'] if price_change >= 0 else COLORS['down']
        
        # 计算资金流总结
        total_net_flow = df['net_flow'].sum()
        flow_direction = "流入" if total_net_flow > 0 else "流出"
        flow_color = COLORS['up'] if total_net_flow > 0 else COLORS['down']
        
        title = f"BINANCE:{symbol_clean}  |  {interval_text}  |  ${current_price:,.2f}  ({change_sign}{price_change:.2f}%)"
        fig.suptitle(title, color=COLORS['text'], fontsize=14, fontweight='bold', y=0.97)
        
        # 右上角信息面板
        info_text = f"Net Flow: {'▲' if total_net_flow > 0 else '▼'} {abs(total_net_flow):,.0f}"
        fig.text(0.94, 0.935, info_text, color=flow_color, fontsize=10, 
                ha='right', fontweight='bold', alpha=0.9)
        
        # 图例
        legend_items = [
            ('━', COLORS['up'], 'Buy/Inflow'),
            ('━', COLORS['down'], 'Sell/Outflow'),
            ('━', COLORS['purple'], 'Cumulative Flow'),
        ]
        for i, (marker, color, label) in enumerate(legend_items):
            fig.text(0.08 + i*0.12, 0.935, f"{marker} {label}", 
                    color=color, fontsize=8, ha='left', alpha=0.8)
        
        # 水印
        fig.text(0.5, 0.5, 'Signal', color=COLORS['yellow'], fontsize=50,
                ha='center', va='center', alpha=0.02, fontweight='bold',
                transform=fig.transFigure)
        
        # ========== 保存图片 ==========
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=130, bbox_inches='tight',
                   facecolor=COLORS['bg'], edgecolor='none')
        buf.seek(0)
        image_data = buf.read()
        buf.close()
        plt.close(fig)
        
        size_kb = len(image_data) / 1024
        logger.info(f"✅ 增强图表v2生成成功: {symbol_clean} ({size_kb:.2f} KB)")
        
        return image_data
        
    except Exception as e:
        logger.exception(f"❌ 图表绘制失败: {e}")
        return None


def send_chart_to_telegram(symbol, interval='15m', caption=None):
    """
    生成图表并发送到 Telegram
    
    Args:
        symbol: 交易对符号
        interval: K线周期（默认15分钟）
        caption: 图片说明
    
    Returns:
        bool: 发送成功返回 True
    """
    from telegram import send_telegram_photo
    
    chart_data = generate_chart_free(symbol, interval=interval)
    
    if not chart_data:
        return False
    
    if caption is None:
        symbol_clean = symbol.upper().replace('$', '').strip()
        if not symbol_clean.endswith('USDT'):
            symbol_clean = f"{symbol_clean}USDT"
        caption = f"📊 <b>{symbol_clean}</b> 15min K线 + 清算热力"
    
    return send_telegram_photo(chart_data, caption=caption)


def test_chart(symbol='BTC'):
    """测试图表生成"""
    import os
    
    logger.info(f"🧪 测试增强图表生成: ${symbol}")
    
    image_data = generate_chart_free(symbol, interval='15m', limit=60)
    
    if image_data:
        os.makedirs('output', exist_ok=True)
        output_path = f'output/chart_{symbol}_15m_heatmap.png'
        with open(output_path, 'wb') as f:
            f.write(image_data)
        logger.info(f"✅ 测试成功！图片已保存: {output_path}")
        return True
    else:
        logger.error("❌ 测试失败")
        return False


if __name__ == '__main__':
    test_chart('BTC')
    test_chart('ETH')
