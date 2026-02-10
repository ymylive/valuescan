#!/usr/bin/env python3
from DrissionPage import ChromiumPage
page = ChromiumPage(addr_or_opts=9222)
print("URL:", page.url)
print("Title:", page.title)
html = page.html[:3000] if page.html else ""
if "login" in page.url.lower():
    print("STATUS: NOT LOGGED IN")
elif "signal" in page.url.lower() or "GEMs" in page.url:
    print("STATUS: On signals page")
else:
    print("STATUS: Unknown page")
# Check for login elements
if "Sign in" in html or "Log in" in html:
    print("LOGIN REQUIRED: Yes")
else:
    print("LOGIN REQUIRED: No")
