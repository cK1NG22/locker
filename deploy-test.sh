#!/bin/sh
# Requires: LOCKER_API_KEY set in server env; server running; bullets.txt in cwd
LOCKER_VAULT_URL=http://localhost:8000 LOCKER_API_KEY=mykey .venv/bin/locker deploy bullets.txt
