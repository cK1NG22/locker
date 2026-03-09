import uuid

from asyncpg import UniqueViolationError
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional

from vault.auth_deps import require_user
from vault.db import get_db
from vault.audit import audit
from vault.crypto import encrypt, decrypt
from vault.helpers import utc_now
from vault.models import (
    SkillCreate,
    SkillUpdate,
    SkillCreated,
    SkillUpdated,
    SkillMeta,
    SkillFull,
    SkillBundleItem,
    SkillFileCreate,
    SkillFileMeta,
    SkillFileFull,
    SkillFolderDeploy,
)

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_user)])


@router.post("/skills", status_code=201, response_model=SkillCreated)
async def create_skill(body: SkillCreate, user: dict = Depends(require_user)):
    skill_id = str(uuid.uuid4())
    now = utc_now()
    encrypted = encrypt(body.content)
    uploaded_by = user["sub"]
    db = get_db()
    # Enforce per-user uniqueness for personal skills
    if body.scope == "personal":
        dup = await db.fetchrow(
            "SELECT 1 FROM skills WHERE name = $1 AND scope = 'personal' AND uploaded_by = $2",
            body.name, uploaded_by,
        )
        if dup is not None:
            raise HTTPException(status_code=409, detail=f"You already have a personal skill named '{body.name}'")
    # Enforce name uniqueness for team skills
    replaced_team_ids: list[str] = []
    if body.scope == "team":
        dup = await db.fetchrow(
            "SELECT id FROM skills WHERE name = $1 AND scope = 'team'",
            body.name,
        )
        if dup is not None:
            if body.replace_skill_id and body.replace_skill_id == dup["id"]:
                # Save team links before deleting (CASCADE will remove them)
                team_rows = await db.fetch(
                    "SELECT team_id FROM team_skills WHERE skill_id = $1", dup["id"],
                )
                replaced_team_ids = [r["team_id"] for r in team_rows]
                await db.execute("DELETE FROM skills WHERE id = $1", dup["id"])
                await audit(db, user["sub"], "skill.replace", "skill", dup["id"], {"name": body.name})
            else:
                return JSONResponse(
                    status_code=409,
                    content={"detail": f"A team skill named '{body.name}' already exists", "existing_skill_id": dup["id"]},
                )
    await db.execute(
        "INSERT INTO skills (id, name, content, description, visibility, scope, uploaded_by, created_at, updated_at) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
        skill_id, body.name, encrypted, body.description, body.visibility, body.scope, uploaded_by, now, now,
    )
    # Re-link to the same teams the old skill belonged to
    for team_id in replaced_team_ids:
        await db.execute(
            "INSERT INTO team_skills (team_id, skill_id) VALUES ($1, $2)", team_id, skill_id,
        )
    await audit(db, user["sub"], "skill.create", "skill", skill_id, {"name": body.name, "scope": body.scope, "visibility": body.visibility})
    return SkillCreated(id=skill_id, name=body.name, visibility=body.visibility, scope=body.scope, created_at=now)


@router.get("/skills/bundle")
async def bundle_skills():
    db = get_db()
    rows = await db.fetch("SELECT id, name, content FROM skills WHERE scope = 'team'")
    skills = [
        SkillBundleItem(id=row["id"], name=row["name"], content=decrypt(row["content"]))
        for row in rows
    ]
    return {"skills": skills}


@router.get("/skills")
async def list_skills(name: Optional[str] = Query(default=None), user: dict = Depends(require_user)):
    db = get_db()
    user_id = user["sub"]
    if name is not None:
        row = await db.fetchrow(
            """SELECT s.id, s.name, s.content, s.description, s.visibility, s.scope, s.uploaded_by,
                      u.name AS uploaded_by_name, s.created_at, s.updated_at
               FROM skills s
               LEFT JOIN users u ON u.id = s.uploaded_by
               WHERE s.name = $1 AND (s.scope = 'team' OR s.uploaded_by = $2)""",
            name, user_id,
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        file_rows = await db.fetch(
            "SELECT id, path, size_bytes, created_at FROM skill_files WHERE skill_id = $1",
            row["id"],
        )
        files = [
            SkillFileMeta(id=fr["id"], path=fr["path"], size_bytes=fr["size_bytes"], created_at=fr["created_at"])
            for fr in file_rows
        ]
        return SkillFull(
            id=row["id"],
            name=row["name"],
            content=decrypt(row["content"]),
            description=row["description"],
            visibility=row["visibility"],
            scope=row["scope"],
            uploaded_by=row["uploaded_by"],
            uploaded_by_name=row["uploaded_by_name"],
            files=files,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
    rows = await db.fetch(
        """SELECT s.id, s.name, s.description, s.visibility, s.scope, s.uploaded_by,
                  u.name AS uploaded_by_name, s.created_at, s.updated_at,
                  COUNT(sf.id) AS file_count
           FROM skills s
           LEFT JOIN users u ON u.id = s.uploaded_by
           LEFT JOIN skill_files sf ON sf.skill_id = s.id
           WHERE s.scope = 'team' OR s.uploaded_by = $1
           GROUP BY s.id, s.name, s.description, s.visibility, s.scope, s.uploaded_by,
                    u.name, s.created_at, s.updated_at""",
        user_id,
    )
    skills = [
        SkillMeta(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            visibility=row["visibility"],
            scope=row["scope"],
            uploaded_by=row["uploaded_by"],
            uploaded_by_name=row["uploaded_by_name"],
            file_count=row["file_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]
    return {"skills": skills}


@router.post("/skills/deploy-folder", status_code=201)
async def deploy_folder(body: SkillFolderDeploy, user: dict = Depends(require_user)):
    # Create the skill
    skill_id = str(uuid.uuid4())
    now = utc_now()
    encrypted_content = encrypt(body.content)
    uploaded_by = user["sub"]
    db = get_db()
    # Enforce per-user uniqueness for personal skills
    if body.scope == "personal":
        dup = await db.fetchrow(
            "SELECT 1 FROM skills WHERE name = $1 AND scope = 'personal' AND uploaded_by = $2",
            body.name, uploaded_by,
        )
        if dup is not None:
            raise HTTPException(status_code=409, detail=f"You already have a personal skill named '{body.name}'")
    # Enforce name uniqueness for team skills
    replaced_team_ids: list[str] = []
    if body.scope == "team":
        dup = await db.fetchrow(
            "SELECT id FROM skills WHERE name = $1 AND scope = 'team'",
            body.name,
        )
        if dup is not None:
            if body.replace_skill_id and body.replace_skill_id == dup["id"]:
                # Save team links before deleting (CASCADE will remove them)
                team_rows = await db.fetch(
                    "SELECT team_id FROM team_skills WHERE skill_id = $1", dup["id"],
                )
                replaced_team_ids = [r["team_id"] for r in team_rows]
                await db.execute("DELETE FROM skills WHERE id = $1", dup["id"])
                await audit(db, user["sub"], "skill.replace", "skill", dup["id"], {"name": body.name})
            else:
                return JSONResponse(
                    status_code=409,
                    content={"detail": f"A team skill named '{body.name}' already exists", "existing_skill_id": dup["id"]},
                )
    async with db.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO skills (id, name, content, description, visibility, scope, uploaded_by, created_at, updated_at) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                skill_id, body.name, encrypted_content, body.description, body.visibility, body.scope, uploaded_by, now, now,
            )
            # Insert reference files
            for f in body.files:
                file_id = str(uuid.uuid4())
                size_bytes = len(f.content.encode("utf-8"))
                encrypted_file = encrypt(f.content)
                await conn.execute(
                    "INSERT INTO skill_files (id, skill_id, path, content, size_bytes, created_at) VALUES ($1, $2, $3, $4, $5, $6)",
                    file_id, skill_id, f.path, encrypted_file, size_bytes, now,
                )
    # Re-link to the same teams the old skill belonged to
    for team_id in replaced_team_ids:
        await db.execute(
            "INSERT INTO team_skills (team_id, skill_id) VALUES ($1, $2)", team_id, skill_id,
        )
    await audit(db, user["sub"], "skill.deploy", "skill", skill_id, {"name": body.name, "file_count": len(body.files)})
    return {"id": skill_id, "name": body.name, "scope": body.scope, "file_count": len(body.files), "created_at": now}


@router.get("/skills/{skill_id}", response_model=SkillFull)
async def get_skill(skill_id: str, user: dict = Depends(require_user)):
    db = get_db()
    user_id = user["sub"]
    row = await db.fetchrow(
        """SELECT s.id, s.name, s.content, s.description, s.visibility, s.scope, s.uploaded_by,
                  u.name AS uploaded_by_name, s.created_at, s.updated_at
           FROM skills s
           LEFT JOIN users u ON u.id = s.uploaded_by
           WHERE s.id = $1 AND (s.scope = 'team' OR s.uploaded_by = $2)""",
        skill_id, user_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    file_rows = await db.fetch(
        "SELECT id, path, size_bytes, created_at FROM skill_files WHERE skill_id = $1",
        skill_id,
    )
    files = [
        SkillFileMeta(id=fr["id"], path=fr["path"], size_bytes=fr["size_bytes"], created_at=fr["created_at"])
        for fr in file_rows
    ]
    return SkillFull(
        id=row["id"],
        name=row["name"],
        content=decrypt(row["content"]),
        description=row["description"],
        visibility=row["visibility"],
        scope=row["scope"],
        uploaded_by=row["uploaded_by"],
        uploaded_by_name=row["uploaded_by_name"],
        files=files,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.put("/skills/{skill_id}", response_model=SkillUpdated)
async def update_skill(skill_id: str, body: SkillUpdate, user: dict = Depends(require_user)):
    if body.name is None and body.content is None and body.description is None and body.visibility is None and body.scope is None:
        raise HTTPException(status_code=422, detail="At least one field required")
    db = get_db()
    user_id = user["sub"]
    row = await db.fetchrow(
        "SELECT id, name, content, description, visibility, scope, uploaded_by FROM skills WHERE id = $1", skill_id
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    # Personal skills can only be modified by their owner
    if row["scope"] == "personal" and row["uploaded_by"] != user_id:
        raise HTTPException(status_code=403, detail="Only the owner can modify a personal skill")
    # Block team -> personal scope change
    if body.scope == "personal" and row["scope"] == "team":
        raise HTTPException(status_code=422, detail="Cannot change a team skill to personal scope")
    new_name = body.name if body.name is not None else row["name"]
    new_content = encrypt(body.content) if body.content is not None else row["content"]
    new_description = body.description if body.description is not None else row["description"]
    new_visibility = body.visibility if body.visibility is not None else row["visibility"]
    new_scope = body.scope if body.scope is not None else row["scope"]
    now = utc_now()
    await db.execute(
        "UPDATE skills SET name = $1, content = $2, description = $3, visibility = $4, scope = $5, updated_at = $6 WHERE id = $7",
        new_name, new_content, new_description, new_visibility, new_scope, now, skill_id,
    )
    changed = {}
    if body.name is not None:
        changed["name"] = body.name
    if body.content is not None:
        changed["content"] = True
    if body.description is not None:
        changed["description"] = body.description
    if body.visibility is not None:
        changed["visibility"] = body.visibility
    if body.scope is not None:
        changed["scope"] = body.scope
    await audit(db, user["sub"], "skill.update", "skill", skill_id, changed)
    return SkillUpdated(id=skill_id, name=new_name, visibility=new_visibility, scope=new_scope, updated_at=now)


@router.delete("/skills/{skill_id}", status_code=204)
async def delete_skill(skill_id: str, user: dict = Depends(require_user)):
    db = get_db()
    user_id = user["sub"]
    row = await db.fetchrow("SELECT id, name, scope, uploaded_by FROM skills WHERE id = $1", skill_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    if row["scope"] == "personal" and row["uploaded_by"] != user_id:
        raise HTTPException(status_code=403, detail="Only the owner can delete a personal skill")
    await db.execute("DELETE FROM skills WHERE id = $1", skill_id)
    await audit(db, user["sub"], "skill.delete", "skill", skill_id, {"name": row["name"]})


# --- Skill file endpoints ---


async def _require_skill(skill_id: str):
    db = get_db()
    row = await db.fetchrow("SELECT id FROM skills WHERE id = $1", skill_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return row


@router.get("/skills/{skill_id}/files")
async def list_skill_files(skill_id: str):
    await _require_skill(skill_id)
    db = get_db()
    rows = await db.fetch(
        "SELECT id, path, size_bytes, created_at FROM skill_files WHERE skill_id = $1",
        skill_id,
    )
    return {
        "files": [
            SkillFileMeta(id=r["id"], path=r["path"], size_bytes=r["size_bytes"], created_at=r["created_at"])
            for r in rows
        ]
    }


@router.get("/skills/{skill_id}/files/{file_id}", response_model=SkillFileFull)
async def get_skill_file(skill_id: str, file_id: str):
    await _require_skill(skill_id)
    db = get_db()
    row = await db.fetchrow(
        "SELECT id, path, content, size_bytes, created_at FROM skill_files WHERE id = $1 AND skill_id = $2",
        file_id, skill_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="File not found")
    return SkillFileFull(
        id=row["id"],
        path=row["path"],
        content=decrypt(row["content"]),
        size_bytes=row["size_bytes"],
        created_at=row["created_at"],
    )


@router.post("/skills/{skill_id}/files", status_code=201, response_model=SkillFileMeta)
async def upload_skill_file(skill_id: str, body: SkillFileCreate, user: dict = Depends(require_user)):
    await _require_skill(skill_id)
    file_id = str(uuid.uuid4())
    now = utc_now()
    size_bytes = len(body.content.encode("utf-8"))
    encrypted = encrypt(body.content)
    db = get_db()
    try:
        await db.execute(
            "INSERT INTO skill_files (id, skill_id, path, content, size_bytes, created_at) VALUES ($1, $2, $3, $4, $5, $6)",
            file_id, skill_id, body.path, encrypted, size_bytes, now,
        )
    except UniqueViolationError:
        raise HTTPException(status_code=409, detail=f"File path '{body.path}' already exists for this skill")
    await audit(db, user["sub"], "skill_file.upload", "skill_file", file_id, {"skill_id": skill_id, "path": body.path})
    return SkillFileMeta(id=file_id, path=body.path, size_bytes=size_bytes, created_at=now)


@router.delete("/skills/{skill_id}/files/{file_id}", status_code=204)
async def delete_skill_file(skill_id: str, file_id: str, user: dict = Depends(require_user)):
    await _require_skill(skill_id)
    db = get_db()
    row = await db.fetchrow(
        "SELECT id, path FROM skill_files WHERE id = $1 AND skill_id = $2",
        file_id, skill_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="File not found")
    await db.execute("DELETE FROM skill_files WHERE id = $1", file_id)
    await audit(db, user["sub"], "skill_file.delete", "skill_file", file_id, {"skill_id": skill_id, "path": row["path"]})
