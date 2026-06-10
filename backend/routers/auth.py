from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import create_token, verify_password
from config import settings
from database import get_db
from models import User
from schemas import LoginIn, TokenOut
from seed import child_email_for, ensure_child_supporting_data

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Child entry: name-only against allowlist ──────────────────────────────────

class ChildEntryIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=40)


@router.post("/enter", response_model=TokenOut)
def child_enter(body: ChildEntryIn, db: Session = Depends(get_db)):
    name_raw = body.name.strip()
    if not name_raw:
        raise HTTPException(400, "Name required")

    allowed_dict = settings.allowed_children_dict  # {name: year_level}
    # Case-insensitive match — display the canonical casing from the allowlist
    canonical = next((a for a in allowed_dict if a.lower() == name_raw.lower()), None)
    if canonical is None:
        raise HTTPException(403, "That name isn't on the list. Ask whoever sent you the link.")
    desired_year = allowed_dict[canonical]

    # find-or-create child user, keyed by synthetic email derived from name
    synth_email = child_email_for(canonical)
    user = db.query(User).filter(User.email == synth_email).first()
    created = False
    if user is None:
        # Attach to the (single) parent so notifications (level-up, exam-ready,
        # difficulty-promoted, etc.) actually reach the parent dashboard.
        parent = db.query(User).filter_by(role="parent").first()
        user = User(
            email=synth_email, name=canonical, role="child", password_hash="",
            parent_id=parent.id if parent else None,
            year_level=desired_year,
        )
        db.add(user); db.commit(); db.refresh(user)
        created = True
    elif user.name != canonical:
        # allowlist casing changed — sync the display name
        user.name = canonical
        db.commit()

    # Backfill parent_id on any pre-existing child rows that were created
    # before this fix landed (Samihan + Anvi got parent_id=NULL originally).
    if user.parent_id is None:
        parent = db.query(User).filter_by(role="parent").first()
        if parent:
            user.parent_id = parent.id
            db.commit()

    # Keep year_level synced with the allowlist (so editing the env var is
    # enough to reclassify a kid — no DB poke needed).
    if user.year_level != desired_year:
        user.year_level = desired_year
        db.commit()

    # bootstrap supporting rows on first entry (idempotent — safe to repeat)
    if created:
        ensure_child_supporting_data(db, user)

    return TokenOut(access_token=create_token(user.id, user.role), role=user.role, name=user.name)


# ── Parent admin login (preserved) ───────────────────────────────────────────

@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    return TokenOut(access_token=create_token(user.id, user.role), role=user.role, name=user.name)
