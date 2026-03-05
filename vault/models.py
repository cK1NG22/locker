from pydantic import BaseModel, field_validator
from typing import Literal, Optional, List

Visibility = Literal["hidden", "shared", "open"]
Scope = Literal["personal", "team"]


class SkillCreate(BaseModel):
    name: str
    content: str
    description: Optional[str] = None
    visibility: Visibility = "open"
    scope: Scope = "team"


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None
    visibility: Optional[Visibility] = None
    scope: Optional[Scope] = None


class SkillMeta(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    visibility: str
    scope: str = "team"
    uploaded_by: Optional[str] = None
    uploaded_by_name: Optional[str] = None
    file_count: int = 0
    created_at: str
    updated_at: str


class SkillFull(BaseModel):
    id: str
    name: str
    content: str
    description: Optional[str] = None
    visibility: str
    scope: str = "team"
    uploaded_by: Optional[str] = None
    uploaded_by_name: Optional[str] = None
    files: List["SkillFileMeta"] = []
    created_at: str
    updated_at: str


class SkillCreated(BaseModel):
    id: str
    name: str
    visibility: str
    scope: str
    created_at: str


class SkillUpdated(BaseModel):
    id: str
    name: str
    visibility: str
    scope: str
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


class TeamMemberOut(BaseModel):
    id: str
    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    role: str
    can_share: bool
    created_at: str


class TeamMemberUpdate(BaseModel):
    role: Optional[str] = None
    can_share: Optional[bool] = None


class TeamMemberAdd(BaseModel):
    email: str


class TeamOut(BaseModel):
    id: str
    name: str
    token: str
    owner_id: Optional[str] = None
    created_at: str


class TeamSummary(BaseModel):
    id: str
    name: str
    skill_count: int


class TeamDetail(BaseModel):
    id: str
    name: str
    token: str
    owner_id: Optional[str] = None
    created_at: str
    skills: List[str]
    members: List[TeamMemberOut] = []


class TeamSkillsSet(BaseModel):
    skill_ids: List[str]


class EmployeeSkill(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    content: Optional[str] = None


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
    visibility: Visibility = "open"
    scope: Scope = "team"
    files: List[SkillFileCreate]


class SkillCopied(BaseModel):
    id: str
    name: str
    target_team_id: str
    created_at: str
