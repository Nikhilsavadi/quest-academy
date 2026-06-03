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
        # Health check — Samihan's Railway session 11 wedged with 0 questions
        # and the get_quest self-heal couldn't recover (presumed AI fallback
        # hanging on a phantom topic). If the linked session has zero Question
        # rows AND no answers yet, nuke and rebuild so the child isn't stuck.
        from models import Question, Answer
        existing_sess = db.get(DBSession, existing.session_id)
        if existing_sess and existing.status != "completed":
            q_count = db.query(Question).filter_by(session_id=existing.session_id).count()
            if q_count == 0:
                # No answers can exist (no questions to answer), so this is safe
                db.delete(existing)
                if existing_sess:
                    db.delete(existing_sess)
                db.commit()
                # Fall through to recreate below
                existing = None
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
        yesterday = date.today() - timedelta(days=1)
        children = db.query(User).filter_by(role="child").all()

        # Per-child: end-of-yesterday summary + streak break check
        for child in children:
            prog = db.query(Progress).filter_by(child_id=child.id).first()
            if not prog:
                continue
            _emit_daily_summary(db, child, yesterday)
            had_rest = db.query(RestDay).filter_by(child_id=child.id, date=yesterday).first()
            dq = db.query(DailyQuest).filter_by(child_id=child.id, date=yesterday).first()
            completed = dq and dq.status == "completed"
            if not completed and not had_rest:
                prog.streak_days = 0
        db.commit()

        # Tick all rivals (Max + Aisha + Tom) once per day
        max_engine.tick_daily(db)

        # Create today's daily quests
        for child in children:
            ensure_daily_quest(db, child.id)
    finally:
        db.close()


def _emit_daily_summary(db: Session, child: User, on_date) -> None:
    """End-of-day rollup notification to the parent — what the child did
    yesterday in one line. Hands-off accountability."""
    if not child.parent_id:
        return
    from sqlalchemy import func as sqlfunc
    from models import Session as DBSession, Question, Answer
    # Sessions completed yesterday
    sess_count = (
        db.query(DBSession)
        .filter(
            DBSession.child_id == child.id,
            DBSession.status == "completed",
            sqlfunc.date(DBSession.completed_at) == on_date,
        )
        .count()
    )
    if sess_count == 0:
        # Skip if the child didn't play at all — no point pinging
        return
    # XP earned yesterday: sum of correct-answer XP across yesterday's sessions
    correct = (
        db.query(sqlfunc.count(Answer.id))
        .join(Question, Answer.question_id == Question.id)
        .filter(
            Answer.child_id == child.id,
            Answer.is_correct == True,  # noqa: E712
            sqlfunc.date(Answer.answered_at) == on_date,
        )
        .scalar()
    ) or 0
    # Promotions notified yesterday (count of difficulty_promoted notifications)
    promos = (
        db.query(Notification)
        .filter(
            Notification.parent_id == child.parent_id,
            Notification.kind == "difficulty_promoted",
            sqlfunc.date(Notification.created_at) == on_date,
        )
        .count()
    )
    prog = db.query(Progress).filter_by(child_id=child.id).first()
    streak = prog.streak_days if prog else 0
    dq = db.query(DailyQuest).filter_by(child_id=child.id, date=on_date).first()
    did_daily = dq and dq.status == "completed"

    bits = [f"{sess_count} quest{'s' if sess_count != 1 else ''}", f"{correct} correct"]
    if did_daily:
        bits.append(f"streak {streak}d 🔥")
    if promos:
        bits.append(f"{promos} promotion{'s' if promos != 1 else ''} 📈")
    msg = f"📊 {child.name} yesterday: " + ", ".join(bits)
    db.add(Notification(
        parent_id=child.parent_id,
        kind="daily_summary",
        message=msg,
        payload={
            "child": child.name, "date": on_date.isoformat(),
            "sessions": sess_count, "correct": correct,
            "promotions": promos, "daily_done": bool(did_daily),
            "streak": streak,
        },
    ))


def start_scheduler(app):
    """APScheduler attached to FastAPI app lifespan."""
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    sched = BackgroundScheduler(timezone="Europe/London")
    # misfire_grace_time + coalesce: if the process was down at 00:05 and starts
    # within the hour, still run the missed job once (instead of skipping to
    # tomorrow). ensure_daily_quest is idempotent, so a late run is harmless.
    sched.add_job(
        midnight_job, CronTrigger(hour=0, minute=5), id="midnight",
        misfire_grace_time=3600, coalesce=True,
    )
    sched.add_job(_risk_job, CronTrigger(hour="18,20", minute=0), id="risk")
    sched.start()
    app.state.scheduler = sched


def _risk_job():
    db = SessionLocal()
    try:
        check_risk_notifications(db)
    finally:
        db.close()
