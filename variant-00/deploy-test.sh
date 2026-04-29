#!/bin/sh
# Requires: LOCKER_API_KEY set in server env; server running
# Usage: ./deploy-test.sh <skill-file>
LOCKER_VAULT_URL=http://localhost:8080 LOCKER_API_KEY=mykey .venv/bin/locker deploy "${1:?Usage: ./deploy-test.sh <skill-file>}"
