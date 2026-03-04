import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from src.auth import require_api_key
from vault.db import get_db
from vault.crypto import encrypt, decrypt
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

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_key)])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/skills", status_code=201, response_model=SkillCreated)
async def create_skill(body: SkillCreate):
    skill_id = str(uuid.uuid4())
    now = _now()
    encrypted = encrypt(body.content)
    db = get_db()
    try:
        await db.execute(
            "INSERT INTO skills (id, name, content, description, visibility, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (skill_id, body.name, encrypted, body.description, body.visibility, now, now),
        )
        await db.commit()
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(status_code=409, detail=f"Skill '{body.name}' already exists")
        raise
    return SkillCreated(id=skill_id, name=body.name, visibility=body.visibility, created_at=now)


@router.get("/skills/bundle")
async def bundle_skills():
    db = get_db()
    cursor = await db.execute("SELECT id, name, content FROM skills")
    rows = await cursor.fetchall()
    skills = [
        SkillBundleItem(id=row["id"], name=row["name"], content=decrypt(row["content"]))
        for row in rows
    ]
    return {"skills": skills}


@router.get("/skills")
async def list_skills(name: Optional[str] = Query(default=None)):
    db = get_db()
    if name is not None:
        cursor = await db.execute(
            "SELECT id, name, content, description, visibility, created_at, updated_at FROM skills WHERE name = ?",
            (name,),
        )
        row = await cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        fc = await db.execute(
            "SELECT id, path, size_bytes, created_at FROM skill_files WHERE skill_id = ?",
            (row["id"],),
        )
        file_rows = await fc.fetchall()
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
            files=files,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
    cursor = await db.execute(
        """SELECT s.id, s.name, s.description, s.visibility, s.created_at, s.updated_at,
                  COUNT(sf.id) AS file_count
           FROM skills s
           LEFT JOIN skill_files sf ON sf.skill_id = s.id
           GROUP BY s.id"""
    )
    rows = await cursor.fetchall()
    skills = [
        SkillMeta(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            visibility=row["visibility"],
            file_count=row["file_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]
    return {"skills": skills}


@router.get("/skills/{skill_id}", response_model=SkillFull)
async def get_skill(skill_id: str):
    db = get_db()
    cursor = await db.execute(
        "SELECT id, name, content, description, visibility, created_at, updated_at FROM skills WHERE id = ?",
        (skill_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    fc = await db.execute(
        "SELECT id, path, size_bytes, created_at FROM skill_files WHERE skill_id = ?",
        (skill_id,),
    )
    file_rows = await fc.fetchall()
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
        files=files,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.put("/skills/{skill_id}", response_model=SkillUpdated)
async def update_skill(skill_id: str, body: SkillUpdate):
    if body.name is None and body.content is None and body.description is None and body.visibility is None:
        raise HTTPException(status_code=422, detail="At least one field required")
    db = get_db()
    cursor = await db.execute(
        "SELECT id, name, content, description, visibility FROM skills WHERE id = ?", (skill_id,)
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    new_name = body.name if body.name is not None else row["name"]
    new_content = encrypt(body.content) if body.content is not None else row["content"]
    new_description = body.description if body.description is not None else row["description"]
    new_visibility = body.visibility if body.visibility is not None else row["visibility"]
    now = _now()
    await db.execute(
        "UPDATE skills SET name = ?, content = ?, description = ?, visibility = ?, updated_at = ? WHERE id = ?",
        (new_name, new_content, new_description, new_visibility, now, skill_id),
    )
    await db.commit()
    return SkillUpdated(id=skill_id, name=new_name, visibility=new_visibility, updated_at=now)


@router.delete("/skills/{skill_id}", status_code=204)
async def delete_skill(skill_id: str):
    db = get_db()
    cursor = await db.execute("SELECT id FROM skills WHERE id = ?", (skill_id,))
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    await db.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
    await db.commit()


# --- Skill file endpoints ---


async def _require_skill(skill_id: str):
    db = get_db()
    cursor = await db.execute("SELECT id FROM skills WHERE id = ?", (skill_id,))
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return row


@router.get("/skills/{skill_id}/files")
async def list_skill_files(skill_id: str):
    await _require_skill(skill_id)
    db = get_db()
    cursor = await db.execute(
        "SELECT id, path, size_bytes, created_at FROM skill_files WHERE skill_id = ?",
        (skill_id,),
    )
    rows = await cursor.fetchall()
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
    cursor = await db.execute(
        "SELECT id, path, content, size_bytes, created_at FROM skill_files WHERE id = ? AND skill_id = ?",
        (file_id, skill_id),
    )
    row = await cursor.fetchone()
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
async def upload_skill_file(skill_id: str, body: SkillFileCreate):
    await _require_skill(skill_id)
    file_id = str(uuid.uuid4())
    now = _now()
    size_bytes = len(body.content.encode("utf-8"))
    encrypted = encrypt(body.content)
    db = get_db()
    try:
        await db.execute(
            "INSERT INTO skill_files (id, skill_id, path, content, size_bytes, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (file_id, skill_id, body.path, encrypted, size_bytes, now),
        )
        await db.commit()
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(status_code=409, detail=f"File path '{body.path}' already exists for this skill")
        raise
    return SkillFileMeta(id=file_id, path=body.path, size_bytes=size_bytes, created_at=now)


@router.delete("/skills/{skill_id}/files/{file_id}", status_code=204)
async def delete_skill_file(skill_id: str, file_id: str):
    await _require_skill(skill_id)
    db = get_db()
    cursor = await db.execute(
        "SELECT id FROM skill_files WHERE id = ? AND skill_id = ?",
        (file_id, skill_id),
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="File not found")
    await db.execute("DELETE FROM skill_files WHERE id = ?", (file_id,))
    await db.commit()


@router.post("/skills/deploy-folder", status_code=201)
async def deploy_folder(body: SkillFolderDeploy):
    # Create the skill
    skill_id = str(uuid.uuid4())
    now = _now()
    encrypted_content = encrypt(body.content)
    db = get_db()
    try:
        await db.execute(
            "INSERT INTO skills (id, name, content, description, visibility, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (skill_id, body.name, encrypted_content, body.description, body.visibility, now, now),
        )
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(status_code=409, detail=f"Skill '{body.name}' already exists")
        raise
    # Insert reference files
    for f in body.files:
        file_id = str(uuid.uuid4())
        size_bytes = len(f.content.encode("utf-8"))
        encrypted_file = encrypt(f.content)
        await db.execute(
            "INSERT INTO skill_files (id, skill_id, path, content, size_bytes, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (file_id, skill_id, f.path, encrypted_file, size_bytes, now),
        )
    await db.commit()
    return {"id": skill_id, "name": body.name, "file_count": len(body.files), "created_at": now}
