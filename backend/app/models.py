import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from app.database import Base
import enum

# UUID and JSONB are PostgreSQL-specific. We use String (for UUIDs) and JSON
# (for JSONB) so the models work on both SQLite (dev) and PostgreSQL (prod).


class UserRole(str, enum.Enum):
    rescuer = "rescuer"
    police = "police"
    public = "public"
    admin = "admin"

class PersonType(str, enum.Enum):
    found = "found"
    missing = "missing"

class MatchState(str, enum.Enum):
    under_review = "under_review"
    verified = "verified"
    rejected = "rejected"


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.rescuer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Person(Base):
    __tablename__ = "persons"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(SQLEnum(PersonType), nullable=False, index=True)
    raw_fields = Column(JSON, nullable=False, default=dict)
    cleaned_fields = Column(JSON, nullable=False, default=dict)
    phonetic = Column(String, index=True)
    age_min = Column(Integer)
    age_max = Column(Integer)
    gender = Column(String)
    descriptors = Column(String)
    lat = Column(Float)
    lon = Column(Float)
    radius_m = Column(Float)
    shelter = Column(String)
    status = Column(String)
    priority_flags = Column(JSON, default=list)
    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    version = Column(Integer, default=1)


class Match(Base):
    __tablename__ = "matches"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    found_id = Column(String, ForeignKey("persons.id"), nullable=False)
    missing_id = Column(String, ForeignKey("persons.id"), nullable=False)
    score = Column(Float, nullable=False)
    reasons = Column(JSON, default=dict)
    model_version = Column(String)
    state = Column(SQLEnum(MatchState), default=MatchState.under_review)
    verified_by = Column(String, ForeignKey("users.id"))
    verified_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    actor = Column(String, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)
    entity = Column(String, nullable=False)
    before = Column(JSON)
    after = Column(JSON)
    prev_hash = Column(String)
    hash = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
