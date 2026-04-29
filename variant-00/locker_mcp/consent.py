"""OAuth consent page — Google sign-in + team picker.

GET  /oauth/consent?session=<jwt>  — renders the consent HTML page
POST /oauth/consent/complete       — verifies Google token, creates auth code, redirects
"""

import os
import secrets
import time
import uuid
from datetime import datetime, timezone

import jwt as pyjwt
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pydantic import BaseModel

from vault.db import get_db

router = APIRouter(prefix="/oauth")

_ALLOWED_REDIRECT_URIS = {
    "https://claude.ai/api/mcp/auth_callback",
    "https://claude.com/api/mcp/auth_callback",
}


def _jwt_secret() -> str:
    return os.environ.get("LOCKER_JWT_SECRET", "dev-secret-change-me")


def _google_client_id() -> str:
    return os.environ.get("GOOGLE_CLIENT_ID", "")


# --- GET /oauth/consent ---

@router.get("/consent", response_class=HTMLResponse)
async def consent_page(session: str):
    """Serve the consent page. The session JWT is validated client-side on submit."""
    try:
        pyjwt.decode(session, _jwt_secret(), algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Session expired. Please restart authorization.")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Invalid session.")

    google_client_id = _google_client_id()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Connect Locker</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://accounts.google.com/gsi/client" async defer></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
    </style>
</head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center">
    <div class="bg-white rounded-xl shadow-lg p-8 max-w-md w-full mx-4">
        <div class="text-center mb-6">
            <h1 class="text-2xl font-bold text-gray-900 mb-2">Connect Locker</h1>
            <p class="text-gray-600">Sign in with Google to connect Locker with Claude</p>
        </div>

        <!-- Step 1: Google Sign-in -->
        <div id="step-signin">
            <div id="g_id_onload"
                 data-client_id="{google_client_id}"
                 data-callback="handleGoogleSignIn"
                 data-auto_prompt="false">
            </div>
            <div class="flex justify-center">
                <div class="g_id_signin"
                     data-type="standard"
                     data-size="large"
                     data-theme="outline"
                     data-text="signin_with"
                     data-shape="rectangular"
                     data-width="300">
                </div>
            </div>
        </div>

        <!-- Step 2: Team picker -->
        <div id="step-team" class="hidden">
            <p class="text-sm text-gray-600 mb-3">Select a team to authorize:</p>
            <div id="team-list" class="space-y-2 mb-4"></div>
            <button id="btn-authorize" onclick="completeAuth()"
                    class="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
                    disabled>
                Authorize
            </button>
        </div>

        <!-- Step 3: Processing -->
        <div id="step-processing" class="hidden text-center">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-3"></div>
            <p class="text-gray-600">Connecting...</p>
        </div>

        <!-- Error -->
        <div id="step-error" class="hidden text-center">
            <p class="text-red-600" id="error-msg"></p>
        </div>
    </div>

    <script>
        const SESSION = "{session}";
        let googleToken = null;
        let selectedTeamId = null;

        async function handleGoogleSignIn(response) {{
            googleToken = response.credential;
            document.getElementById('step-signin').classList.add('hidden');
            document.getElementById('step-team').classList.remove('hidden');

            // Fetch user's teams
            try {{
                const resp = await fetch('/oauth/consent/teams', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{google_token: googleToken}})
                }});
                if (!resp.ok) throw new Error((await resp.json()).detail || 'Failed to load teams');
                const data = await resp.json();
                const teams = data.teams;
                const teamList = document.getElementById('team-list');

                if (teams.length === 0) {{
                    teamList.innerHTML = '<p class="text-gray-500 text-sm">No teams found. Ask your admin to add you to a team.</p>';
                    return;
                }}

                if (teams.length === 1) {{
                    selectedTeamId = teams[0].id;
                    document.getElementById('btn-authorize').disabled = false;
                }}

                teams.forEach(t => {{
                    const div = document.createElement('div');
                    div.className = 'flex items-center p-3 border rounded-lg cursor-pointer hover:bg-blue-50 transition';
                    const radio = document.createElement('input');
                    radio.type = 'radio';
                    radio.name = 'team';
                    radio.value = t.id;
                    radio.className = 'mr-3';
                    if (teams.length === 1) radio.checked = true;
                    const label = document.createElement('span');
                    label.className = 'font-medium';
                    label.textContent = t.name;
                    div.appendChild(radio);
                    div.appendChild(label);
                    div.onclick = () => {{
                        selectedTeamId = t.id;
                        document.querySelectorAll('input[name="team"]').forEach(r => r.checked = false);
                        radio.checked = true;
                        document.getElementById('btn-authorize').disabled = false;
                    }};
                    teamList.appendChild(div);
                }});
            }} catch (e) {{
                showError(e.message);
            }}
        }}

        async function completeAuth() {{
            document.getElementById('step-team').classList.add('hidden');
            document.getElementById('step-processing').classList.remove('hidden');

            try {{
                const resp = await fetch('/oauth/consent/complete', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        google_token: googleToken,
                        team_id: selectedTeamId,
                        session: SESSION
                    }})
                }});
                if (!resp.ok) throw new Error((await resp.json()).detail || 'Authorization failed');
                const data = await resp.json();
                window.location.href = data.redirect_url;
            }} catch (e) {{
                showError(e.message);
            }}
        }}

        function showError(msg) {{
            document.getElementById('step-signin').classList.add('hidden');
            document.getElementById('step-team').classList.add('hidden');
            document.getElementById('step-processing').classList.add('hidden');
            document.getElementById('step-error').classList.remove('hidden');
            document.getElementById('error-msg').textContent = msg;
        }}
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)


# --- POST /oauth/consent/teams ---

class TeamsRequest(BaseModel):
    google_token: str


@router.post("/consent/teams")
async def consent_teams(body: TeamsRequest):
    """Return teams the user belongs to after verifying their Google token."""
    google_client_id = _google_client_id()
    try:
        idinfo = id_token.verify_oauth2_token(
            body.google_token, google_requests.Request(), google_client_id
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {e}")

    google_id = idinfo["sub"]
    db = get_db()

    # Find user
    user_row = await db.fetchrow("SELECT id FROM users WHERE google_id = $1", google_id)
    if user_row is None:
        # Auto-create user on first OAuth consent
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO users (id, email, name, google_id, created_at) VALUES ($1, $2, $3, $4, $5)",
            user_id, idinfo["email"], idinfo.get("name", ""), google_id, now,
        )
    else:
        user_id = user_row["id"]

    # Get teams via team_members
    rows = await db.fetch(
        "SELECT t.id, t.name FROM teams t "
        "JOIN team_members tm ON tm.team_id = t.id "
        "WHERE tm.user_id = $1",
        user_id,
    )
    # Also include teams owned by this user
    owned_rows = await db.fetch(
        "SELECT id, name FROM teams WHERE owner_id = $1",
        user_id,
    )

    # Deduplicate
    teams = {}
    for r in list(rows) + list(owned_rows):
        teams[r["id"]] = {"id": r["id"], "name": r["name"]}

    return {"teams": list(teams.values())}


# --- POST /oauth/consent/complete ---

class ConsentCompleteRequest(BaseModel):
    google_token: str
    team_id: str
    session: str


@router.post("/consent/complete")
async def consent_complete(body: ConsentCompleteRequest):
    """Verify Google token, create auth code, return redirect URL."""
    # Verify session JWT
    try:
        session_data = pyjwt.decode(body.session, _jwt_secret(), algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Session expired. Please restart authorization.")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Invalid session.")

    # Verify Google token
    google_client_id = _google_client_id()
    try:
        idinfo = id_token.verify_oauth2_token(
            body.google_token, google_requests.Request(), google_client_id
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {e}")

    google_id = idinfo["sub"]
    db = get_db()

    # Find or create user
    user_row = await db.fetchrow("SELECT id FROM users WHERE google_id = $1", google_id)
    if user_row is None:
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO users (id, email, name, google_id, created_at) VALUES ($1, $2, $3, $4, $5)",
            user_id, idinfo["email"], idinfo.get("name", ""), google_id, now,
        )
    else:
        user_id = user_row["id"]

    # Verify user has access to the requested team
    team_row = await db.fetchrow(
        "SELECT id FROM teams WHERE id = $1 AND (owner_id = $2 OR id IN "
        "(SELECT team_id FROM team_members WHERE user_id = $2))",
        body.team_id, user_id,
    )
    if team_row is None:
        raise HTTPException(status_code=403, detail="You don't have access to this team.")

    # Validate redirect URI
    redirect_uri = session_data["redirect_uri"]
    if redirect_uri not in _ALLOWED_REDIRECT_URIS:
        raise HTTPException(status_code=400, detail="Invalid redirect URI.")

    # Create authorization code (160 bits = 20 bytes)
    code = secrets.token_hex(20)
    now = datetime.now(timezone.utc).isoformat()
    expires_at = time.time() + 600  # 10 minutes

    await db.execute(
        "INSERT INTO oauth_codes (code, client_id, user_id, team_id, scopes, code_challenge, "
        "redirect_uri, redirect_uri_provided_explicitly, resource, expires_at, created_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)",
        code,
        session_data["client_id"],
        user_id,
        body.team_id,
        " ".join(session_data.get("scopes", [])),
        session_data["code_challenge"],
        redirect_uri,
        session_data.get("redirect_uri_provided_explicitly", True),
        session_data.get("resource"),
        expires_at,
        now,
    )

    # Build redirect URL back to Claude
    state = session_data.get("state")
    redirect_url = f"{redirect_uri}?code={code}"
    if state:
        redirect_url += f"&state={state}"

    return JSONResponse({"redirect_url": redirect_url})
