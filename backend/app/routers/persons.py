"""
Persons router
  POST /persons/found         – rescuer submits a found person (with optional image)
  POST /persons/missing       – family member submits a missing person report (with optional image)
  GET  /persons               – list persons (filterable by type, query string)
  GET  /persons/{id}          – single person detail
  GET  /persons/{id}/image    – retrieve person image by ID
  POST /matches/run           – (re)run matching for all unmatched persons
  GET  /matches               – list matches (filterable by state, score)
"""

from __future__ import annotations

import uuid
import logging
import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Person, Match, MatchState, PersonType, AuditLog, User
from app.schemas import PersonCreate, PersonResponse, MatchResponse
from app.auth import get_current_user
from app.cleaning import clean_record
from app.matching import score_pair

logger = logging.getLogger(__name__)

router = APIRouter(tags=["persons"])

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

MATCH_THRESHOLD = 0.40   # minimum score to persist a candidate match

# Person images directory
PERSON_IMAGES_DIR = Path(__file__).parent.parent / "person_images"
PERSON_IMAGES_DIR.mkdir(exist_ok=True)

# Allowed image extensions
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_IMAGE_SIZE_MB = 5  # 5 MB limit


# ─────────────────────────────────────────────────────────────────────────────
# Image Handling Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def save_person_image(file: UploadFile) -> Optional[str]:
    """
    Save an uploaded person image. Returns the filename (UUID + extension) on success,
    or None if validation fails.
    
    Validates file extension and size.
    """
    if not file or not file.filename:
        return None
    
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image format. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
        )
    
    # Read file content and check size
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_IMAGE_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"Image too large. Maximum size: {MAX_IMAGE_SIZE_MB} MB"
        )
    
    # Generate UUID-based filename
    image_filename = f"{uuid.uuid4()}{file_ext}"
    image_path = PERSON_IMAGES_DIR / image_filename
    
    # Save file
    try:
        with open(image_path, "wb") as f:
            f.write(content)
        logger.info("Saved person image: %s", image_filename)
        return image_filename
    except Exception as e:
        logger.error("Failed to save person image: %s", e)
        raise HTTPException(status_code=500, detail="Failed to save image")


def delete_person_image(image_filename: str) -> None:
    """Delete a person image file if it exists."""
    if not image_filename:
        return
    
    image_path = PERSON_IMAGES_DIR / image_filename
    try:
        if image_path.exists():
            image_path.unlink()
            logger.info("Deleted person image: %s", image_filename)
    except Exception as e:
        logger.error("Failed to delete person image %s: %s", image_filename, e)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
    """Turn the Pydantic payload into the raw_fields JSONB blob."""
    return {
        "name": data.name or "",
        "age_raw": data.age_raw or "",
        "gender": data.gender or "Unknown",
        "location": data.location or "",
        "lat": data.lat,
        "lon": data.lon,
        "condition": data.condition or "",
        "shelter": data.shelter or "",
        "descriptors": data.descriptors or "",
        "priority_flags": data.priority_flags or [],
    }


def _build_person(raw: dict, person_type: PersonType, creator_id: uuid.UUID) -> Person:
    """Clean the raw dict, then build a Person ORM object."""
    # Inject age_raw so clean_record can parse it
    cleaned = clean_record({**raw, "age_raw": raw.get("age_raw", "")})

    person = Person(
        type=person_type,
        raw_fields=raw,
        cleaned_fields=cleaned,
        age_min=cleaned.get("age_min"),
        age_max=cleaned.get("age_max"),
        gender=cleaned.get("gender"),
        lat=raw.get("lat"),
        lon=raw.get("lon"),
        shelter=raw.get("shelter"),
        status="active",
        priority_flags=raw.get("priority_flags", []),
        created_by=creator_id,
    )
    return person


def _run_matching_for_person(person: Person, db: Session) -> List[Match]:
    """
    Given a newly added person, score it against every record of the
    opposite type and persist matches above the threshold.
    Returns the list of new Match objects created.
    """
    opposite_type = PersonType.missing if person.type == PersonType.found else PersonType.found
    candidates = db.query(Person).filter(Person.type == opposite_type).all()

    new_matches: List[Match] = []
    for candidate in candidates:
        if person.type == PersonType.found:
            found_rec, missing_rec = person.cleaned_fields, candidate.cleaned_fields
            found_id, missing_id = person.id, candidate.id
        else:
            found_rec, missing_rec = candidate.cleaned_fields, person.cleaned_fields
            found_id, missing_id = candidate.id, person.id

        # Skip if a match already exists for this pair
        existing = (
            db.query(Match)
            .filter(Match.found_id == found_id, Match.missing_id == missing_id)
            .first()
        )
        if existing:
            continue

        result = score_pair(found_rec, missing_rec)
        if result["score"] >= MATCH_THRESHOLD:
            match = Match(
                found_id=found_id,
                missing_id=missing_id,
                score=result["score"],
                reasons={"reasons": result["reasons"], "features": result["raw_features"]},
                model_version=result["model_version"],
                state=MatchState.under_review,
            )
            db.add(match)
            new_matches.append(match)

    db.commit()
    logger.info("Matching produced %d new candidates for person %s", len(new_matches), person.id)
    return new_matches


# ─────────────────────────────────────────────────────────────────────────────
# Person endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/persons/found", response_model=PersonResponse, status_code=201)
async def submit_found_person(
    name: Optional[str] = Form(None),
    age_raw: Optional[str] = Form(None),
    gender: str = Form("Unknown"),
    location: Optional[str] = Form(None),
    lat: Optional[str] = Form(None),
    lon: Optional[str] = Form(None),
    condition: Optional[str] = Form(None),
    shelter: Optional[str] = Form(None),
    descriptors: Optional[str] = Form(None),
    priority_flags: str = Form("[]"),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = Depends(),
):
    """
    Rescuer submits a found / rescued person.
    Accepts multipart/form-data with optional image upload.
    Matching runs asynchronously in the background so the response is instant.
    """
    # Convert form data to PersonCreate
    try:
        import json
        priority_flags_list = json.loads(priority_flags) if priority_flags else []
    except (json.JSONDecodeError, TypeError):
        priority_flags_list = []
    
    # Parse lat/lon from strings
    lat_val = float(lat) if lat else None
    lon_val = float(lon) if lon else None
    
    data = PersonCreate(
        name=name,
        age_raw=age_raw,
        gender=gender,
        location=location,
        lat=lat_val,
        lon=lon_val,
        condition=condition,
        shelter=shelter,
        descriptors=descriptors,
        priority_flags=priority_flags_list,
    )
    
    raw = _build_raw(data)
    person = _build_person(raw, PersonType.found, current_user.id)
    
    # Handle image upload if provided
    if image and image.filename:
        image_filename = await save_person_image(image)
        person.image_filename = image_filename
    
    db.add(person)
    db.commit()
    db.refresh(person)

    # Fire-and-forget matching
    background_tasks.add_task(_run_matching_for_person, person, db)

    audit = AuditLog(
        actor=current_user.id,
        action="CREATE_FOUND_PERSON",
        entity="Person",
        before=None,
        after={"id": str(person.id), "type": "found", "has_image": person.image_filename is not None},
    )
    db.add(audit)
    db.commit()

    return person


@router.post("/persons/missing", response_model=PersonResponse, status_code=201)
async def submit_missing_person(
    name: Optional[str] = Form(None),
    age_raw: Optional[str] = Form(None),
    gender: str = Form("Unknown"),
    location: Optional[str] = Form(None),
    lat: Optional[str] = Form(None),
    lon: Optional[str] = Form(None),
    condition: Optional[str] = Form(None),
    shelter: Optional[str] = Form(None),
    descriptors: Optional[str] = Form(None),
    priority_flags: str = Form("[]"),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = Depends(),
):
    """
    Family member / police submits a missing person report.
    Accepts multipart/form-data with optional image upload.
    """
    # Convert form data to PersonCreate
    try:
        import json
        priority_flags_list = json.loads(priority_flags) if priority_flags else []
    except (json.JSONDecodeError, TypeError):
        priority_flags_list = []
    
    # Parse lat/lon from strings
    lat_val = float(lat) if lat else None
    lon_val = float(lon) if lon else None
    
    data = PersonCreate(
        name=name,
        age_raw=age_raw,
        gender=gender,
        location=location,
        lat=lat_val,
        lon=lon_val,
        condition=condition,
        shelter=shelter,
        descriptors=descriptors,
        priority_flags=priority_flags_list,
    )
    
    raw = _build_raw(data)
    person = _build_person(raw, PersonType.missing, current_user.id)
    
    # Handle image upload if provided
    if image and image.filename:
        image_filename = await save_person_image(image)
        person.image_filename = image_filename
    
    db.add(person)
    db.commit()
    db.refresh(person)

    background_tasks.add_task(_run_matching_for_person, person, db)

    audit = AuditLog(
        actor=current_user.id,
        action="CREATE_MISSING_PERSON",
        entity="Person",
        before=None,
        after={"id": str(person.id), "type": "missing", "has_image": person.image_filename is not None},
    )
    db.add(audit)
    db.commit()

    return person


@router.get("/persons", response_model=List[PersonResponse])
def list_persons(
    type: Optional[str] = Query(None, description="'found' or 'missing'"),
    q: Optional[str] = Query(None, description="Name substring search"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List persons. Filterable by type and name substring."""
    query = db.query(Person)
    if type:
        try:
            ptype = PersonType(type)
            query = query.filter(Person.type == ptype)
        except ValueError:
            raise HTTPException(status_code=400, detail="type must be 'found' or 'missing'")
    if q:
        # Simple substring match on the JSONB name field
        query = query.filter(Person.raw_fields["name"].astext.ilike(f"%{q}%"))
    return query.order_by(Person.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/persons/{person_id}", response_model=PersonResponse)
def get_person(
    person_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    return person


@router.get("/persons/{person_id}/image")
def get_person_image(
    person_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve image for a person by ID.
    Returns the image file with appropriate media type.
    """
    from fastapi.responses import FileResponse
    
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    
    if not person.image_filename:
        raise HTTPException(status_code=404, detail="No image for this person")
    
    image_path = PERSON_IMAGES_DIR / person.image_filename
    if not image_path.exists():
        logger.warning("Image file missing for person %s: %s", person_id, person.image_filename)
        raise HTTPException(status_code=404, detail="Image file not found")
    
    # Determine media type from extension
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    file_ext = Path(person.image_filename).suffix.lower()
    media_type = media_types.get(file_ext, "image/jpeg")
    
    return FileResponse(image_path, media_type=media_type)


# ─────────────────────────────────────────────────────────────────────────────
# Match endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/matches/run", status_code=200)
def run_full_matching(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    (Re)run matching across ALL found × missing pairs.
    Admin / police only.  Use this to bootstrap after seeding.
    """
    if current_user.role.value not in ("police", "admin"):
        raise HTTPException(status_code=403, detail="Police or admin role required.")

    found_persons = db.query(Person).filter(Person.type == PersonType.found).all()
    total_new = 0
    for person in found_persons:
        new = _run_matching_for_person(person, db)
        total_new += len(new)

    return {"status": "ok", "new_matches_created": total_new}


@router.get("/matches", response_model=List[MatchResponse])
def list_matches(
    state: Optional[str] = Query(None, description="under_review | verified | rejected"),
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List match candidates. Police/admin see all; rescuers see only verified."""
    query = db.query(Match)

    if current_user.role.value not in ("police", "admin"):
        # Public / rescuers only see confirmed matches
        query = query.filter(Match.state == MatchState.verified)
    elif state:
        try:
            query = query.filter(Match.state == MatchState(state))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid state value")

    query = query.filter(Match.score >= min_score)
    matches = query.order_by(Match.score.desc()).offset(offset).limit(limit).all()

    # Enrich with names from the Person table
    results: List[MatchResponse] = []
    for m in matches:
        found_person = db.query(Person).filter(Person.id == m.found_id).first()
        missing_person = db.query(Person).filter(Person.id == m.missing_id).first()
        item = MatchResponse.model_validate(m)
        if found_person:
            item.found_name = (found_person.raw_fields or {}).get("name", "Unknown")
            item.found_person = found_person.raw_fields
        else:
            item.found_name = "Unknown"
            item.found_person = {}
            
        if missing_person:
            item.missing_name = (missing_person.raw_fields or {}).get("name", "Unknown")
            item.missing_person = missing_person.raw_fields
        else:
            item.missing_name = "Unknown"
            item.missing_person = {}
            
        results.append(item)

    return results
