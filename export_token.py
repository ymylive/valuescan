#!/usr/bin/env python3
"""
Token 导出工具 - 从浏览器导出 valuescan.io 的 localStorage token

使用方法:
1. 打开 Chrome 浏览器，访问 https://www.valuescan.io 并登录
2. 运行此脚本: python export_token.py
3. 脚本会自动连接到 Chrome 并导出 token

或者手动导出:
1. 打开 valuescan.io，按 F12 打开开发者工具
2. 在 Console 中输入: copy(JSON.stringify(localStorage))
3. 粘贴到文件保存为 valuescan_localstorage.json
"""

import json
import sys
from pathlib import Path

def export_from_chrome_cdp(port: int = 9222) -> dict:
    """通过 Chrome DevTools Protocol 导出 localStorage"""
    import requests

    try:
        # 获取可用的页面
        resp = requests.get(f"http://127.0.0.1:{port}/json", timeout=5)
        pages = resp.json()

        # 找到 valuescan 页面
        target = None
        for page in pages:
            if "valuescan" in page.get("url", "").lower():
                target = page
                break

        if not target:
            print("未找到 valuescan.io 页面，请先在 Chrome 中打开该网站")
            return {}

        ws_url = target.get("webSocketDebuggerUrl")
        if not ws_url:
            print("无法获取 WebSocket URL")
            return {}

        # 使用 websocket 连接
        import websocket
        ws = websocket.create_connection(ws_url)

        # 执行 JavaScript 获取 localStorage
        cmd = {
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {
                "expression": "JSON.stringify(localStorage)",
                "returnByValue": True
            }
        }
        ws.send(json.dumps(cmd))
        result = json.loads(ws.recv())
        ws.close()

        if "result" in result and "result" in result["result"]:
            value = result["result"]["result"].get("value", "{}")
            return json.loads(value)

        return {}
    except Exception as e:
        print(f"CDP 连接失败: {e}")
        return {}


def main():
    output_file = Path(__file__).parent / "signal_monitor" / "valuescan_localstorage.json"

    print("=" * 50)
    print("ValuScan Token 导出工具")
    print("=" * 50)

    # 尝试 CDP 方式
    print("\n尝试通过 Chrome DevTools Protocol 导出...")
    data = export_from_chrome_cdp()

    if data:
        output_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n✅ Token 已导出到: {output_file}")

        # 检查 token 是否有效
        token = data.get("account_token") or data.get("accessToken") or data.get("token")
        if token:
            print(f"✅ 找到有效 token (长度: {len(token)})")
        else:
            print("⚠️ 未找到 token，请确保已登录 valuescan.io")
    else:
        print("\n❌ 自动导出失败")
        print("\n请手动导出:")
        print("1. 打开 Chrome，访问 https://www.valuescan.io 并登录")
        print("2. 按 F12 打开开发者工具")
        print("3. 切换到 Console 标签")
        print("4. 输入以下命令并回车:")
        print("   copy(JSON.stringify(localStorage))")
        print("5. 粘贴到文件保存为:")
        print(f"   {output_file}")


if __name__ == "__main__":
    main()
