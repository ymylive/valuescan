#!/usr/bin/env python3
"""
测试 CDP Token 刷新器
Test script for CDP token refresher
"""
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from simple_cdp_refresher import (
    find_chrome,
    start_chrome,
    stop_chrome,
    load_credentials,
    ComponentManager
)


def test_find_chrome():
    """测试查找 Chrome"""
    print("测试查找 Chrome...")
    chrome_path = find_chrome()
    if chrome_path:
        print(f"[OK] 找到 Chrome: {chrome_path}")
        return True
    else:
        print("[FAIL] 未找到 Chrome")
        return False


def test_load_credentials():
    """测试加载凭证"""
    print("\n测试加载凭证...")
    email, password = load_credentials()
    if email and password:
        print(f"[OK] 凭证已加载: {email}")
        return True
    else:
        print("[FAIL] 未找到凭证")
        return False


def test_chrome_lifecycle():
    """测试 Chrome 生命周期"""
    print("\n测试 Chrome 启动和停止...")
    proc = start_chrome()
    if proc:
        print("[OK] Chrome 已启动")
        import time
        time.sleep(2)
        stop_chrome(proc)
        print("[OK] Chrome 已停止")
        return True
    else:
        print("[FAIL] Chrome 启动失败")
        return False


def main():
    """运行所有测试"""
    print("=" * 50)
    print("CDP Token 刷新器测试")
    print("=" * 50)

    results = []
    results.append(("查找 Chrome", test_find_chrome()))
    results.append(("加载凭证", test_load_credentials()))
    results.append(("Chrome 生命周期", test_chrome_lifecycle()))

    print("\n" + "=" * 50)
    print("测试结果:")
    print("=" * 50)
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{name}: {status}")

    all_passed = all(r[1] for r in results)
    print("\n总体:", "[PASS] 所有测试通过" if all_passed else "[FAIL] 部分测试失败")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
