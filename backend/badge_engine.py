"""Badge awarder — runs after every session completes."""
from datetime import datetime, date
from sqlalchemy.orm import Session

from models import (
    Progress, TopicMastery, TablesSession, Answer, Session as DBSession,
    BeltProgress
)
from mastery_context import TOPICS

BADGES = {
    "first_quest": {"name": "First Quest", "icon": "🚀", "desc": "Completed your first quest"},
    "streak_7": {"name": "7-Day Streak", "icon": "🔥", "desc": "Quested 7 days in a row"},
    "streak_30": {"name": "30-Day Streak", "icon": "⚡", "desc": "Quested 30 days in a row"},
    "perfect_quest": {"name": "Perfect Quest", "icon": "💯", "desc": "Got every question right"},
    "combo_5": {"name": "Combo Master", "icon": "🔥", "desc": "Hit a 5-answer combo"},
    "speed_demon": {"name": "Speed Demon", "icon": "⚡", "desc": "Blitz tables under 60s"},
    "topic_master": {"name": "Topic Master", "icon": "🎯", "desc": "Reached 90% on a topic"},
    "subject_sweep": {"name": "Subject Sweep", "icon": "🌊", "desc": "70%+ on every topic in a subject"},
    "belt_bronze": {"name": "Bronze Belt", "icon": "🥉", "desc": "Earned the Bronze Belt"},
    "belt_silver": {"name": "Silver Belt", "icon": "🥈", "desc": "Earned the Silver Belt"},
    "belt_gold": {"name": "Gold Belt", "icon": "🥇", "desc": "Earned the Gold Belt"},
    "belt_platinum": {"name": "Platinum Belt", "icon": "💎", "desc": "Earned the Platinum Belt"},
    "belt_elite": {"name": "Elite Scholar", "icon": "🏆", "desc": "Reached Elite Scholar"},
}


def _already(prog: Progress, key: str) -> bool:
    return any(b.get("id") == key for b in (prog.badges or []))


def _award(prog: Progress, key: str, new_list: list[dict]) -> None:
    if _already(prog, key):
        return
    badge = {"id": key, **BADGES[key], "earned_at": datetime.utcnow().isoformat()}
    prog.badges = (prog.badges or []) + [badge]
    new_list.append(badge)


def evaluate(
    db: Session,
    child_id: int,
    *,
    session_score: int | None = None,
    session_total: int | None = None,
    max_combo: int = 0,
    blitz_seconds: int | None = None,
) -> list[dict]:
    prog = db.query(Progress).filter_by(child_id=child_id).first()
    if not prog:
        return []

    awarded: list[dict] = []

    # First quest
    if db.query(DBSession).filter_by(child_id=child_id, status="completed").count() >= 1:
        _award(prog, "first_quest", awarded)

    # Perfect quest
    if session_total and session_score == session_total and session_total >= 5:
        _award(prog, "perfect_quest", awarded)

    # Combo
    if max_combo >= 5:
        _award(prog, "combo_5", awarded)

    # Streak
    if prog.longest_streak >= 7:
        _award(prog, "streak_7", awarded)
    if prog.longest_streak >= 30:
        _award(prog, "streak_30", awarded)

    # Speed demon
    if blitz_seconds is not None and blitz_seconds < 60:
        _award(prog, "speed_demon", awarded)

    # Topic master & Subject sweep
    rows = db.query(TopicMastery).filter_by(child_id=child_id).all()
    for r in rows:
        if r.attempts >= 10 and r.accuracy >= 0.90:
            _award(prog, "topic_master", awarded)
            break
    for subject, topics in TOPICS.items():
        subj_rows = {r.topic: r for r in rows if r.subject == subject}
        if all((r := subj_rows.get(t)) and r.attempts >= 5 and r.accuracy >= 0.70 for t in topics):
            _award(prog, "subject_sweep", awarded)
            break

    # Belt badges
    bp = db.query(BeltProgress).filter_by(child_id=child_id).first()
    if bp:
        if bp.current_belt >= 1: _award(prog, "belt_bronze", awarded)
        if bp.current_belt >= 2: _award(prog, "belt_silver", awarded)
        if bp.current_belt >= 3: _award(prog, "belt_gold", awarded)
        if bp.current_belt >= 4: _award(prog, "belt_platinum", awarded)
        if bp.current_belt >= 5: _award(prog, "belt_elite", awarded)

    db.commit()
    return awarded
