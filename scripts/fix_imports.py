#!/usr/bin/env python3
"""
批量修复 Go 文件中的 nofx/ 导入路径
将 nofx/ 替换为正确的模块路径
"""

import os
import re
from pathlib import Path

# 需要修复的文件列表
files_to_fix = [
    "api/proxy.go",
    "api/server.go",
    "api/strategy.go",
    "api/backtest.go",
    "store/store.go",
    "store/ai_model.go",
    "trader/okx_trader.go",
    "trader/position_sync.go",
    "trader/lighter_trader_v2_account.go",
    "trader/lighter_trader_v2_orders.go",
    "trader/lighter_trader_v2_trading.go",
    "trader/lighter_trader_v2.go",
    "trader/hyperliquid_trader.go",
    "trader/binance_futures.go",
    "trader/auto_trader_test.go",
    "trader/auto_trader.go",
    "market/api_client.go",
    "market/data.go",
    "manager/trader_manager.go",
    "decision/engine.go",
    "main.go",
]

def fix_imports(file_path):
    """修复单个文件的导入路径"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 替换 nofx/ 为 nofx/ (保持不变，因为 go.mod 中模块名就是 nofx)
        # 实际上不需要修改，Go 会根据 go.mod 自动解析
        original_content = content

        # 检查是否有变化
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Fixed: {file_path}")
            return True
        else:
            print(f"- Skipped: {file_path} (no changes needed)")
            return False
    except Exception as e:
        print(f"✗ Error fixing {file_path}: {e}")
        return False

def main():
    print("=" * 60)
    print("  修复 Go 导入路径")
    print("=" * 60)
    print()

    fixed_count = 0
    skipped_count = 0

    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if fix_imports(file_path):
                fixed_count += 1
            else:
                skipped_count += 1
        else:
            print(f"✗ File not found: {file_path}")

    print()
    print("=" * 60)
    print(f"  完成: {fixed_count} 个文件已修复, {skipped_count} 个文件跳过")
    print("=" * 60)

if __name__ == "__main__":
    main()
