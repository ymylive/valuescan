#!/usr/bin/env python3
"""Test CDP login on Windows."""

import os
import sys
from pathlib import Path

# Add signal_monitor to path
sys.path.insert(0, str(Path(__file__).parent.parent / "signal_monitor"))

def find_chrome():
    """Find Chrome executable on Windows."""
    possible_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def main():
    print("=" * 60)
    print("Testing CDP Login on Windows")
    print("=" * 60)

    # Check Chrome
    chrome_path = find_chrome()
    if chrome_path:
        print(f"\n[+] Chrome found: {chrome_path}")
    else:
        print("\n[ERROR] Chrome not found on this system")
        print("Please install Google Chrome to test CDP login")
        return 1

    # Set environment variables
    os.environ["VALUESCAN_EMAIL"] = "ymy_live@outlook.com"
    os.environ["VALUESCAN_PASSWORD"] = "Qq159741."

    print("\n[*] Testing CDP token refresh...")
    print("[*] This will:")
    print("    1. Start headless Chrome")
    print("    2. Navigate to ValueScan login page")
    print("    3. Fill credentials and login")
    print("    4. Extract tokens from localStorage")
    print()

    try:
        from cdp_token_refresher import cdp_refresh_token, load_credentials

        creds = load_credentials()
        if not creds:
            print("[ERROR] No credentials found")
            return 1

        print(f"[*] Using credentials: {creds['email']}")
        print("[*] Starting login process...\n")

        success = cdp_refresh_token(creds['email'], creds['password'])

        if success:
            print("\n" + "=" * 60)
            print("[SUCCESS] CDP login completed successfully!")
            print("=" * 60)
            return 0
        else:
            print("\n" + "=" * 60)
            print("[FAILED] CDP login failed")
            print("=" * 60)
            return 1

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
