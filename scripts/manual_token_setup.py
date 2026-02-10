#!/usr/bin/env python3
"""
Manual token setup helper.
Helps you manually input tokens from browser localStorage.
"""

import json
from pathlib import Path

def main():
    print("=" * 60)
    print("ValueScan Token Manual Setup")
    print("=" * 60)
    print()
    print("Please follow these steps:")
    print("1. Open browser and go to https://www.valuescan.io")
    print("2. Login with your account: ymy_live@outlook.com")
    print("3. Press F12 to open Developer Tools")
    print("4. Go to Console tab")
    print("5. Run this command:")
    print()
    print("   localStorage.getItem('account_token')")
    print()
    print("6. Copy the token (without quotes)")
    print()

    account_token = input("Paste account_token here: ").strip().strip('"').strip("'")

    print()
    print("7. Now run this command:")
    print()
    print("   localStorage.getItem('refresh_token')")
    print()

    refresh_token = input("Paste refresh_token here: ").strip().strip('"').strip("'")

    if not account_token or not refresh_token:
        print()
        print("ERROR: Both tokens are required!")
        return 1

    # Create token data
    token_data = {
        "account_token": account_token,
        "refresh_token": refresh_token
    }

    # Save to file
    token_file = Path(__file__).resolve().parent.parent / "signal_monitor" / "valuescan_localstorage.json"
    token_file.parent.mkdir(parents=True, exist_ok=True)

    with open(token_file, 'w', encoding='utf-8') as f:
        json.dump(token_data, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 60)
    print(f"✓ Tokens saved to: {token_file}")
    print("=" * 60)
    print()
    print("Now you can start the token refresher:")
    print("  python token_refresher.py")
    print()

    return 0

if __name__ == "__main__":
    exit(main())
