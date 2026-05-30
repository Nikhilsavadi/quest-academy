"""Idempotent seed routine — runs on startup."""
import logging
import re
from datetime import date

from sqlalchemy.orm import Session

from auth import hash_password
from config import settings
from database import SessionLocal
from mastery_context import TOPICS
from models import (
    User, Progress, BeltProgress, AvatarUnlocks, MaxRival,
    TopicMastery, TablesFactStats, TablesTargets,
)
import daily_scheduler

log = logging.getLogger("seed")


def child_email_for(name: str) -> str:
    """Synthetic email used as the unique key for a name-entry child user."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return f"child-{slug}@quest-academy.app"


def ensure_child_supporting_data(db: Session, child: User, parent_id: int | None = None) -> None:
    """Idempotently create all per-child supporting rows.

    Safe to call from seed AND from /api/auth/enter on first arrival.
    """
    # Topic mastery — all 25 topics, starter, 0 attempts
    existing = {(r.subject, r.topic)
                for r in db.query(TopicMastery).filter_by(child_id=child.id).all()}
    for subj, topics in TOPICS.items():
        for t in topics:
            if (subj, t) not in existing:
                db.add(TopicMastery(
                    child_id=child.id, subject=subj, topic=t,
                    current_difficulty="starter",
                ))
    db.commit()

    if not db.query(Progress).filter_by(child_id=child.id).first():
        db.add(Progress(child_id=child.id)); db.commit()

    if not db.query(BeltProgress).filter_by(child_id=child.id).first():
        db.add(BeltProgress(child_id=child.id)); db.commit()

    if not db.query(AvatarUnlocks).filter_by(child_id=child.id).first():
        db.add(AvatarUnlocks(child_id=child.id)); db.commit()

    if not db.query(TablesTargets).filter_by(child_id=child.id).first():
        # set_by may be None if no parent was bootstrapped (env var omits parent)
        set_by = parent_id
        if set_by is None:
            anyp = db.query(User).filter_by(role="parent").first()
            set_by = anyp.id if anyp else child.id
        db.add(TablesTargets(child_id=child.id, set_by=set_by)); db.commit()

    existing_facts = {(r.multiplicand, r.multiplier)
                      for r in db.query(TablesFactStats).filter_by(child_id=child.id).all()}
    if len(existing_facts) < 144:
        for m in range(1, 13):
            for n in range(1, 13):
                if (m, n) not in existing_facts:
                    db.add(TablesFactStats(
                        child_id=child.id, multiplicand=m, multiplier=n,
                    ))
        db.commit()

    # Today's daily quest
    daily_scheduler.ensure_daily_quest(db, child.id, date.today())


def seed() -> None:
    db: Session = SessionLocal()
    try:
        # ── 1. Parent ────────────────────────────────────────────────────────
        parent = db.query(User).filter_by(email=settings.PARENT_EMAIL).first()
        if not parent:
            parent = User(
                name=settings.PARENT_NAME,
                email=settings.PARENT_EMAIL,
                password_hash=hash_password(settings.PARENT_PASSWORD),
                role="parent",
            )
            db.add(parent); db.commit(); db.refresh(parent)
            log.info("Seeded parent user")

        # ── 2. Rival league (Max + Aisha + Tom) ─────────────────────────────
        # Migration 0002 also seeds these; keep idempotent here so fresh
        # local DBs work whether or not alembic ran the seed-INSERT branch.
        for spec in [
            {"name": "Max",   "avatar": "🤖", "personality": "balanced"},
            {"name": "Aisha", "avatar": "📐", "personality": "mathlete"},
            {"name": "Tom",   "avatar": "🧠", "personality": "strategist"},
        ]:
            if not db.query(MaxRival).filter_by(name=spec["name"]).first():
                db.add(MaxRival(**spec)); db.commit()

        # ── 3. Children: created lazily on first /api/auth/enter call ──────
        # See routers/auth.py:child_enter — calls ensure_child_supporting_data
        # on first arrival per name. This avoids startup hangs from bulk
        # Anthropic calls to generate daily quests, and supports adding new
        # names to ALLOWED_CHILDREN without redeploying.

        log.info("Seed complete (parent + Max rival; %d children allowlisted, created lazily)",
                 len(settings.allowed_children_list))
    finally:
        db.close()
