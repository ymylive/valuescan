#!/usr/bin/env python3
"""
Quick test to verify the config page is working.
"""

import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("[ERROR] Playwright not installed")
    sys.exit(1)

async def quick_test():
    """Quick test of config page."""
    print("[TEST] Quick config page test...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        # Navigate
        print("[1/4] Loading page...")
        await page.goto('http://localhost:3000', wait_until='networkidle')

        # Click config tab
        print("[2/4] Clicking config tab...")
        await page.click('button:has-text("系统配置")')
        await page.wait_for_timeout(2000)

        # Check if config loaded
        print("[3/4] Checking if config loaded...")
        config_heading = await page.query_selector('h2:has-text("系统配置")')
        signal_tab = await page.query_selector('button:has-text("信号监控")')

        if config_heading and signal_tab:
            print("[4/4] SUCCESS! Config page is working!")
            print("  - Config heading found")
            print("  - Signal monitor tab found")
            result = True
        else:
            print("[4/4] FAILED! Config page not loading properly")
            print(f"  - Config heading: {'found' if config_heading else 'NOT FOUND'}")
            print(f"  - Signal tab: {'found' if signal_tab else 'NOT FOUND'}")
            result = False

        # Take screenshot
        screenshot_path = Path(__file__).parent.parent / "output" / "config_test.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(screenshot_path))
        print(f"\nScreenshot saved: {screenshot_path}")

        # Keep browser open briefly
        print("\nBrowser will close in 5 seconds...")
        await page.wait_for_timeout(5000)
        await browser.close()

        return result

if __name__ == '__main__':
    result = asyncio.run(quick_test())
    sys.exit(0 if result else 1)
