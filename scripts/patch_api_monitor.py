#!/usr/bin/env python3
"""修改 api_monitor.py 注入 localStorage"""
import json

# 读取 localStorage
with open('/opt/valuescan/signal_monitor/valuescan_localstorage.json', 'r') as f:
    ls_data = json.load(f)

account_token = ls_data.get('account_token', '')
refresh_token = ls_data.get('refresh_token', '')

# 读取 api_monitor.py
with open('/opt/valuescan/signal_monitor/api_monitor.py', 'r') as f:
    content = f.read()

# 检查是否已经有注入代码
if 'inject_localstorage' not in content:
    # 在 page.get 之后添加注入代码
    inject_code = f'''
                # 注入 localStorage (自动添加)
                def inject_localstorage(p):
                    try:
                        p.run_js(f"""
                            localStorage.setItem('account_token', '{account_token}');
                            localStorage.setItem('refresh_token', '{refresh_token}');
                            localStorage.setItem('language', 'en-US');
                        """)
                        logger.info("✅ localStorage 已注入")
                    except Exception as e:
                        logger.warning(f"localStorage 注入失败: {{e}}")
                
                inject_localstorage(page)
                page.refresh()
                time.sleep(2)
'''
    
    # 在 page.get 后添加
    old_code = "page.get('https://www.valuescan.io/GEMs/signals')\n                time.sleep(2)  # 绛夊緟椤甸潰鍔犺浇"
    new_code = "page.get('https://www.valuescan.io/GEMs/signals')\n                time.sleep(2)  # 绛夊緟椤甸潰鍔犺浇" + inject_code
    
    content = content.replace(old_code, new_code)
    
    with open('/opt/valuescan/signal_monitor/api_monitor.py', 'w') as f:
        f.write(content)
    
    print("✅ api_monitor.py 已修改，添加了 localStorage 注入")
else:
    print("已有注入代码，跳过修改")
