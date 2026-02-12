#!/usr/bin/env python3
"""Deploy improved CDP token refresher to VPS."""

import os
import sys

# Set credentials from environment
os.environ["VALUESCAN_EMAIL"] = os.environ.get("VALUESCAN_EMAIL", "")
os.environ["VALUESCAN_PASSWORD"] = os.environ.get("VALUESCAN_PASSWORD", "")
os.environ["VALUESCAN_VPS_PASSWORD"] = os.environ.get("VALUESCAN_VPS_PASSWORD", "")

if not os.environ["VALUESCAN_VPS_PASSWORD"]:
    print("Error: VALUESCAN_VPS_PASSWORD environment variable is required")
    sys.exit(1)
if not os.environ["VALUESCAN_EMAIL"] or not os.environ["VALUESCAN_PASSWORD"]:
    print("Error: VALUESCAN_EMAIL and VALUESCAN_PASSWORD environment variables are required")
    sys.exit(1)

# Import and run the deployment
sys.path.insert(0, os.path.dirname(__file__))
from deploy_token_refresher import main

if __name__ == "__main__":
    sys.exit(main())
