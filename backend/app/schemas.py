from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from app.models import UserRole, PersonType, MatchState

# ── Auth ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    password: str
    role: Optional[UserRole] = UserRole.rescuer

class UserResponse(BaseModel):
    id: UUID
    username: str
    role: UserRole
    created_at: datetime

    model_config = {"from_attributes": True}

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str

class TokenData(BaseModel):
    username: Optional[str] = None


# ── Person ────────────────────────────────────────────────────────────────────

class PersonCreate(BaseModel):
    """Payload sent by the rescuer / family member form."""
    name: Optional[str] = None
    age_raw: Optional[str] = None          # "40", "40-45", "40s", "about 40"
    gender: Optional[str] = "Unknown"
    location: Optional[str] = None        # free-text address / landmark
    lat: Optional[float] = None
    lon: Optional[float] = None
    condition: Optional[str] = None       # e.g. "injured", "unconscious"
    shelter: Optional[str] = None         # shelter name / camp
    descriptors: Optional[str] = None     # physical description
    priority_flags: Optional[List[str]] = []

    @field_validator("gender")
    @classmethod
    def normalise_gender(cls, v: str) -> str:
        v = (v or "").lower()
        if v in ("m", "male", "boy", "man"):
            return "Male"
        if v in ("f", "female", "girl", "woman"):
            return "Female"
        return "Unknown"


class PersonResponse(BaseModel):
    id: UUID
    type: PersonType
    raw_fields: Dict[str, Any]
    cleaned_fields: Dict[str, Any]
    age_min: Optional[int]
    age_max: Optional[int]
    gender: Optional[str]
    lat: Optional[float]
    lon: Optional[float]
    shelter: Optional[str]
    status: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Match ─────────────────────────────────────────────────────────────────────

class MatchResponse(BaseModel):
    id: UUID
    found_id: UUID
    missing_id: UUID
    score: float
    reasons: Any
    model_version: Optional[str]
    state: MatchState
    created_at: datetime
    # denormalised convenience fields (populated by the router)
    found_name: Optional[str] = None
    missing_name: Optional[str] = None

    model_config = {"from_attributes": True}


class MatchStateUpdate(BaseModel):
    """Body for verify / reject — optional note."""
    note: Optional[str] = None


# ── Audit ─────────────────────────────────────────────────────────────────────

class AuditLogResponse(BaseModel):
    id: UUID
    actor: UUID
    action: str
    entity: str
    before: Optional[Any]
    after: Optional[Any]
    timestamp: datetime

    model_config = {"from_attributes": True}
