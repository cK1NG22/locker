#!/usr/bin/env bash
set -euo pipefail

# ── Locker End-to-End Test ──────────────────────────────────────────────
# Starts a real server, exercises the full workflow, and verifies
# skill creation, team assignment, visibility filtering, and CLI sync.
# ────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PORT=8111
BASE_URL="http://localhost:$PORT"
SERVER_PID=""
TEST_DB=""
SYNC_DIR=""
PASSED=0
FAILED=0
TOTAL=10

# ── Helpers ─────────────────────────────────────────────────────────────

cleanup() {
    echo ""
    echo "Cleaning up..."
    if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    [ -n "$TEST_DB" ] && rm -f "$TEST_DB"
    [ -n "$SYNC_DIR" ] && rm -rf "$SYNC_DIR"
}
trap cleanup EXIT

pass() {
    echo "PASS: $1"
    PASSED=$((PASSED + 1))
}

fail() {
    echo "FAIL: $1"
    FAILED=$((FAILED + 1))
}

check() {
    # Usage: check "description" <condition>
    if eval "$2"; then
        pass "$1"
    else
        fail "$1"
    fi
}

# ── Preflight ───────────────────────────────────────────────────────────

if ! command -v jq &>/dev/null; then
    echo "ERROR: jq is required but not installed. Install with: brew install jq"
    exit 1
fi

if [ ! -f "$PROJECT_DIR/.venv/bin/uvicorn" ]; then
    echo "ERROR: .venv/bin/uvicorn not found. Run: pip install -e . in the project."
    exit 1
fi

if [ ! -f "$PROJECT_DIR/.venv/bin/locker" ]; then
    echo "ERROR: .venv/bin/locker not found. Run: pip install -e . in the project."
    exit 1
fi

# ── Environment ─────────────────────────────────────────────────────────

export LOCKER_API_KEY="e2e-test-key-$(date +%s)"
export LOCKER_ENCRYPTION_KEY
LOCKER_ENCRYPTION_KEY="$(python3 -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())")"

TEST_DB="$(mktemp /tmp/locker_e2e_XXXXXX.db)"
export LOCKER_DB_PATH="$TEST_DB"

SYNC_DIR="$(mktemp -d /tmp/locker_sync_XXXXXX)"

export LOCKER_VAULT_URL="$BASE_URL"

# Don't need a real Anthropic key for E2E (not testing proxy)
export ANTHROPIC_API_KEY="sk-ant-fake-for-e2e"

# ── Start Server ────────────────────────────────────────────────────────

echo "Starting Locker server on port $PORT..."
cd "$PROJECT_DIR"
.venv/bin/uvicorn main:app --port "$PORT" --log-level warning &
SERVER_PID=$!

# Wait for server to be ready (max 5 seconds)
for i in $(seq 1 25); do
    if curl -s "$BASE_URL/health" >/dev/null 2>&1; then
        break
    fi
    if [ "$i" -eq 25 ]; then
        echo "ERROR: Server did not start within 5 seconds."
        exit 1
    fi
    sleep 0.2
done
echo "Server ready."

# ── Skill Content ───────────────────────────────────────────────────────

HIDDEN_CONTENT="This is a hidden skill — employees should never see this."
SHARED_CONTENT="This is a shared skill — employees see metadata only."
OPEN_CONTENT="This is an open skill — employees get the full content."

# ── Step 1: Create 3 skills ────────────────────────────────────────────

HIDDEN_RESP=$(curl -s -X POST "$BASE_URL/api/v1/skills" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $LOCKER_API_KEY" \
    -d "{\"name\": \"e2e-hidden-skill\", \"content\": \"$HIDDEN_CONTENT\", \"description\": \"Hidden desc\", \"visibility\": \"hidden\"}")
HIDDEN_ID=$(echo "$HIDDEN_RESP" | jq -r '.id')
check "Created hidden skill" '[ -n "$HIDDEN_ID" ] && [ "$HIDDEN_ID" != "null" ]'

SHARED_RESP=$(curl -s -X POST "$BASE_URL/api/v1/skills" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $LOCKER_API_KEY" \
    -d "{\"name\": \"e2e-shared-skill\", \"content\": \"$SHARED_CONTENT\", \"description\": \"Shared desc\", \"visibility\": \"shared\"}")
SHARED_ID=$(echo "$SHARED_RESP" | jq -r '.id')
check "Created shared skill" '[ -n "$SHARED_ID" ] && [ "$SHARED_ID" != "null" ]'

OPEN_RESP=$(curl -s -X POST "$BASE_URL/api/v1/skills" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $LOCKER_API_KEY" \
    -d "{\"name\": \"e2e-open-skill\", \"content\": \"$OPEN_CONTENT\", \"description\": \"Open desc\", \"visibility\": \"open\"}")
OPEN_ID=$(echo "$OPEN_RESP" | jq -r '.id')
check "Created open skill" '[ -n "$OPEN_ID" ] && [ "$OPEN_ID" != "null" ]'

# ── Step 2: Create a team ──────────────────────────────────────────────

TEAM_RESP=$(curl -s -X POST "$BASE_URL/api/v1/teams" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $LOCKER_API_KEY" \
    -d '{"name": "e2e-test-team"}')
TEAM_ID=$(echo "$TEAM_RESP" | jq -r '.id')
TEAM_TOKEN=$(echo "$TEAM_RESP" | jq -r '.token')
check "Created team" '[ -n "$TEAM_ID" ] && [ "$TEAM_ID" != "null" ] && [ -n "$TEAM_TOKEN" ] && [ "$TEAM_TOKEN" != "null" ]'

# ── Step 3: Assign all 3 skills to the team ─────────────────────────────

ASSIGN_RESP=$(curl -s -o /dev/null -w "%{http_code}" -X PUT "$BASE_URL/api/v1/teams/$TEAM_ID/skills" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $LOCKER_API_KEY" \
    -d "{\"skill_ids\": [\"$HIDDEN_ID\", \"$SHARED_ID\", \"$OPEN_ID\"]}")
check "Assigned skills to team" '[ "$ASSIGN_RESP" = "200" ]'

# ── Step 4: Hit the employee endpoint ───────────────────────────────────

EMP_RESP=$(curl -s "$BASE_URL/api/v1/employee/skills" \
    -H "X-Team-Token: $TEAM_TOKEN")

# Hidden skill should NOT appear at all
HIDDEN_MATCH=$(echo "$EMP_RESP" | jq '[.skills[] | select(.name == "e2e-hidden-skill")] | length')
check "Hidden skill not in employee response" '[ "$HIDDEN_MATCH" = "0" ]'

# Shared skill should appear but with no content
SHARED_CONTENT_VAL=$(echo "$EMP_RESP" | jq -r '.skills[] | select(.name == "e2e-shared-skill") | .content')
check "Shared skill has no content" '[ "$SHARED_CONTENT_VAL" = "null" ]'

# Open skill should appear with full content
OPEN_CONTENT_VAL=$(echo "$EMP_RESP" | jq -r '.skills[] | select(.name == "e2e-open-skill") | .content')
check "Open skill has full content" '[ "$OPEN_CONTENT_VAL" = "$OPEN_CONTENT" ]'

# ── Step 5: Run locker sync ────────────────────────────────────────────

export LOCKER_TEAM_TOKEN="$TEAM_TOKEN"
.venv/bin/locker sync --output-dir "$SYNC_DIR" >/dev/null 2>&1

# Only the open skill should be written as a .md file
check "locker sync wrote open skill file" '[ -f "$SYNC_DIR/e2e-open-skill.md" ]'

# File content should match
SYNCED_CONTENT=$(cat "$SYNC_DIR/e2e-open-skill.md")
check "Synced file content matches" '[ "$SYNCED_CONTENT" = "$OPEN_CONTENT" ]'

# ── Results ─────────────────────────────────────────────────────────────

echo ""
echo "$PASSED/$TOTAL tests passed. E2E test complete."

if [ "$FAILED" -gt 0 ]; then
    exit 1
fi
