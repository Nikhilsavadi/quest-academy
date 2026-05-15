"""Topic-level accuracy + difficulty promotion/demotion suggestions."""
from datetime import date
from sqlalchemy.orm import Session

from models import (
    Answer, Question, Session as DBSession, TopicMastery, ProgressionSuggestion
)

DIFFICULTY_ORDER = ["starter", "challenge", "olympiad"]


def _next(diff: str) -> str | None:
    i = DIFFICULTY_ORDER.index(diff)
    return DIFFICULTY_ORDER[i + 1] if i + 1 < len(DIFFICULTY_ORDER) else None


def _prev(diff: str) -> str | None:
    i = DIFFICULTY_ORDER.index(diff)
    return DIFFICULTY_ORDER[i - 1] if i - 1 >= 0 else None


def run(db: Session, child_id: int, session_id: int) -> None:
    """Update topic_mastery and emit suggestions after a session completes."""
    sess = db.get(DBSession, session_id)
    if not sess or sess.session_type == "belt_exam":
        return  # belt exam doesn't affect mastery progression

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

        # Promotion: accuracy ≥80% with ≥10 attempts at current difficulty
        if (
            row.current_difficulty != "olympiad"
            and row.attempts_at_current >= 10
            and row.correct_at_current / row.attempts_at_current >= 0.8
            and not row.progression_pending
        ):
            target = _next(row.current_difficulty)
            if target and not _has_open_suggestion(db, child_id, subject, topic):
                db.add(ProgressionSuggestion(
                    child_id=child_id, subject=subject, topic=topic,
                    from_difficulty=row.current_difficulty, to_difficulty=target,
                ))
                row.suggested_difficulty = target
                row.progression_pending = True

        # Demotion: accuracy <50% over last 5
        elif (
            row.current_difficulty != "starter"
            and len(latest5) >= 5
            and row.last5_correct < 3
            and not row.progression_pending
        ):
            target = _prev(row.current_difficulty)
            if target and not _has_open_suggestion(db, child_id, subject, topic):
                db.add(ProgressionSuggestion(
                    child_id=child_id, subject=subject, topic=topic,
                    from_difficulty=row.current_difficulty, to_difficulty=target,
                ))
                row.suggested_difficulty = target
                row.progression_pending = True

    db.commit()


def _has_open_suggestion(db: Session, child_id: int, subject: str, topic: str) -> bool:
    return db.query(ProgressionSuggestion).filter_by(
        child_id=child_id, subject=subject, topic=topic, status="pending"
    ).first() is not None
