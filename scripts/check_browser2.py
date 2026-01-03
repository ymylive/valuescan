#!/usr/bin/env python3
from DrissionPage import ChromiumPage, ChromiumOptions
co = ChromiumOptions()
co.set_local_port(9222)
page = ChromiumPage(addr_or_opts=co)
print("URL:", page.url)
print("Title:", page.title)
if "login" in page.url.lower():
    print("STATUS: NOT LOGGED IN")
elif "signal" in page.url.lower() or "GEMs" in page.url:
    print("STATUS: On signals page - GOOD")
html = page.html[:2000] if page.html else ""
if "Sign in" in html or "Log in" in html or "登录" in html:
    print("LOGIN BUTTON FOUND: Page requires login")
