"""
Persons router
  POST /persons/found         – rescuer submits a found person
  POST /persons/missing       – family member submits a missing person report
  GET  /persons               – list persons (filterable by type, query string)
  GET  /persons/{id}          – single person detail
  POST /matches/run           – (re)run matching for all unmatched persons
  GET  /matches               – list matches (filterable by state, score)
"""

from __future__ import annotations

import uuid
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
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
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

MATCH_THRESHOLD = 0.40   # minimum score to persist a candidate match


def _build_raw(data: PersonCreate) -> dict:
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
def submit_found_person(
    data: PersonCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Rescuer submits a found / rescued person.
    Matching runs asynchronously in the background so the response is instant.
    """
    raw = _build_raw(data)
    person = _build_person(raw, PersonType.found, current_user.id)
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
        after={"id": str(person.id), "type": "found"},
    )
    db.add(audit)
    db.commit()

    return person


@router.post("/persons/missing", response_model=PersonResponse, status_code=201)
def submit_missing_person(
    data: PersonCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Family member / police submits a missing person report.
    """
    raw = _build_raw(data)
    person = _build_person(raw, PersonType.missing, current_user.id)
    db.add(person)
    db.commit()
    db.refresh(person)

    background_tasks.add_task(_run_matching_for_person, person, db)

    audit = AuditLog(
        actor=current_user.id,
        action="CREATE_MISSING_PERSON",
        entity="Person",
        before=None,
        after={"id": str(person.id), "type": "missing"},
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
        item.found_name = (found_person.raw_fields or {}).get("name", "Unknown") if found_person else "Unknown"
        item.missing_name = (missing_person.raw_fields or {}).get("name", "Unknown") if missing_person else "Unknown"
        results.append(item)

    return results
