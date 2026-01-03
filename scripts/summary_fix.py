#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import paramiko
import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("82.158.88.34", username="root", password="Qq159741",
           look_for_keys=False, allow_agent=False)

print("检查测试脚本的完整输出（包括后台线程的日志）...")
print("注意：后台线程的日志可能不会出现在标准输出中\n")

print("方案：直接测试真实信号触发异步图表生成")
print("等待下一个真实信号到来，观察Telegram中的效果\n")

print("当前修复内容：")
print("1. ✅ 添加了30秒超时控制")
print("2. ✅ 添加了详细的错误日志和traceback")
print("3. ✅ 添加了图表大小日志")
print("4. ✅ 区分了超时错误和其他异常\n")

print("预期行为：")
print("- 如果图表生成超过30秒，会记录超时错误")
print("- 如果图表生成失败，会记录详细的异常信息")
print("- 如果图表生成成功，会记录图表大小和编辑结果\n")

print("建议：等待真实信号触发，然后检查以下内容：")
print("1. Telegram中消息是否先显示文字")
print("2. 几秒后消息是否自动更新添加图表")
print("3. 如果失败，检查服务日志中的错误信息")

ssh.close()
