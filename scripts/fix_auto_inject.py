#!/usr/bin/env python3
"""修改 api_monitor.py 在页面加载后自动注入 localStorage"""
import json

# 读取 tokens
with open('/opt/valuescan/signal_monitor/valuescan_localstorage.json', 'r') as f:
    ls_data = json.load(f)

account_token = ls_data.get('account_token', '')
refresh_token = ls_data.get('refresh_token', '')

# 读取 api_monitor.py
with open('/opt/valuescan/signal_monitor/api_monitor.py', 'r') as f:
    content = f.read()

# 检查是否已有注入代码
if 'AUTO_INJECT_TOKEN' not in content:
    # 在 "网站已自动打开" 后添加注入代码
    inject_code = f'''
                # AUTO_INJECT_TOKEN - 自动注入登录 token
                try:
                    page.run_js("""
                        localStorage.setItem('account_token', '{account_token}');
                        localStorage.setItem('refresh_token', '{refresh_token}');
                        localStorage.setItem('language', 'en-US');
                    """)
                    logger.info("✅ localStorage token 已注入")
                    page.refresh()
                    time.sleep(2)
                    logger.info("✅ 页面已刷新")
                except Exception as e:
                    logger.warning(f"localStorage 注入失败: {{e}}")
'''
    
    # 找到 "网站已自动打开" 的位置并在其后添加
    old_text = 'logger.info("✓ 网站已自动打开")'
    if old_text in content:
        content = content.replace(old_text, old_text + inject_code)
        with open('/opt/valuescan/signal_monitor/api_monitor.py', 'w') as f:
            f.write(content)
        print("✅ 已添加自动注入 token 代码")
    else:
        print("❌ 未找到插入点，尝试其他方式...")
        # 尝试其他关键字
        for marker in ['缃戠珯宸茶嚜鍔ㄦ墦寮', '网站已自动打开']:
            if marker in content:
                idx = content.find(marker)
                line_end = content.find('\n', idx)
                content = content[:line_end] + inject_code + content[line_end:]
                with open('/opt/valuescan/signal_monitor/api_monitor.py', 'w') as f:
                    f.write(content)
                print(f"✅ 已在 '{marker}' 后添加注入代码")
                break
else:
    print("已有注入代码，跳过")
