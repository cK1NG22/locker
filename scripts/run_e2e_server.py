#!/usr/bin/env python3
"""Start Locker server with env vars from argv (for E2E). Usage: run_e2e_server.py API_KEY ENC_KEY DATABASE_URL PORT"""
import os
import sys
from pathlib import Path

# Ensure project root is on path (script lives in scripts/)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if len(sys.argv) < 5:
    sys.exit("Usage: run_e2e_server.py LOCKER_API_KEY LOCKER_ENCRYPTION_KEY DATABASE_URL PORT")

os.environ["LOCKER_API_KEY"] = sys.argv[1]
os.environ["LOCKER_ENCRYPTION_KEY"] = sys.argv[2]
os.environ["DATABASE_URL"] = sys.argv[3]
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-fake-for-e2e")
# Env set before uvicorn loads app
assert os.environ.get("LOCKER_API_KEY"), "LOCKER_API_KEY must be set"

import uvicorn

uvicorn.run("main:app", host="0.0.0.0", port=int(sys.argv[4]), log_level="warning")
