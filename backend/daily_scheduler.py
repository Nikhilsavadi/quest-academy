"""Midnight job: create today's daily quest + tick Max forward + risk notifications."""
import logging
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session

from database import SessionLocal
from models import (
    User, DailyQuest, Session as DBSession, RestDay, Progress, BeltProgress,
    Notification, TopicMastery,
)
import ai
import mastery_context
import max_engine

log = logging.getLogger("scheduler")

# Maths-only for v1 launch (NVR + VR question generation has visual-vs-logic
# mismatch bugs — see screenshots from 2026-05-15 testing). Re-add NVR / VR
# when deterministic generators land for those subjects.
SUBJECT_ROTATION = ["Maths"] * 7
# Mon=0, Sun=6 → spec: Sun=free choice; we default to Maths for free choice


def subject_for_date(d: date) -> str:
    return SUBJECT_ROTATION[d.weekday()]


def ensure_daily_quest(db: Session, child_id: int, on_date: date | None = None) -> DailyQuest | None:
    on_date = on_date or date.today()
    # Skip if rest day
    if db.query(RestDay).filter_by(child_id=child_id, date=on_date).first():
        return None
    existing = db.query(DailyQuest).filter_by(child_id=child_id, date=on_date).first()
    if existing:
        return existing

    subject = subject_for_date(on_date)
    # Pick a topic — weakest with attempts, else first unseen, else first topic
    topic = _pick_topic(db, child_id, subject)
    # Difficulty = current_difficulty for that topic
    tm = db.query(TopicMastery).filter_by(child_id=child_id, subject=subject, topic=topic).first()
    difficulty = tm.current_difficulty if tm else "starter"
    learn_mode = tm is not None and not tm.learn_mode_seen and tm.attempts == 0

    sess = DBSession(
        child_id=child_id, subject=subject, difficulty=difficulty,
        session_type="daily", status="pending", topic=topic,
        questions_count=20, source="ai_generated",
    )
    db.add(sess); db.commit(); db.refresh(sess)

    # Materialise via parent router helper
    from routers.parent import _materialise_questions
    _materialise_questions(db, sess, child_id, learn_mode=learn_mode)

    dq = DailyQuest(
        child_id=child_id, date=on_date, subject=subject,
        session_id=sess.id, status="pending",
    )
    db.add(dq); db.commit()
    return dq


def _pick_topic(db: Session, child_id: int, subject: str) -> str:
    topics = mastery_context.TOPICS[subject]
    rows = {
        r.topic: r
        for r in db.query(TopicMastery).filter_by(child_id=child_id, subject=subject).all()
    }
    unseen = [t for t in topics if not rows.get(t) or rows[t].attempts == 0]
    if unseen:
        return unseen[0]
    sorted_rows = sorted(rows.values(), key=lambda r: r.accuracy)
    return sorted_rows[0].topic if sorted_rows else topics[0]


def check_risk_notifications(db: Session) -> None:
    """Called periodically; emits 'quest at risk' notification after 6pm London time."""
    now = datetime.utcnow()
    if now.hour < 17:  # 17 UTC ≈ 18:00 London (roughly; good enough)
        return
    today = date.today()
    children = db.query(User).filter_by(role="child").all()
    for c in children:
        dq = db.query(DailyQuest).filter_by(child_id=c.id, date=today).first()
        if not dq or dq.status == "completed":
            continue
        # Avoid duplicate notification
        existing = (
            db.query(Notification)
            .filter_by(parent_id=c.parent_id, kind="quest_at_risk")
            .filter(Notification.created_at >= datetime.combine(today, datetime.min.time()))
            .first()
        )
        if existing:
            continue
        db.add(Notification(
            parent_id=c.parent_id, kind="quest_at_risk",
            message=f"⏰ {c.name}'s daily quest isn't done — streak at risk.",
            payload={"session_id": dq.session_id},
        ))
    db.commit()


def midnight_job() -> None:
    db = SessionLocal()
    try:
        # Streak break for anyone who missed yesterday (no rest day)
        yesterday = date.today() - timedelta(days=1)
        for child in db.query(User).filter_by(role="child").all():
            prog = db.query(Progress).filter_by(child_id=child.id).first()
            if not prog:
                continue
            had_rest = db.query(RestDay).filter_by(child_id=child.id, date=yesterday).first()
            dq = db.query(DailyQuest).filter_by(child_id=child.id, date=yesterday).first()
            completed = dq and dq.status == "completed"
            if not completed and not had_rest:
                prog.streak_days = 0
        db.commit()

        # Tick Max
        max_engine.tick_daily(db)

        # Create today's daily quests
        for child in db.query(User).filter_by(role="child").all():
            ensure_daily_quest(db, child.id)
    finally:
        db.close()


def start_scheduler(app):
    """APScheduler attached to FastAPI app lifespan."""
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    sched = BackgroundScheduler(timezone="Europe/London")
    sched.add_job(midnight_job, CronTrigger(hour=0, minute=5), id="midnight")
    sched.add_job(_risk_job, CronTrigger(hour="18,20", minute=0), id="risk")
    sched.start()
    app.state.scheduler = sched


def _risk_job():
    db = SessionLocal()
    try:
        check_risk_notifications(db)
    finally:
        db.close()
