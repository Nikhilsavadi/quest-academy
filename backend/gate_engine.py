"""Belt gate evaluation. Runs after every session completes."""
from sqlalchemy.orm import Session
from sqlalchemy import func

from mastery_context import TOPICS
from models import (
    BeltProgress, TopicMastery, TablesSession, TablesFactStats,
    Notification, Progress, Session as DBSession
)


BELT_NAMES = ["Unranked", "Bronze", "Silver", "Gold", "Platinum", "Elite Scholar"]


def _topic_qualifies(row: TopicMastery, min_acc: float, min_attempts: int, difficulty: str | None = None) -> bool:
    if row.attempts < min_attempts:
        return False
    if difficulty and row.current_difficulty != difficulty and difficulty != "any":
        # For non-starter checks, count attempts at that difficulty
        if difficulty == "challenge" and row.current_difficulty in ("challenge", "olympiad"):
            pass
        elif difficulty == "olympiad" and row.current_difficulty == "olympiad":
            pass
        else:
            return False
    return row.accuracy >= min_acc


def _check_subject(rows: list[TopicMastery], subject: str, count_needed: int, min_acc: float, min_attempts: int) -> dict:
    qualifying = [r for r in rows if r.subject == subject and r.attempts >= min_attempts and r.accuracy >= min_acc]
    return {
        "label": f"{subject}: {count_needed} topics ≥{int(min_acc*100)}% acc ({min_attempts}+ attempts each)",
        "subject": subject,
        "needed": count_needed,
        "have": len(qualifying),
        "met": len(qualifying) >= count_needed,
        "qualifying": [r.topic for r in qualifying],
    }


def _all_topics_qualify(rows: list[TopicMastery], subject: str, min_acc: float, min_attempts: int = 1) -> dict:
    expected = TOPICS[subject]
    by_topic = {r.topic: r for r in rows if r.subject == subject}
    qualifying = [t for t in expected if (r := by_topic.get(t)) and r.attempts >= min_attempts and r.accuracy >= min_acc]
    return {
        "label": f"All {subject} topics ≥{int(min_acc*100)}% acc",
        "subject": subject,
        "needed": len(expected),
        "have": len(qualifying),
        "met": len(qualifying) == len(expected),
        "qualifying": qualifying,
    }


def evaluate(db: Session, child_id: int) -> dict:
    bp = db.query(BeltProgress).filter_by(child_id=child_id).first()
    prog = db.query(Progress).filter_by(child_id=child_id).first()
    if not bp or not prog:
        return {"current_belt": 0, "next_belt": None, "checklist": [], "exam_unlocked": False}

    mastery = db.query(TopicMastery).filter_by(child_id=child_id).all()
    blitz_sessions = db.query(TablesSession).filter_by(child_id=child_id, mode="blitz").all()
    blitz_count = len(blitz_sessions)
    avg_blitz = (sum(s.duration_seconds for s in blitz_sessions) / blitz_count) if blitz_count else 9999

    longest = prog.longest_streak

    checklist: list[dict] = []
    next_belt = bp.current_belt + 1

    if next_belt == 1:  # Bronze
        # First belt is intentionally fast (~1–2 days) so Samihan ranks up early.
        # Silver/Gold/Plat keep their stiffer gates so the climb still feels earned.
        checklist.append(_check_subject(mastery, "Maths", 3, 0.65, 3))
        # NVR + VR gates suspended for v1 (Maths-only launch)
        checklist.append({"label": "Tables: 2 Blitz sessions", "needed": 2, "have": blitz_count, "met": blitz_count >= 2})

    elif next_belt == 2:  # Silver
        checklist.append(_check_subject(mastery, "Maths", 10, 0.75, 8))
        # NVR + VR gates suspended for v1
        checklist.append({"label": "Avg Blitz < 90s", "met": avg_blitz < 90, "value": int(avg_blitz)})
        checklist.append({"label": "14-day streak ever", "met": longest >= 14, "value": longest})

    elif next_belt == 3:  # Gold
        checklist.append(_all_topics_qualify(mastery, "Maths", 0.80))
        # NVR + VR gates suspended for v1
        facts = db.query(TablesFactStats).filter_by(child_id=child_id).all()
        good = sum(1 for f in facts if f.attempts > 0 and f.correct / f.attempts >= 0.80)
        checklist.append({"label": "All 144 facts ≥80%", "have": good, "needed": 144, "met": good >= 144})
        checklist.append({"label": "Avg Blitz < 60s", "met": avg_blitz < 60, "value": int(avg_blitz)})
        template_sessions = db.query(DBSession).filter_by(child_id=child_id, source="template", status="completed").count()
        checklist.append({"label": "3 template sessions completed", "have": template_sessions, "needed": 3, "met": template_sessions >= 3})
        checklist.append({"label": "30-day streak ever", "met": longest >= 30, "value": longest})

    elif next_belt == 4:  # Platinum
        oly = [r for r in mastery if r.current_difficulty == "olympiad" and r.subject == "Maths"]
        good = [r for r in oly if r.attempts >= 10 and r.accuracy >= 0.85]
        total_expected = len(TOPICS["Maths"])  # v1: Maths-only
        checklist.append({"label": f"All Maths topics ≥85% at Olympiad", "have": len(good), "needed": total_expected, "met": len(good) >= total_expected})
        checklist.append({"label": "Avg Blitz < 45s", "met": avg_blitz < 45, "value": int(avg_blitz)})
        mocks = db.query(DBSession).filter_by(child_id=child_id, session_type="mock_exam", status="completed").count()
        checklist.append({"label": "2 Mock Exams passed ≥85%", "have": mocks, "needed": 2, "met": mocks >= 2})
        checklist.append({"label": "60-day streak ever", "met": longest >= 60, "value": longest})

    elif next_belt == 5:  # Elite
        oly = [r for r in mastery if r.current_difficulty == "olympiad" and r.subject == "Maths"]
        good = [r for r in oly if r.accuracy >= 0.90]
        total_expected = len(TOPICS["Maths"])  # v1: Maths-only
        checklist.append({"label": "All Maths topics ≥90% at Olympiad", "have": len(good), "needed": total_expected, "met": len(good) >= total_expected})
        checklist.append({"label": "Avg Blitz < 35s", "met": avg_blitz < 35, "value": int(avg_blitz)})
        sims = db.query(DBSession).filter_by(child_id=child_id, session_type="exam_sim", status="completed").count()
        checklist.append({"label": "3 Exam Simulator papers ≥90%", "have": sims, "needed": 3, "met": sims >= 3})

    all_met = bool(checklist) and all(c["met"] for c in checklist)
    bp.gate_progress = {"checklist": checklist, "belt_target": next_belt}

    if all_met and bp.exam_unlocked_belt != next_belt and next_belt <= 5:
        bp.exam_unlocked_belt = next_belt
        # Notify parent
        parent_id = _parent_id_for_child(db, child_id)
        if parent_id:
            db.add(Notification(
                parent_id=parent_id,
                kind="belt_exam_ready",
                message=f"⚔️ Samihan has unlocked the {BELT_NAMES[next_belt]} Belt Exam!",
                payload={"belt": next_belt},
            ))
        if next_belt == 1:
            bp.bronze_gate_met = True
        elif next_belt == 2:
            bp.silver_gate_met = True
        elif next_belt == 3:
            bp.gold_gate_met = True
        elif next_belt == 4:
            bp.platinum_gate_met = True
        elif next_belt == 5:
            bp.elite_gate_met = True

    db.commit()

    return {
        "current_belt": bp.current_belt,
        "current_belt_name": BELT_NAMES[bp.current_belt],
        "next_belt": next_belt if next_belt <= 5 else None,
        "next_belt_name": BELT_NAMES[next_belt] if next_belt <= 5 else None,
        "checklist": checklist,
        "exam_unlocked": bp.exam_unlocked_belt == next_belt,
        "all_met": all_met,
    }


def _parent_id_for_child(db: Session, child_id: int) -> int | None:
    from models import User
    child = db.get(User, child_id)
    return child.parent_id if child else None
