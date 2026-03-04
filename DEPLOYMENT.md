# Deploying Locker

## Prerequisites

- Docker installed
- An Anthropic API key for your company
- A secure place to store your encryption key (password manager, secrets vault, etc.)

## 1. Generate secrets

```bash
# Admin API key (any strong random string)
openssl rand -hex 32

# Encryption key (AES-256, base64-encoded)
python3 -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"
```

**Back up the encryption key immediately.** If lost, all stored skill content is unrecoverable.

## 2. Build the Docker image

```bash
docker build -t locker:latest .
```

This builds both frontends (companion + dashboard) and packages everything into a single image.

## 3. Run the container

```bash
docker run -d \
  --name locker \
  -p 8000:8000 \
  -e LOCKER_API_KEY="your-admin-api-key" \
  -e LOCKER_ENCRYPTION_KEY="your-base64-encryption-key" \
  -e ANTHROPIC_API_KEY="sk-ant-your-key" \
  -v locker-data:/app/data \
  locker:latest
```

To persist the database across container restarts, also set:

```bash
-e LOCKER_DB_PATH="/app/data/locker.db"
```

## 4. Verify it's running

```bash
# Health check
curl http://localhost:8000/health
# Should return: {"status":"ok"}

# Test admin auth
curl -H "X-API-Key: your-admin-api-key" http://localhost:8000/api/v1/skills
# Should return: {"skills":[]}
```

## 5. Access the UIs

- **Admin Dashboard:** http://localhost:8000/dashboard (paste your admin API key to log in)
- **Employee Companion:** http://localhost:8000/companion (needs a team token from the dashboard)

## First-run checklist

1. Open the dashboard and sign in with your admin API key
2. Upload a skill (a .txt or .md file with your proprietary instructions)
3. Create a team (e.g. "Sales", "Legal")
4. Assign skills to the team
5. Copy the team token and share it with employees
6. Employees open the companion page, paste the token, and see their assigned skills

## Environment variables reference

| Variable | Required | Description |
|---|---|---|
| `LOCKER_API_KEY` | Yes | Admin auth key for all management endpoints |
| `LOCKER_ENCRYPTION_KEY` | Yes | AES-256 key (base64). Generate with the command above |
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key for the proxy |
| `LOCKER_DB_PATH` | No | SQLite file path (default: `./locker.db`) |
| `LOCKER_VAULT_URL` | No | Vault URL for CLI/MCP (default: `http://localhost:8000`) |
| `LOCKER_STATIC_DIR` | No | Companion build dir (default: `./static/companion`) |
| `LOCKER_DASHBOARD_DIR` | No | Dashboard build dir (default: `./static/dashboard`) |

## Encryption key backup

The encryption key protects all skill content at rest. Store it in:
- A password manager (1Password, Bitwarden, etc.)
- A cloud secrets manager (AWS Secrets Manager, GCP Secret Manager)
- An encrypted note in a secure location

**Never commit it to git.** The `.gitignore` already excludes `.env` files.

If you need to rotate the key, you must decrypt all skills with the old key and re-encrypt with the new one. There is no automated rotation tool yet.

## Running locally (without Docker)

```bash
# Install Python dependencies
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# Build frontends
cd companion && npm install && npm run build && cd ..
cd dashboard && npm install && npm run build && cd ..

# Set env vars (copy .env.example to .env and fill in values)
export LOCKER_API_KEY="dev-key"
export LOCKER_ENCRYPTION_KEY="$(python3 -c 'import os,base64; print(base64.b64encode(os.urandom(32)).decode())')"
export ANTHROPIC_API_KEY="sk-ant-..."

# Start the server
uvicorn main:app --reload --port 8000
```

## Container orchestration

The `/health` endpoint returns `{"status": "ok"}` and can be used for:
- Docker health checks: `HEALTHCHECK CMD curl -f http://localhost:8000/health`
- Kubernetes liveness/readiness probes
- Load balancer health checks
