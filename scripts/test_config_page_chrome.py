#!/usr/bin/env python3
"""
Test script to diagnose black screen issue on system configuration page.
Uses Chrome DevTools Protocol (CDP) to automate browser testing.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("[WARN]  Playwright not available. Install with: pip install playwright && playwright install chromium")

async def test_config_page():
    """Test the configuration page for black screen issues."""

    if not PLAYWRIGHT_AVAILABLE:
        print("[ERROR] Cannot run test without Playwright")
        return False

    print("[TEST] Starting Chrome MCP test for configuration page...")
    print("=" * 80)

    # Configuration
    base_url = "http://localhost:3000"
    screenshots_dir = Path(__file__).parent.parent / "output" / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    async with async_playwright() as p:
        # Launch browser
        print(f"\n[BROWSER] Launching Chrome...")
        browser = await p.chromium.launch(
            headless=False,  # Show browser for debugging
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ]
        )

        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

        page = await context.new_page()

        # Collect console messages
        console_messages = []
        errors = []

        def handle_console(msg):
            console_messages.append({
                'type': msg.type,
                'text': msg.text,
                'location': msg.location
            })
            print(f"  [Console {msg.type}] {msg.text}")

        def handle_page_error(error):
            errors.append(str(error))
            print(f"  [Page Error] {error}")

        page.on('console', handle_console)
        page.on('pageerror', handle_page_error)

        try:
            # Step 1: Navigate to homepage
            print(f"\n[WEB] Navigating to {base_url}...")
            response = await page.goto(base_url, wait_until='networkidle', timeout=30000)

            if response:
                print(f"  [OK] Page loaded with status: {response.status}")
            else:
                print(f"  [WARN]  No response received")

            # Wait for initial render
            await page.wait_for_timeout(2000)

            # Take screenshot of dashboard
            dashboard_screenshot = screenshots_dir / f"01_dashboard_{timestamp}.png"
            await page.screenshot(path=str(dashboard_screenshot), full_page=True)
            print(f"  [SCREENSHOT] Dashboard screenshot: {dashboard_screenshot}")

            # Step 2: Check if config tab exists
            print(f"\n[SEARCH] Looking for '系统配置' tab...")
            config_tab_selector = 'button:has-text("系统配置")'

            try:
                await page.wait_for_selector(config_tab_selector, timeout=5000)
                print(f"  [OK] Found '系统配置' tab")
            except Exception as e:
                print(f"  [ERROR] Could not find '系统配置' tab: {e}")
                # Try alternative selectors
                all_buttons = await page.query_selector_all('button')
                print(f"  Found {len(all_buttons)} buttons on page")
                for btn in all_buttons[:10]:
                    text = await btn.inner_text()
                    print(f"    - Button: {text}")
                return False

            # Step 3: Click on config tab
            print(f"\n[CLICK] Clicking '系统配置' tab...")
            await page.click(config_tab_selector)

            # Wait for tab transition
            await page.wait_for_timeout(1000)

            # Step 4: Check if config content is visible
            print(f"\n[SEARCH] Checking config page content...")

            # Take screenshot after clicking
            config_screenshot = screenshots_dir / f"02_config_clicked_{timestamp}.png"
            await page.screenshot(path=str(config_screenshot), full_page=True)
            print(f"  [SCREENSHOT] Config page screenshot: {config_screenshot}")

            # Check for loading spinner
            loading_spinner = await page.query_selector('.animate-spin')
            if loading_spinner:
                print(f"  [LOADING] Loading spinner detected, waiting...")
                await page.wait_for_timeout(3000)

                # Take another screenshot after loading
                config_loaded_screenshot = screenshots_dir / f"03_config_loaded_{timestamp}.png"
                await page.screenshot(path=str(config_loaded_screenshot), full_page=True)
                print(f"  [SCREENSHOT] Config loaded screenshot: {config_loaded_screenshot}")

            # Check for config sections
            config_sections = [
                ('信号监控', 'button:has-text("信号监控")'),
                ('自动交易', 'button:has-text("自动交易")'),
                ('跟单系统', 'button:has-text("跟单系统")'),
                ('服务监控', 'button:has-text("服务监控")'),
            ]

            print(f"\n[LIST] Checking for config section tabs...")
            for section_name, selector in config_sections:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        is_visible = await element.is_visible()
                        print(f"  {'[OK]' if is_visible else '[ERROR]'} {section_name}: {'visible' if is_visible else 'hidden'}")
                    else:
                        print(f"  [ERROR] {section_name}: not found")
                except Exception as e:
                    print(f"  [ERROR] {section_name}: error - {e}")

            # Check for "系统配置" heading
            heading_selector = 'h2:has-text("系统配置")'
            try:
                heading = await page.query_selector(heading_selector)
                if heading:
                    is_visible = await heading.is_visible()
                    print(f"\n  {'[OK]' if is_visible else '[ERROR]'} Config heading: {'visible' if is_visible else 'hidden'}")
                else:
                    print(f"\n  [ERROR] Config heading not found")
            except Exception as e:
                print(f"\n  [ERROR] Config heading error: {e}")

            # Step 5: Inspect DOM structure
            print(f"\n[SEARCH] Inspecting DOM structure...")

            # Get the active tab content
            active_content = await page.evaluate('''() => {
                const main = document.querySelector('main');
                if (!main) return { error: 'No main element found' };

                const children = Array.from(main.children);
                return {
                    mainExists: true,
                    childCount: children.length,
                    children: children.map(child => ({
                        tag: child.tagName,
                        classes: child.className,
                        visible: child.offsetHeight > 0 && child.offsetWidth > 0,
                        display: window.getComputedStyle(child).display,
                        opacity: window.getComputedStyle(child).opacity,
                        height: child.offsetHeight,
                        width: child.offsetWidth,
                    }))
                };
            }''')

            print(f"  DOM Structure:")
            print(f"    {json.dumps(active_content, indent=4)}")

            # Step 6: Check for black screen indicators
            print(f"\n[STYLE] Checking for visual issues...")

            visual_check = await page.evaluate('''() => {
                const main = document.querySelector('main');
                if (!main) return { error: 'No main element' };

                const style = window.getComputedStyle(main);
                const configDiv = document.querySelector('[key="config"]') ||
                                 document.querySelector('.max-w-4xl');

                return {
                    mainBackground: style.backgroundColor,
                    mainColor: style.color,
                    mainDisplay: style.display,
                    mainOpacity: style.opacity,
                    configDivExists: !!configDiv,
                    configDivVisible: configDiv ? (configDiv.offsetHeight > 0) : false,
                    configDivStyle: configDiv ? {
                        display: window.getComputedStyle(configDiv).display,
                        opacity: window.getComputedStyle(configDiv).opacity,
                        visibility: window.getComputedStyle(configDiv).visibility,
                        height: configDiv.offsetHeight,
                        width: configDiv.offsetWidth,
                    } : null
                };
            }''')

            print(f"  Visual Check:")
            print(f"    {json.dumps(visual_check, indent=4)}")

            # Step 7: Check network requests
            print(f"\n[WEB] Checking network activity...")

            # Wait a bit for any pending requests
            await page.wait_for_timeout(2000)

            # Check if config API was called
            config_api_called = await page.evaluate('''() => {
                return window.performance.getEntriesByType('resource')
                    .filter(r => r.name.includes('/api/config'))
                    .map(r => ({
                        url: r.name,
                        duration: r.duration,
                        transferSize: r.transferSize,
                    }));
            }''')

            print(f"  Config API calls:")
            for call in config_api_called:
                print(f"    - {call['url']}")
                print(f"      Duration: {call['duration']}ms, Size: {call['transferSize']} bytes")

            # Step 8: Summary
            print(f"\n" + "=" * 80)
            print(f"[SUMMARY] TEST SUMMARY")
            print(f"=" * 80)
            print(f"Console Messages: {len(console_messages)}")
            print(f"Page Errors: {len(errors)}")
            print(f"Screenshots saved to: {screenshots_dir}")

            if errors:
                print(f"\n[ERROR] Errors detected:")
                for error in errors:
                    print(f"  - {error}")

            if not errors and visual_check.get('configDivVisible'):
                print(f"\n[OK] Config page appears to be rendering correctly")
                return True
            else:
                print(f"\n[WARN]  Potential issues detected - check screenshots and logs")
                return False

        except Exception as e:
            print(f"\n[ERROR] Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            # Keep browser open for manual inspection
            print(f"\n[PAUSE]  Browser will remain open for 30 seconds for manual inspection...")
            await page.wait_for_timeout(30000)
            await browser.close()

async def main():
    """Main entry point."""
    success = await test_config_page()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    asyncio.run(main())
