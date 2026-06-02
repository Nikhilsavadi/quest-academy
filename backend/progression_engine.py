"""Topic-level accuracy + AUTOMATIC difficulty promotion/demotion.

Was suggestion-based (parent had to approve every promotion). Now auto-applies
when accuracy thresholds are hit, so the child sees harder questions the next
time they touch a mastered topic without anyone needing to flick a switch.
The Notification log keeps the parent in the loop.
"""
from datetime import date
from sqlalchemy.orm import Session

from models import (
    Answer, Question, Session as DBSession, TopicMastery,
    User, Notification,
)

DIFFICULTY_ORDER = ["starter", "challenge", "olympiad"]


def _next(diff: str) -> str | None:
    i = DIFFICULTY_ORDER.index(diff)
    return DIFFICULTY_ORDER[i + 1] if i + 1 < len(DIFFICULTY_ORDER) else None


def _prev(diff: str) -> str | None:
    i = DIFFICULTY_ORDER.index(diff)
    return DIFFICULTY_ORDER[i - 1] if i - 1 >= 0 else None


def run(db: Session, child_id: int, session_id: int) -> list[dict]:
    """Update topic_mastery and auto-promote/demote.

    Returns a list of promotion/demotion events that fired this run, so the
    complete-session handler can award a 'topic graduation' XP bonus when a
    promotion lands in the same session that earned it."""
    events: list[dict] = []
    sess = db.get(DBSession, session_id)
    if not sess or sess.session_type == "belt_exam":
        return events  # belt exam doesn't affect mastery progression

    # Recompute per-topic stats from answers joined to this session's questions
    q_rows = db.query(Question).filter_by(session_id=session_id).all()
    by_topic: dict[str, list[tuple[int, bool]]] = {}
    for q in q_rows:
        a = db.query(Answer).filter_by(question_id=q.id, child_id=child_id).first()
        if not a:
            continue
        by_topic.setdefault(q.topic, []).append((a.id, a.is_correct))

    subject = sess.subject
    difficulty = sess.difficulty

    for topic, entries in by_topic.items():
        row = (
            db.query(TopicMastery)
            .filter_by(child_id=child_id, subject=subject, topic=topic)
            .first()
        )
        if not row:
            row = TopicMastery(child_id=child_id, subject=subject, topic=topic)
            db.add(row)
            db.flush()

        gained_attempts = len(entries)
        gained_correct = sum(1 for _, c in entries if c)
        row.attempts += gained_attempts
        row.correct += gained_correct
        row.accuracy = row.correct / row.attempts if row.attempts else 0.0
        row.last_attempted = date.today()

        if row.current_difficulty == difficulty:
            row.attempts_at_current += gained_attempts
            row.correct_at_current += gained_correct

        # Rolling last-5 correct count from latest 5 answers on this topic
        latest5 = (
            db.query(Answer)
            .join(Question, Answer.question_id == Question.id)
            .filter(Answer.child_id == child_id, Question.topic == topic)
            .order_by(Answer.answered_at.desc())
            .limit(5)
            .all()
        )
        row.last5_correct = sum(1 for a in latest5 if a.is_correct)

        # Auto-promote: ≥80% accuracy with ≥10 attempts at current difficulty
        if (
            row.current_difficulty != "olympiad"
            and row.attempts_at_current >= 10
            and row.correct_at_current / row.attempts_at_current >= 0.8
        ):
            target = _next(row.current_difficulty)
            if target:
                ev = _apply_change(db, child_id, row, target, "promoted")
                events.append(ev)

        # Auto-demote: <60% over the last 5 answers on this topic (struggling)
        elif (
            row.current_difficulty != "starter"
            and len(latest5) >= 5
            and row.last5_correct < 3
        ):
            target = _prev(row.current_difficulty)
            if target:
                ev = _apply_change(db, child_id, row, target, "demoted")
                events.append(ev)

    db.commit()
    return events


def _apply_change(db: Session, child_id: int, row: TopicMastery, target: str, kind: str) -> dict:
    """Bump current_difficulty up or down, reset the per-difficulty counters,
    and emit a parent notification. Returns an event dict the caller can use
    to award a graduation bonus."""
    prev = row.current_difficulty
    row.current_difficulty = target
    row.attempts_at_current = 0
    row.correct_at_current = 0
    row.suggested_difficulty = None
    row.progression_pending = False

    child = db.get(User, child_id)
    if child and child.parent_id:
        verb = "promoted" if kind == "promoted" else "stepped down"
        emoji = "📈" if kind == "promoted" else "📉"
        db.add(Notification(
            parent_id=child.parent_id,
            kind=f"difficulty_{kind}",
            message=f"{emoji} {child.name} {verb} on {row.topic}: {prev} → {target}",
            payload={
                "topic": row.topic, "subject": row.subject,
                "from": prev, "to": target,
            },
        ))
    return {"kind": kind, "topic": row.topic, "subject": row.subject, "from": prev, "to": target}


