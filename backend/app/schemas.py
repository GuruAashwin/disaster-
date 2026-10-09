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
    contact_phone: Optional[str] = None   # Family member phone (for missing person reports)
    contact_email: Optional[str] = None   # Family member email (for missing person reports)

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
    image_filename: Optional[str]
    photo_filenames: Optional[List[str]]
    contact_phone: Optional[str]
    contact_email: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Match ─────────────────────────────────────────────────────────────────────

class MatchResponse(BaseModel):
    id: UUID
    found_id: UUID
    missing_id: UUID
    score: float
    photo_confidence: Optional[float] = 0.0
    reasons: Any
    model_version: Optional[str]
    state: MatchState
    created_at: datetime
    # denormalised convenience fields (populated by the router)
    found_name: Optional[str] = None
    missing_name: Optional[str] = None
    found_person: Optional[Dict[str, Any]] = None
    missing_person: Optional[Dict[str, Any]] = None
    found_photos: Optional[List[str]] = None
    missing_photos: Optional[List[str]] = None

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


# ── Video Search (STEP 8 API) ─────────────────────────────────────────────────

SUPPORTED_CLOTHING_COLORS = [
    "black",
    "white",
    "gray",
    "red",
    "orange",
    "yellow",
    "green",
    "blue",
    "navy",
    "purple",
    "pink",
    "brown",
    "beige",
    "maroon",
]


class ClothingSearchRequest(BaseModel):
    """Request payload for clothing-based video search.
    
    Searches authorized/publicly available disaster video frames for possible
    clothing matches. Clothing similarity is NOT identity verification.
    Human verification is always required.
    """
    upper_body_color: Optional[str] = None
    lower_body_color: Optional[str] = None
    
    @field_validator("upper_body_color", "lower_body_color", mode="before")
    @classmethod
    def normalize_colors(cls, v: Optional[str]) -> Optional[str]:
        """Normalize color names to lowercase."""
        if v is None:
            return None
        return v.lower().strip() if isinstance(v, str) else v
    
    @field_validator("upper_body_color", "lower_body_color")
    @classmethod
    def validate_color_values(cls, v: Optional[str]) -> Optional[str]:
        """Validate color is in supported list."""
        if v is None:
            return None
        if v not in SUPPORTED_CLOTHING_COLORS:
            raise ValueError(
                f"Unsupported color: {v}. Supported colors: {', '.join(SUPPORTED_CLOTHING_COLORS)}"
            )
        return v
    
    @property
    def has_valid_colors(self) -> bool:
        """Check that at least one color is specified."""
        return self.upper_body_color is not None or self.lower_body_color is not None


class ClothingBodyRegion(BaseModel):
    """Detected clothing in a body region."""
    detected_color: Optional[str] = None
    confidence: float = 0.0
    matched: bool = False


class ClothingCandidate(BaseModel):
    """Individual clothing match candidate from video frames.
    
    IMPORTANT: "possible_sighting" is an investigative lead based on clothing
    similarity. It is NOT identity verification. Human verification is required.
    """
    candidate_id: str
    camera_id: str
    video_id: str
    frame: str
    timestamp_seconds: float
    detection_id: int
    upper_body: ClothingBodyRegion
    lower_body: ClothingBodyRegion
    match_score: int  # 0-100
    status: str  # "possible_sighting"
    verification_required: bool = True


class ClothingSearchResponse(BaseModel):
    """Response for clothing-based video search.
    
    Contains possible sightings that require human verification. Clothing
    matches do not confirm identity and must be investigated by authorized
    personnel using authorized/publicly available video footage only.
    """
    query: Dict[str, Optional[str]]
    candidates: List[ClothingCandidate] = []
    total_candidates: int = 0
    status: str  # "processed" or "failed"
    errors: Optional[List[str]] = None


class VideoStatusResponse(BaseModel):
    """Status of video search service."""
    status: str  # "available" or "unavailable"
    service: str = "clothing_video_search"
