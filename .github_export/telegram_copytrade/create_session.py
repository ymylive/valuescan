#!/usr/bin/env python3
"""
本地创建 Telegram Session 文件
运行此脚本后会要求输入手机号和验证码，完成后生成 session 文件
"""
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import socks

# 公开测试 API 凭证 (Telegram官方测试)
API_ID = 94575
API_HASH = "a3406de8d171bb422bb6ddf3bbd800e2"

# 代理配置 (SOCKS5)
PROXY = (socks.SOCKS5, '127.0.0.1', 1080)

async def main():
    print("="*50)
    print("Telegram Session 创建工具")
    print("="*50)
    
    # 创建客户端（使用代理）
    client = TelegramClient(StringSession(), API_ID, API_HASH, proxy=PROXY)
    
    await client.start()
    
    # 获取session字符串
    session_string = client.session.save()
    
    print("\n" + "="*50)
    print("✅ 登录成功！")
    print("="*50)
    print("\n你的 Session 字符串（保存好，不要泄露）：\n")
    print(session_string)
    print("\n" + "="*50)
    
    # 保存到文件
    with open("telegram_session.txt", "w") as f:
        f.write(session_string)
    print("已保存到 telegram_session.txt")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
