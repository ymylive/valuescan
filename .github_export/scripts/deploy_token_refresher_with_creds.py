#!/usr/bin/env python3
"""Deploy improved CDP token refresher to VPS."""

import os
import sys

# Set credentials
os.environ["VALUESCAN_EMAIL"] = "ymy_live@outlook.com"
os.environ["VALUESCAN_PASSWORD"] = "Qq159741."
os.environ["VALUESCAN_VPS_PASSWORD"] = os.environ.get("VALUESCAN_VPS_PASSWORD", "")

if not os.environ["VALUESCAN_VPS_PASSWORD"]:
    print("Error: VALUESCAN_VPS_PASSWORD environment variable is required")
    sys.exit(1)

# Import and run the deployment
sys.path.insert(0, os.path.dirname(__file__))
from deploy_token_refresher import main

if __name__ == "__main__":
    sys.exit(main())
