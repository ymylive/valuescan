"""
交易员评测图表生成模块
生成可视化图表用于 Telegram 发送
"""

import io
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    from matplotlib.patches import Wedge, FancyBboxPatch
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def setup_chinese_font():
    """配置中文字体 - 确保支持中文显示，修复乱码问题"""
    # Linux 字体优先（VPS环境）
    linux_fonts = [
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',  # 文泉驿微米黑
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',    # 文泉驿正黑
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',  # Noto Sans CJK
        '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
    ]

    for font_path in linux_fonts:
        if os.path.exists(font_path):
            try:
                fm.fontManager.addfont(font_path)
                font_name = fm.FontProperties(fname=font_path).get_name()
                plt.rcParams['font.sans-serif'] = [font_name, 'DejaVu Sans']
                plt.rcParams['axes.unicode_minus'] = False
                plt.rcParams['font.family'] = 'sans-serif'
                return True, font_name
            except Exception:
                continue

    # 字体名称候选列表
    font_candidates = [
        'WenQuanYi Micro Hei',  # 文泉驿微米黑 (Linux)
        'WenQuanYi Zen Hei',    # 文泉驿正黑 (Linux)
        'Noto Sans CJK SC',     # 思源黑体 (Linux)
        'Microsoft YaHei',      # 微软雅黑 (Windows)
        'SimHei',               # 黑体 (Windows)
        'PingFang SC',          # 苹方 (macOS)
    ]

    for font in font_candidates:
        try:
            font_path = fm.findfont(fm.FontProperties(family=font))
            if font_path and 'DejaVu' not in font_path and os.path.exists(font_path):
                plt.rcParams['font.sans-serif'] = [font, 'DejaVu Sans']
                plt.rcParams['axes.unicode_minus'] = False
                plt.rcParams['font.family'] = 'sans-serif'
                return True, font
        except Exception:
            continue

    # Windows 字体文件
    windows_fonts = [
        'C:/Windows/Fonts/msyh.ttc',
        'C:/Windows/Fonts/simhei.ttf',
    ]

    for font_path in windows_fonts:
        if os.path.exists(font_path):
            try:
                fm.fontManager.addfont(font_path)
                font_name = fm.FontProperties(fname=font_path).get_name()
                plt.rcParams['font.sans-serif'] = [font_name, 'DejaVu Sans']
                plt.rcParams['axes.unicode_minus'] = False
                plt.rcParams['font.family'] = 'sans-serif'
                return True, font_name
            except Exception:
                continue

    # 回退到默认字体（英文）
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    return False, 'DejaVu Sans (fallback)'


# 检测是否有中文字体
HAS_CHINESE_FONT = False
FONT_NAME = 'DejaVu Sans'
if HAS_MATPLOTLIB:
    HAS_CHINESE_FONT, FONT_NAME = setup_chinese_font()


# 标签映射（中英文）
LABELS = {
    'roi_curve': 'ROI Curve (90D)' if not HAS_CHINESE_FONT else '收益曲线 (90天)',
    'risk_radar': 'Risk Radar' if not HAS_CHINESE_FONT else '风险雷达',
    'pair_dist': 'Pair Distribution' if not HAS_CHINESE_FONT else '交易对分布',
    'core_metrics': 'Core Metrics' if not HAS_CHINESE_FONT else '核心指标',
    'risk_score': 'Risk Score' if not HAS_CHINESE_FONT else '风险评分',
    'recommendation': 'Recommendation' if not HAS_CHINESE_FONT else '跟随建议',
    'no_data': 'No Data' if not HAS_CHINESE_FONT else '暂无数据',
    'leverage': 'Leverage' if not HAS_CHINESE_FONT else '杠杆',
    'drawdown': 'Drawdown' if not HAS_CHINESE_FONT else '回撤',
    'margin': 'Margin' if not HAS_CHINESE_FONT else '保证金',
    'stoploss': 'StopLoss' if not HAS_CHINESE_FONT else '止损',
    'winrate': 'WinRate' if not HAS_CHINESE_FONT else '胜率',
    'roi_90d': '90D ROI' if not HAS_CHINESE_FONT else '90天收益',
    'max_dd': 'Max DD' if not HAS_CHINESE_FONT else '最大回撤',
    'avg_lev': 'Avg Lev' if not HAS_CHINESE_FONT else '平均杠杆',
    'followers': 'Followers' if not HAS_CHINESE_FONT else '跟随者',
    'low': 'Low' if not HAS_CHINESE_FONT else '低',
    'medium': 'Medium' if not HAS_CHINESE_FONT else '中',
    'high': 'High' if not HAS_CHINESE_FONT else '高',
    'extreme': 'Extreme' if not HAS_CHINESE_FONT else '极高',
    'strongly_recommend': 'Strong Buy' if not HAS_CHINESE_FONT else '强烈推荐',
    'recommend': 'Buy' if not HAS_CHINESE_FONT else '推荐',
    'neutral': 'Neutral' if not HAS_CHINESE_FONT else '中性',
    'caution': 'Caution' if not HAS_CHINESE_FONT else '警告',
    'avoid': 'Avoid' if not HAS_CHINESE_FONT else '回避',
    'copy_ratio': 'Copy Ratio' if not HAS_CHINESE_FONT else '建议跟单比例',
    'margin_warn': 'Margin Add' if not HAS_CHINESE_FONT else '保证金添加',
    'trader_eval': 'Trader Evaluation' if not HAS_CHINESE_FONT else '交易员评测',
}


# 颜色配置 - 现代深色主题（GitHub Dark风格）
COLORS = {
    # 背景色
    'bg': '#0d1117',           # 主背景
    'card': '#161b22',         # 卡片背景
    'card_border': '#30363d',  # 边框色

    # 文字色
    'text': '#f0f6fc',         # 主文字
    'text_secondary': '#8b949e', # 次要文字
    'text_dim': '#6e7681',     # 暗淡文字

    # 强调色
    'green': '#3fb950',        # 正向/成功
    'green_light': '#56d364',  # 亮绿
    'red': '#f85149',          # 负向/危险
    'red_dark': '#da3633',     # 深红
    'yellow': '#d29922',       # 警告
    'orange': '#db6d28',       # 注意
    'blue': '#58a6ff',         # 信息/链接
    'purple': '#a371f7',       # 特殊
    'cyan': '#39c5cf',         # 高亮
    'pink': '#db61a2',         # 强调

    # 图表专用
    'grid': '#21262d',         # 网格线
    'axis': '#484f58',         # 坐标轴
    'gray': '#6e7681',         # 灰色
}


def generate_trader_charts(trader_data, metrics, evaluation: Dict) -> Optional[bytes]:
    """生成交易员评测图表 - 优化版"""
    if not HAS_MATPLOTLIB:
        return None

    # 增大图表尺寸，提高清晰度
    fig = plt.figure(figsize=(14, 12), facecolor=COLORS['bg'])

    # 优化子图布局，增加间距
    gs = fig.add_gridspec(3, 3, hspace=0.4, wspace=0.35,
                          left=0.06, right=0.94, top=0.92, bottom=0.06)

    # 1. ROI 曲线 (左上，占2列)
    ax1 = fig.add_subplot(gs[0, :2])
    _draw_roi_curve(ax1, trader_data)

    # 2. 风险雷达图 (右上)
    ax2 = fig.add_subplot(gs[0, 2], projection='polar')
    _draw_risk_radar(ax2, metrics, evaluation)

    # 3. 持仓分布饼图 (中左)
    ax3 = fig.add_subplot(gs[1, 0])
    _draw_pair_distribution(ax3, trader_data, metrics)

    # 4. 表现指标 (中中)
    ax4 = fig.add_subplot(gs[1, 1])
    _draw_performance_stats(ax4, metrics)

    # 5. 风险评分仪表盘 (中右)
    ax5 = fig.add_subplot(gs[1, 2])
    _draw_risk_gauge(ax5, evaluation)

    # 6. 跟随建议 (底部，占3列)
    ax6 = fig.add_subplot(gs[2, :])
    _draw_recommendation(ax6, metrics, evaluation)

    # 标题
    title = f"{LABELS['trader_eval']}: {metrics.nickname}"
    fig.suptitle(title, fontsize=18, color=COLORS['text'], fontweight='bold')

    # 保存为字节 - 提高DPI以获得更清晰的图像
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, facecolor=COLORS['bg'],
                bbox_inches='tight', pad_inches=0.2)
    buf.seek(0)
    plt.close(fig)

    return buf.read()


def _draw_roi_curve(ax, trader_data):
    """绘制 ROI 曲线"""
    ax.set_facecolor(COLORS['card'])

    roi_curve = getattr(trader_data, 'roi_curve', []) or []

    if roi_curve and len(roi_curve) > 1:
        times = list(range(len(roi_curve)))
        values = []
        for p in roi_curve:
            if isinstance(p, dict):
                v = p.get('roi', p.get('value', 0))
            else:
                v = p
            try:
                values.append(float(v))
            except:
                values.append(0)

        if values:
            # 填充颜色
            color = COLORS['green'] if values[-1] >= 0 else COLORS['red']
            ax.fill_between(times, values, alpha=0.3, color=color)
            ax.plot(times, values, color=color, linewidth=2)
            # 零线
            ax.axhline(y=0, color=COLORS['gray'], linestyle='--', alpha=0.5)
            # 最新值标注
            ax.annotate(f'{values[-1]:.1f}%', xy=(times[-1], values[-1]),
                       color=color, fontsize=10, fontweight='bold')
    else:
        ax.text(0.5, 0.5, LABELS['no_data'], ha='center', va='center',
                color=COLORS['gray'], fontsize=12, transform=ax.transAxes)

    ax.set_title(LABELS['roi_curve'], color=COLORS['text'], fontsize=11)
    ax.tick_params(colors=COLORS['text_dim'], labelsize=8)
    for spine in ['bottom', 'left']:
        ax.spines[spine].set_color(COLORS['card_border'])
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)


def _draw_risk_radar(ax, metrics, evaluation):
    """绘制风险雷达图"""
    categories = [LABELS['leverage'], LABELS['drawdown'], LABELS['margin'],
                  LABELS['stoploss'], LABELS['winrate']]
    N = len(categories)

    # 计算各维度分数 (0-100，越高越好)
    leverage_score = max(0, min(100, 100 - getattr(metrics, 'avg_leverage', 10) * 4))
    drawdown_score = max(0, min(100, 100 - getattr(metrics, 'max_drawdown', 50) * 2))
    margin_ratio = getattr(metrics, 'margin_addition_ratio', 0) or 0
    margin_score = max(0, min(100, 100 - margin_ratio * 500))
    stoploss_score = min(100, (getattr(metrics, 'stop_loss_usage_rate', 0) or 0) * 100)
    winrate_score = min(100, (getattr(metrics, 'win_rate', 0) or 0) * 100)

    values = [leverage_score, drawdown_score, margin_score, stoploss_score, winrate_score]
    values += values[:1]  # 闭合

    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]

    ax.set_facecolor(COLORS['card'])
    ax.plot(angles, values, 'o-', linewidth=2, color=COLORS['cyan'], markersize=4)
    ax.fill(angles, values, alpha=0.25, color=COLORS['cyan'])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, color=COLORS['text'], fontsize=8)
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(['25', '50', '75', '100'], color=COLORS['text_dim'], fontsize=7)
    ax.spines['polar'].set_color(COLORS['card_border'])


def _draw_pair_distribution(ax, trader_data, metrics):
    """绘制交易对分布 - 使用真实数据"""
    ax.set_facecolor(COLORS['card'])

    # 优先使用 coin_distribution 真实数据
    coin_dist = getattr(trader_data, 'coin_distribution', []) or []

    if coin_dist and len(coin_dist) > 0:
        # 从真实数据提取 - 支持多种API字段名
        pairs = []
        sizes = []
        for item in coin_dist[:5]:  # 最多显示5个
            if isinstance(item, dict):
                # 支持多种字段名: symbol, coin, asset
                symbol = item.get('symbol', item.get('coin', item.get('asset', 'Unknown')))
                # 支持多种比例字段: ratio, percentage, pnlRatio, volume
                ratio = item.get('ratio', item.get('percentage', item.get('pnlRatio', item.get('volume', 0))))
                try:
                    ratio = float(ratio)
                    # 如果是小数形式(0-1)，转换为百分比
                    if ratio <= 1:
                        ratio = ratio * 100
                except:
                    ratio = 0
                pairs.append(symbol.replace('USDT', ''))
                sizes.append(max(ratio, 1))  # 至少1%避免显示问题
    else:
        # 回退到 preferred_pairs
        pref_pairs = getattr(metrics, 'preferred_pairs', []) or []
        if pref_pairs:
            pairs = [p.replace('USDT', '') for p in pref_pairs[:5]]
            # 估算分布
            total = len(pairs)
            sizes = [100 / total] * total
        else:
            pairs = ['BTC', 'ETH', 'Other']
            sizes = [40, 35, 25]

    if not pairs:
        ax.text(0.5, 0.5, LABELS['no_data'], ha='center', va='center',
                color=COLORS['gray'], fontsize=12, transform=ax.transAxes)
        ax.axis('off')
        return

    colors = [COLORS['cyan'], COLORS['green'], COLORS['yellow'],
              COLORS['purple'], COLORS['blue']][:len(pairs)]

    wedges, texts, autotexts = ax.pie(
        sizes, labels=pairs, autopct='%1.0f%%',
        colors=colors,
        textprops={'color': COLORS['text'], 'fontsize': 9},
        wedgeprops={'edgecolor': COLORS['card_border'], 'linewidth': 1}
    )
    for autotext in autotexts:
        autotext.set_fontsize(8)
        autotext.set_color(COLORS['text'])

    ax.set_title(LABELS['pair_dist'], color=COLORS['text'], fontsize=11)


def _draw_performance_stats(ax, metrics):
    """绘制表现指标"""
    ax.set_facecolor(COLORS['card'])
    ax.axis('off')

    roi_90d = getattr(metrics, 'roi_90d', 0) or 0
    win_rate = getattr(metrics, 'win_rate', 0) or 0
    max_dd = getattr(metrics, 'max_drawdown', 0) or 0
    avg_lev = getattr(metrics, 'avg_leverage', 0) or 0
    followers = getattr(metrics, 'follower_count', 0) or 0

    stats = [
        (LABELS['roi_90d'], f"{roi_90d:+.1f}%",
         COLORS['green'] if roi_90d >= 0 else COLORS['red']),
        (LABELS['winrate'], f"{win_rate:.1%}", COLORS['text']),
        (LABELS['max_dd'], f"{max_dd:.1f}%", COLORS['red']),
        (LABELS['avg_lev'], f"{avg_lev:.1f}x", COLORS['yellow'] if avg_lev > 10 else COLORS['text']),
        (LABELS['followers'], f"{followers:,}", COLORS['cyan']),
    ]

    for i, (label, value, color) in enumerate(stats):
        y = 0.85 - i * 0.17
        ax.text(0.1, y, label, color=COLORS['text_dim'], fontsize=10,
                transform=ax.transAxes, va='center')
        ax.text(0.9, y, value, color=color, fontsize=11, fontweight='bold',
                transform=ax.transAxes, va='center', ha='right')

    ax.set_title(LABELS['core_metrics'], color=COLORS['text'], fontsize=11)


def _draw_risk_gauge(ax, evaluation):
    """绘制风险评分仪表盘"""
    ax.set_facecolor(COLORS['card'])
    ax.axis('off')
    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-0.5, 1.5)

    risk = evaluation.get('risk_assessment', {}) if evaluation else {}
    score = risk.get('score', 50)

    # 背景弧
    for i, (start, end, color) in enumerate([
        (0, 40, COLORS['green']),
        (40, 60, COLORS['yellow']),
        (60, 80, COLORS['red']),
        (80, 100, COLORS['red_dark']),
    ]):
        theta1 = 180 - start * 1.8
        theta2 = 180 - end * 1.8
        wedge = Wedge((0, 0), 1.2, theta2, theta1, width=0.3, facecolor=color, alpha=0.3)
        ax.add_patch(wedge)

    # 指针
    angle = np.radians(180 - score * 1.8)
    ax.arrow(0, 0, 0.9 * np.cos(angle), 0.9 * np.sin(angle),
             head_width=0.1, head_length=0.05, fc=COLORS['text'], ec=COLORS['text'])

    # 分数
    ax.text(0, -0.3, f"{score}", fontsize=24, fontweight='bold',
            color=COLORS['text'], ha='center', va='center')
    ax.text(0, -0.55, LABELS['risk_score'], fontsize=10, color=COLORS['text_dim'],
            ha='center', va='center')

    # 等级标签
    level = risk.get('level', 'medium')
    level_labels = {
        'low': LABELS['low'], 'medium': LABELS['medium'],
        'high': LABELS['high'], 'extreme': LABELS['extreme']
    }
    level_colors = {
        'low': COLORS['green'], 'medium': COLORS['yellow'],
        'high': COLORS['red'], 'extreme': COLORS['red_dark']
    }
    ax.text(0, 0.3, level_labels.get(level, LABELS['medium']),
            fontsize=14, color=level_colors.get(level, COLORS['yellow']),
            ha='center', va='center', fontweight='bold')


def _draw_recommendation(ax, metrics, evaluation):
    """绘制跟随建议"""
    ax.set_facecolor(COLORS['card'])
    ax.axis('off')

    rec = evaluation.get('follow_recommendation', {}) if evaluation else {}
    verdict = rec.get('verdict', 'neutral')

    verdict_info = {
        'strongly_recommend': (LABELS['strongly_recommend'], COLORS['green']),
        'recommend': (LABELS['recommend'], COLORS['green']),
        'neutral': (LABELS['neutral'], COLORS['yellow']),
        'caution': (LABELS['caution'], COLORS['red']),
        'avoid': (LABELS['avoid'], COLORS['red_dark']),
    }

    label, color = verdict_info.get(verdict, (LABELS['neutral'], COLORS['yellow']))

    # 主建议
    ax.text(0.5, 0.75, f"{LABELS['recommendation']}: {label}",
            fontsize=16, color=color, fontweight='bold',
            ha='center', va='center', transform=ax.transAxes)

    # 建议比例
    ratio = rec.get('suggested_copy_ratio', 0.5)
    ax.text(0.5, 0.5, f"{LABELS['copy_ratio']}: {ratio:.0%}",
            fontsize=12, color=COLORS['text'],
            ha='center', va='center', transform=ax.transAxes)

    # 理由
    reasoning = rec.get('reasoning', '')
    if reasoning:
        if len(reasoning) > 60:
            reasoning = reasoning[:57] + '...'
        ax.text(0.5, 0.25, reasoning,
                fontsize=10, color=COLORS['text_dim'],
                ha='center', va='center', transform=ax.transAxes)

    # 保证金警告
    margin = evaluation.get('margin_behavior', {}) if evaluation else {}
    if margin.get('concern_level') in ['medium', 'high']:
        freq = margin.get('frequency', 'Unknown')
        ax.text(0.5, 0.05, f"⚠ {LABELS['margin_warn']}: {freq}",
                fontsize=10, color=COLORS['red'],
                ha='center', va='center', transform=ax.transAxes)


def generate_simple_chart(metrics) -> Optional[bytes]:
    """生成简化版图表（无 AI 评测时使用）"""
    if not HAS_MATPLOTLIB:
        return None

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), facecolor=COLORS['bg'])

    # 左图：核心指标
    ax1 = axes[0]
    ax1.set_facecolor(COLORS['card'])
    ax1.axis('off')

    roi_90d = getattr(metrics, 'roi_90d', 0) or 0
    win_rate = getattr(metrics, 'win_rate', 0) or 0
    max_dd = getattr(metrics, 'max_drawdown', 0) or 0
    avg_lev = getattr(metrics, 'avg_leverage', 0) or 0
    margin_ratio = getattr(metrics, 'margin_addition_ratio', 0) or 0

    stats = [
        ('Nickname', getattr(metrics, 'nickname', 'Unknown'), COLORS['text']),
        (LABELS['roi_90d'], f"{roi_90d:+.1f}%",
         COLORS['green'] if roi_90d >= 0 else COLORS['red']),
        (LABELS['winrate'], f"{win_rate:.1%}", COLORS['text']),
        (LABELS['max_dd'], f"{max_dd:.1f}%", COLORS['red']),
        (LABELS['avg_lev'], f"{avg_lev:.1f}x", COLORS['text']),
        (LABELS['margin_warn'], f"{margin_ratio:.1%}",
         COLORS['red'] if margin_ratio > 0.1 else COLORS['text']),
    ]

    for i, (label, value, color) in enumerate(stats):
        y = 0.9 - i * 0.15
        ax1.text(0.1, y, label, color=COLORS['text_dim'], fontsize=11, transform=ax1.transAxes)
        ax1.text(0.9, y, str(value), color=color, fontsize=11, fontweight='bold',
                 transform=ax1.transAxes, ha='right')

    ax1.set_title('Trader Data', color=COLORS['text'], fontsize=12)

    # 右图：风险评估
    ax2 = axes[1]
    ax2.set_facecolor(COLORS['card'])
    ax2.axis('off')

    risk_score = getattr(metrics, 'risk_score', 50) or 50
    risk_level = getattr(metrics, 'risk_level', 'medium') or 'medium'

    ax2.text(0.5, 0.7, f"Risk Score: {risk_score}/100",
             fontsize=14, color=COLORS['text'], ha='center', transform=ax2.transAxes)

    level_colors = {
        'low': COLORS['green'], 'medium': COLORS['yellow'],
        'high': COLORS['red'], 'extreme': COLORS['red_dark']
    }
    level_labels = {
        'low': 'Low Risk', 'medium': 'Medium Risk',
        'high': 'High Risk', 'extreme': 'Extreme Risk'
    }

    ax2.text(0.5, 0.4, level_labels.get(risk_level, 'Medium Risk'),
             fontsize=16, color=level_colors.get(risk_level, COLORS['yellow']),
             ha='center', fontweight='bold', transform=ax2.transAxes)

    ax2.set_title('Risk Assessment', color=COLORS['text'], fontsize=12)

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=120, facecolor=COLORS['bg'])
    buf.seek(0)
    plt.close(fig)

    return buf.read()
