"""Build the mastery-context string injected into AI generation prompts."""
from sqlalchemy.orm import Session

from models import TopicMastery, Session as DBSession, Question


TOPICS = {
    "Maths": [
        # Deterministic-generated topics first (no AI; guaranteed correct)
        "Mental Arithmetic",       # 86 Schofield MA1-style templates
        "Times & Division Mix",
        "Division 2÷1", "Division 3÷1",
        # AI-generated topics — used when deterministic ones are mastered
        "Number Patterns", "Factors & Multiples",
        "Fractions", "Place Value", "Word Problems", "Shape Area",
        "Perimeter", "Angles", "Sequences & Series", "Time & Calendars",
        "Logic Puzzles", "Probability",
    ],
    "NVR": [
        "NVR Sequences", "NVR Matrices", "NVR Odd One Out",
        "NVR Rotations", "NVR Analogies",
    ],
    "VR": [
        "Word Analogies", "Letter Sequences", "Number Codes",
        "Missing Words", "Logical Deduction", "Hidden Words",
        "Word Connections",
    ],
}


def all_topics(subject: str) -> list[str]:
    return TOPICS.get(subject, [])


def all_subjects() -> list[str]:
    return list(TOPICS.keys())


def build_context(db: Session, child_id: int, subject: str, topic: str) -> str:
    rows = db.query(TopicMastery).filter_by(child_id=child_id, subject=subject).all()
    by_topic = {r.topic: r for r in rows}

    strong, developing, weak, unseen = [], [], [], []
    for t in TOPICS.get(subject, []):
        r = by_topic.get(t)
        if not r or r.attempts == 0:
            unseen.append(t)
        elif r.accuracy >= 0.8:
            strong.append(t)
        elif r.accuracy >= 0.5:
            developing.append(t)
        else:
            weak.append(t)

    # Recent question styles to avoid (last 3 sessions on this topic)
    recent_q_texts: list[str] = []
    recent_sessions = (
        db.query(DBSession)
        .filter(DBSession.child_id == child_id, DBSession.topic == topic)
        .order_by(DBSession.assigned_at.desc())
        .limit(3)
        .all()
    )
    for s in recent_sessions:
        qs = db.query(Question).filter_by(session_id=s.id).limit(3).all()
        recent_q_texts.extend(q.question_text[:80] for q in qs)

    def join(lst): return ", ".join(lst) if lst else "—"

    ctx = (
        f"Strong topics (>80%): {join(strong)}\n"
        f"Developing (50-80%): {join(developing)}\n"
        f"Weak (<50%): {join(weak)}\n"
        f"Not yet seen: {join(unseen)}\n"
        f"Current focus: {topic}\n"
    )
    if recent_q_texts:
        ctx += "Avoid repeating these recent question styles:\n"
        for q in recent_q_texts[:6]:
            ctx += f"  - {q}\n"
    return ctx
