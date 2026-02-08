#!/usr/bin/env python3
"""Find the correct ValuScan login API endpoint"""
import requests
import re

def main():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Origin": "https://www.valuescan.io",
        "Referer": "https://www.valuescan.io/login",
    })
    
    # First, get the main JS bundle to find API patterns
    print("Fetching main page...")
    r = session.get("https://www.valuescan.io/", timeout=30)
    print(f"Main page status: {r.status_code}")
    
    # Find the JS bundle URL
    js_match = re.search(r'src="/assets/(index-[^"]+\.js)"', r.text)
    if js_match:
        js_url = f"https://www.valuescan.io/assets/{js_match.group(1)}"
        print(f"Found JS bundle: {js_url}")
        
        # Download and search for API endpoints
        js_resp = session.get(js_url, timeout=60)
        js_text = js_resp.text
        
        # Save JS for offline analysis
        with open("valuescan_bundle.js", "w", encoding="utf-8") as f:
            f.write(js_text)
        print("Saved JS bundle to valuescan_bundle.js")
        
        # Find api_login function definition
        api_login_matches = re.findall(r'.{100}api_login.{100}', js_text)
        print("\napi_login context:")
        for m in api_login_matches[:5]:
            print(f"  ...{m}...")
        
        # Find axios/fetch POST patterns
        post_patterns = re.findall(r'\.post\s*\(\s*["\']([^"\']+)["\']', js_text)
        print("\nPOST endpoints:")
        for p in sorted(set(post_patterns))[:30]:
            print(f"  {p}")
        
        # Find account-related endpoints
        account_patterns = re.findall(r'["\']([^"\']*account[^"\']*)["\']', js_text, re.IGNORECASE)
        print("\nAccount-related strings:")
        for p in sorted(set(account_patterns))[:20]:
            if '/' in p:
                print(f"  {p}")
    
    # Test some common endpoints
    print("\n\nTesting login endpoints...")
    endpoints = [
        "https://api.valuescan.io/api/account/login",
        "https://api.valuescan.io/api/v1/account/login", 
        "https://api.valuescan.io/api/v2/account/login",
        "https://api.valuescan.io/api/auth/login",
        "https://api.valuescan.io/api/v1/auth/login",
        "https://api.valuescan.io/api/user/login",
        "https://api.valuescan.io/api/v1/user/login",
        "https://www.valuescan.io/api/account/login",
        "https://www.valuescan.io/api/v1/account/login",
    ]
    
    payload = {
        "account": "ymy_live@outlook.com",
        "password": "Qq159741.",
        "language": "en-US"
    }
    
    for endpoint in endpoints:
        try:
            r = session.post(endpoint, json=payload, timeout=15)
            resp_preview = r.text[:200] if r.text else "empty"
            has_token = "token" in r.text.lower() if r.text else False
            print(f"\n{endpoint}")
            print(f"  Status: {r.status_code}, Has token: {has_token}")
            print(f"  Response: {resp_preview}")
        except Exception as e:
            print(f"\n{endpoint}")
            print(f"  Error: {e}")

if __name__ == "__main__":
    main()
