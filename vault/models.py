from pydantic import BaseModel
from typing import Optional, List


class SkillCreate(BaseModel):
    name: str
    content: str
    description: Optional[str] = None


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None


class SkillMeta(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    file_count: int = 0
    created_at: str
    updated_at: str


class SkillFull(BaseModel):
    id: str
    name: str
    content: str
    description: Optional[str] = None
    files: List["SkillFileMeta"] = []
    created_at: str
    updated_at: str


class SkillCreated(BaseModel):
    id: str
    name: str
    created_at: str


class SkillUpdated(BaseModel):
    id: str
    name: str
    updated_at: str


class SkillBundleItem(BaseModel):
    id: str
    name: str
    content: str


# --- Team models ---


class TeamCreate(BaseModel):
    name: str


class TeamUpdate(BaseModel):
    name: str


class TeamOut(BaseModel):
    id: str
    name: str
    token: str
    created_at: str


class TeamSummary(BaseModel):
    id: str
    name: str
    skill_count: int


class TeamDetail(BaseModel):
    id: str
    name: str
    token: str
    created_at: str
    skills: List[str]


class TeamSkillsSet(BaseModel):
    skill_ids: List[str]


class EmployeeSkill(BaseModel):
    name: str
    description: Optional[str] = None


# --- Skill file models ---


class SkillFileCreate(BaseModel):
    path: str
    content: str


class SkillFileMeta(BaseModel):
    id: str
    path: str
    size_bytes: int
    created_at: str


class SkillFileFull(SkillFileMeta):
    content: str


class SkillFolderDeploy(BaseModel):
    name: str
    content: str
    description: Optional[str] = None
    files: List[SkillFileCreate]
