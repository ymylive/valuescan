#!/usr/bin/env python3
"""
从浏览器 localStorage 提取 ValueScan token 的辅助脚本。

使用方法：
1. 在浏览器中登录 valuescan.io
2. 打开开发者工具 (F12) -> Console
3. 运行以下代码获取 token:
   
   console.log(JSON.stringify({
     account_token: localStorage.getItem('account_token'),
     refresh_token: localStorage.getItem('refresh_token'),
     language: localStorage.getItem('language') || 'en-US'
   }, null, 2))

4. 复制输出的 JSON
5. 运行此脚本: python extract_valuescan_token.py
6. 粘贴 JSON 内容，按 Enter 两次完成
"""

import json
import sys
from pathlib import Path


def main():
    print("=" * 60)
    print("ValueScan Token 提取工具")
    print("=" * 60)
    print()
    print("请在浏览器控制台运行以下代码获取 token:")
    print()
    print("  console.log(JSON.stringify({")
    print("    account_token: localStorage.getItem('account_token'),")
    print("    refresh_token: localStorage.getItem('refresh_token'),")
    print("    language: localStorage.getItem('language') || 'en-US'")
    print("  }, null, 2))")
    print()
    print("然后粘贴输出的 JSON 到这里 (输入完成后按两次 Enter):")
    print()
    
    lines = []
    empty_count = 0
    while empty_count < 2:
        try:
            line = input()
            if not line.strip():
                empty_count += 1
            else:
                empty_count = 0
                lines.append(line)
        except EOFError:
            break
    
    if not lines:
        print("错误: 未输入任何内容")
        return 1
    
    json_str = "\n".join(lines)
    
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"错误: JSON 解析失败 - {e}")
        return 1
    
    account_token = (data.get("account_token") or "").strip()
    refresh_token = (data.get("refresh_token") or "").strip()
    
    if not account_token:
        print("错误: 未找到 account_token")
        print("请确保已在 valuescan.io 登录")
        return 1
    
    # 准备保存的数据
    token_data = {
        "account_token": account_token,
        "refresh_token": refresh_token,
        "language": data.get("language") or "en-US"
    }
    
    # 确定保存路径
    script_dir = Path(__file__).resolve().parent
    base_dir = script_dir.parent
    
    # 优先保存到 signal_monitor 目录
    signal_monitor_dir = base_dir / "signal_monitor"
    if signal_monitor_dir.exists():
        output_path = signal_monitor_dir / "valuescan_localstorage.json"
    else:
        output_path = base_dir / "valuescan_localstorage.json"
    
    # 保存文件
    try:
        output_path.write_text(
            json.dumps(token_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        print()
        print("=" * 60)
        print("✅ Token 保存成功!")
        print(f"   文件: {output_path}")
        print()
        print(f"   account_token: {account_token[:20]}...{account_token[-10:]}")
        print(f"   refresh_token: {refresh_token[:20] if refresh_token else '(空)'}...")
        print("=" * 60)
        print()
        print("下一步:")
        print("  1. 重启信号监控服务:")
        print("     sudo systemctl restart valuescan-signal")
        print("  2. 或本地运行:")
        print("     cd signal_monitor && python start_with_chrome.py")
        return 0
    except Exception as e:
        print(f"错误: 保存文件失败 - {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
