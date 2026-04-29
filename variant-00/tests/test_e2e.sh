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
PG_CONTAINER=""
SYNC_DIR=""
PASSED=0
FAILED=0

# ── Helpers ─────────────────────────────────────────────────────────────

cleanup() {
    echo ""
    echo "Cleaning up..."
    [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null && wait "$SERVER_PID" 2>/dev/null || true
    [ -n "$PG_CONTAINER" ] && docker rm -f "$PG_CONTAINER" 2>/dev/null || true
    [ -n "$SYNC_DIR" ] && rm -rf "$SYNC_DIR"
}
trap cleanup EXIT

check() {
    if eval "$2"; then
        echo "  PASS: $1"; PASSED=$((PASSED + 1))
    else
        echo "  FAIL: $1"; FAILED=$((FAILED + 1))
    fi
}

admin_post() { curl -s -X POST "$BASE_URL$1" -H "Content-Type: application/json" -H "X-API-Key: $LOCKER_API_KEY" -d "$2"; }
admin_put()  { curl -s -o /dev/null -w "%{http_code}" -X PUT "$BASE_URL$1" -H "Content-Type: application/json" -H "X-API-Key: $LOCKER_API_KEY" -d "$2"; }

require_cmd() { command -v "$1" &>/dev/null || { echo "ERROR: $1 is required. $2"; exit 1; }; }
require_file() { [ -f "$1" ] || { echo "ERROR: $1 not found. $2"; exit 1; }; }

wait_for() {
    local url="$1" max="$2" interval="$3" label="$4"
    for i in $(seq 1 "$max"); do
        curl -s "$url" >/dev/null 2>&1 && return 0
        [ "$i" -eq "$max" ] && { echo "ERROR: $label did not start in time."; exit 1; }
        sleep "$interval"
    done
}

# ── Preflight ───────────────────────────────────────────────────────────

require_cmd jq "Install with: brew install jq"
require_file "$PROJECT_DIR/.venv/bin/uvicorn" "Run: pip install -e . in the project."
require_file "$PROJECT_DIR/.venv/bin/locker" "Run: pip install -e . in the project."

# ── Environment ─────────────────────────────────────────────────────────

export LOCKER_API_KEY="e2e-test-key-$(date +%s)"
export LOCKER_ENCRYPTION_KEY
LOCKER_ENCRYPTION_KEY="$(python3 -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())")"
export ANTHROPIC_API_KEY="sk-ant-fake-for-e2e"

RUN_SUFFIX="$(date +%s%N)-$$"
SYNC_DIR="$(mktemp -d /tmp/locker_sync_XXXXXX)"
export LOCKER_VAULT_URL="$BASE_URL"

# ── Start Postgres ──────────────────────────────────────────────────────

E2E_PORT=5433

if command -v docker &>/dev/null && docker ps >/dev/null 2>&1; then
    PG_CONTAINER="locker-e2e-db-$$"
    echo "Starting Postgres container $PG_CONTAINER..."
    docker run -d --name "$PG_CONTAINER" \
        -e POSTGRES_USER=locker -e POSTGRES_PASSWORD=locker -e POSTGRES_DB=locker \
        -p "127.0.0.1:$E2E_PORT:5432" \
        postgres:16-alpine
    export DATABASE_URL="postgresql://locker:locker@127.0.0.1:$E2E_PORT/locker"

    for i in $(seq 1 30); do
        docker exec "$PG_CONTAINER" pg_isready -U locker -q 2>/dev/null && break
        [ "$i" -eq 30 ] && { echo "ERROR: Postgres did not start within 15 seconds."; exit 1; }
        sleep 0.5
    done
    echo "Postgres ready."
else
    export DATABASE_URL="${DATABASE_URL:-postgresql://locker:locker@127.0.0.1:5432/locker}"
    echo "Docker unavailable; using DATABASE_URL=$DATABASE_URL"
fi

# ── Start Server ────────────────────────────────────────────────────────

lsof -ti:$PORT 2>/dev/null | xargs kill -9 2>/dev/null || true
sleep 1

echo "Starting Locker server on port $PORT..."
cd "$PROJECT_DIR"
.venv/bin/python scripts/run_e2e_server.py "$LOCKER_API_KEY" "$LOCKER_ENCRYPTION_KEY" "$DATABASE_URL" "$PORT" &
SERVER_PID=$!

wait_for "$BASE_URL/health" 25 0.2 "Server"
echo "Server ready."

# ── Test Data ──────────────────────────────────────────────────────────

HIDDEN_CONTENT="This is a hidden skill — employees should never see this."
SHARED_CONTENT="This is a shared skill — employees see metadata only."
OPEN_CONTENT="This is an open skill — employees get the full content."

HIDDEN_NAME="e2e-hidden-skill-$RUN_SUFFIX"
SHARED_NAME="e2e-shared-skill-$RUN_SUFFIX"
OPEN_NAME="e2e-open-skill-$RUN_SUFFIX"
TEAM_NAME="e2e-test-team-$RUN_SUFFIX"

# ── Step 1: Create skills ──────────────────────────────────────────────

echo ""
echo "Running tests..."

HIDDEN_RESP=$(admin_post "/api/v1/skills" "{\"name\": \"$HIDDEN_NAME\", \"content\": \"$HIDDEN_CONTENT\", \"description\": \"Hidden desc\", \"visibility\": \"hidden\"}")
HIDDEN_ID=$(echo "$HIDDEN_RESP" | jq -r '.id')
check "Created hidden skill" '[ -n "$HIDDEN_ID" ] && [ "$HIDDEN_ID" != "null" ]'

SHARED_RESP=$(admin_post "/api/v1/skills" "{\"name\": \"$SHARED_NAME\", \"content\": \"$SHARED_CONTENT\", \"description\": \"Shared desc\", \"visibility\": \"shared\"}")
SHARED_ID=$(echo "$SHARED_RESP" | jq -r '.id')
check "Created shared skill" '[ -n "$SHARED_ID" ] && [ "$SHARED_ID" != "null" ]'

OPEN_RESP=$(admin_post "/api/v1/skills" "{\"name\": \"$OPEN_NAME\", \"content\": \"$OPEN_CONTENT\", \"description\": \"Open desc\", \"visibility\": \"open\"}")
OPEN_ID=$(echo "$OPEN_RESP" | jq -r '.id')
check "Created open skill" '[ -n "$OPEN_ID" ] && [ "$OPEN_ID" != "null" ]'

# ── Step 2: Create team ────────────────────────────────────────────────

TEAM_RESP=$(admin_post "/api/v1/teams" "{\"name\": \"$TEAM_NAME\"}")
TEAM_ID=$(echo "$TEAM_RESP" | jq -r '.id')
TEAM_TOKEN=$(echo "$TEAM_RESP" | jq -r '.token')
check "Created team" '[ -n "$TEAM_ID" ] && [ "$TEAM_ID" != "null" ] && [ -n "$TEAM_TOKEN" ] && [ "$TEAM_TOKEN" != "null" ]'

# ── Step 3: Assign skills to team ──────────────────────────────────────

ASSIGN_RESP=$(admin_put "/api/v1/teams/$TEAM_ID/skills" "{\"skill_ids\": [\"$HIDDEN_ID\", \"$SHARED_ID\", \"$OPEN_ID\"]}")
check "Assigned skills to team" '[ "$ASSIGN_RESP" = "200" ]'

# ── Step 4: Verify employee visibility ─────────────────────────────────

EMP_RESP=$(curl -s "$BASE_URL/api/v1/employee/skills" -H "X-Team-Token: $TEAM_TOKEN")

HIDDEN_MATCH=$(echo "$EMP_RESP" | jq --arg name "$HIDDEN_NAME" '[.skills[] | select(.name == $name)] | length')
check "Hidden skill not in employee response" '[ "$HIDDEN_MATCH" = "0" ]'

SHARED_CONTENT_VAL=$(echo "$EMP_RESP" | jq -r --arg name "$SHARED_NAME" '.skills[] | select(.name == $name) | .content')
check "Shared skill has no content" '[ "$SHARED_CONTENT_VAL" = "null" ]'

OPEN_CONTENT_VAL=$(echo "$EMP_RESP" | jq -r --arg name "$OPEN_NAME" '.skills[] | select(.name == $name) | .content')
check "Open skill has full content" '[ "$OPEN_CONTENT_VAL" = "$OPEN_CONTENT" ]'

# ── Step 5: Verify CLI sync ───────────────────────────────────────────

export LOCKER_TEAM_TOKEN="$TEAM_TOKEN"
.venv/bin/locker sync --output-dir "$SYNC_DIR" >/dev/null 2>&1

check "locker sync wrote open skill file" '[ -f "$SYNC_DIR/$OPEN_NAME.md" ]'

SYNCED_CONTENT=$(cat "$SYNC_DIR/$OPEN_NAME.md")
check "Synced file content matches" '[ "$SYNCED_CONTENT" = "$OPEN_CONTENT" ]'

# ── Results ─────────────────────────────────────────────────────────────

TOTAL=$((PASSED + FAILED))
echo ""
echo "$PASSED/$TOTAL passed. E2E test complete."

[ "$FAILED" -gt 0 ] && exit 1
