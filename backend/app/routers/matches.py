from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Match, MatchState, AuditLog, User
from app.schemas import MatchStateUpdate, AuditLogResponse
from app.auth import get_current_user
from typing import List
import uuid

router = APIRouter(tags=["matches"])


@router.post("/matches/{match_id}/verify")
def verify_match(
    match_id: uuid.UUID,
    body: MatchStateUpdate = MatchStateUpdate(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.value not in ("police", "admin"):
        raise HTTPException(status_code=403, detail="Not authorized. Police role required.")

    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    old_state = match.state.value
    match.state = MatchState.verified
    match.verified_by = current_user.id

    from datetime import datetime, timezone
    match.verified_at = datetime.now(timezone.utc)

    audit = AuditLog(
        actor=current_user.id,
        action="VERIFY_MATCH",
        entity="Match",
        before={"state": old_state},
        after={"state": "verified", "note": body.note},
    )
    db.add(audit)
    db.commit()
    return {"status": "success", "message": "Match verified."}


@router.post("/matches/{match_id}/reject")
def reject_match(
    match_id: uuid.UUID,
    body: MatchStateUpdate = MatchStateUpdate(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.value not in ("police", "admin"):
        raise HTTPException(status_code=403, detail="Not authorized.")

    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    old_state = match.state.value
    match.state = MatchState.rejected
    match.verified_by = current_user.id

    from datetime import datetime, timezone
    match.verified_at = datetime.now(timezone.utc)

    audit = AuditLog(
        actor=current_user.id,
        action="REJECT_MATCH",
        entity="Match",
        before={"state": old_state},
        after={"state": "rejected", "note": body.note},
    )
    db.add(audit)
    db.commit()
    return {"status": "success", "message": "Match rejected."}


@router.get("/audit", response_model=List[AuditLogResponse])
def get_audit_log(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.value not in ("police", "admin"):
        raise HTTPException(status_code=403, detail="Not authorized. Police role required.")
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()
