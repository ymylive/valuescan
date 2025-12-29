#!/usr/bin/env python3
"""移除导致超时的 localStorage 注入代码"""
with open('/opt/valuescan/signal_monitor/api_monitor.py', 'r') as f:
    content = f.read()

# 移除 AUTO_INJECT_TOKEN 代码块
if 'AUTO_INJECT_TOKEN' in content:
    lines = content.split('\n')
    new_lines = []
    skip = False
    for line in lines:
        if 'AUTO_INJECT_TOKEN' in line:
            skip = True
            continue
        if skip and 'localStorage 娉ㄥ叆澶辫触' in line:
            skip = False
            continue
        if skip and ('page.refresh()' in line or 'logger.warning' in line):
            continue
        if not skip:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    with open('/opt/valuescan/signal_monitor/api_monitor.py', 'w') as f:
        f.write(content)
    print("Removed AUTO_INJECT_TOKEN code")
else:
    print("No AUTO_INJECT_TOKEN found")
