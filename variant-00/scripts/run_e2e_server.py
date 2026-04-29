#!/usr/bin/env python3
"""Start Locker server with env vars from argv for E2E testing.

Usage: run_e2e_server.py LOCKER_API_KEY LOCKER_ENCRYPTION_KEY DATABASE_URL PORT
"""
import os
import sys
from pathlib import Path

EXPECTED_ARGS = ["LOCKER_API_KEY", "LOCKER_ENCRYPTION_KEY", "DATABASE_URL", "PORT"]

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if len(sys.argv) < len(EXPECTED_ARGS) + 1:
    sys.exit(f"Usage: {Path(__file__).name} {' '.join(EXPECTED_ARGS)}")

os.environ["LOCKER_API_KEY"] = sys.argv[1]
os.environ["LOCKER_ENCRYPTION_KEY"] = sys.argv[2]
os.environ["DATABASE_URL"] = sys.argv[3]
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-fake-for-e2e")

import uvicorn  # noqa: E402 — must import after env vars are set

uvicorn.run("main:app", host="0.0.0.0", port=int(sys.argv[4]), log_level="warning")
