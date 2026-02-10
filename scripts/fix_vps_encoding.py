#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix encoding issues in ai_signal_scheduler.py on VPS"""
import codecs

path = '/root/valuescan/signal_monitor/ai_signal_scheduler.py'

with codecs.open(path, 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

# Chinese strings
cn1 = '\u3010\u5b9e\u65f6\u884c\u60c5\u3011'  # 【实时行情】
cn2 = '\u5317\u4eac\u65f6\u95f4'  # 北京时间
cn3 = '\u4ef7\u683c'  # 价格
cn4 = '24H\u6da8\u8dcc'  # 24H涨跌
cn5 = '24H\u6210\u4ea4\u91cf'  # 24H成交量
cn6 = '\u6570\u636e\u6e90'  # 数据源

new_lines = []
for i, line in enumerate(lines):
    ln = i + 1
    if ln == 471:
        line = '    lines = [f"' + cn1 + '{symbol}", f"' + cn2 + ': {now_bj}"]\n'
    elif ln == 478:
        line = '            lines.append(f"' + cn3 + ': {price:,.4f}")\n'
    elif ln == 480:
        line = '            lines.append(f"' + cn4 + ': {change:,.2f}%")\n'
    elif ln == 482:
        line = '            lines.append(f"' + cn5 + ': {vol:,.2f}")\n'
    elif ln == 484:
        line = '            lines.append(f"' + cn6 + ': {source}")\n'
    new_lines.append(line)

with codecs.open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('Fixed encoding successfully!')
