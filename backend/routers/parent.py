"""Parent dashboard endpoints. Require parent JWT."""
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DB
from sqlalchemy import func

from auth import require_parent, get_only_child
from database import get_db
from models import (
    User, Session as DBSession, Question, Answer, Progress, BeltProgress,
    AvatarUnlocks, DailyQuest, DailyLimit, TopicMastery, RestDay, BeltExam,
    ProgressionSuggestion, ProblemSetTemplate, MaxRival, Notification,
)
from schemas import AssignBonusIn, RestDayIn, MaxControlsIn
import ai
import mastery_context
import gate_engine
import max_engine

router = APIRouter(prefix="/api/parent", tags=["parent"], dependencies=[Depends(require_parent)])


# ── Dashboard summary ──────────────────────────────────────────
@router.get("/dashboard")
def dashboard(db: DB = Depends(get_db)):
    child = get_only_child(db)
    today = date.today()
    prog = db.query(Progress).filter_by(child_id=child.id).first()
    bp = db.query(BeltProgress).filter_by(child_id=child.id).first()
    dl = db.query(DailyLimit).filter_by(child_id=child.id, date=today).first()
    notif_count = db.query(Notification).filter_by(parent_id=child.parent_id, read=False).count()

    return {
        "child": {"name": child.name, "id": child.id},
        "xp": prog.total_xp,
        "level": prog.level,
        "streak": prog.streak_days,
        "longest_streak": prog.longest_streak,
        "belt": {
            "current": bp.current_belt,
            "current_name": gate_engine.BELT_NAMES[bp.current_belt],
            "exam_unlocked_belt": bp.exam_unlocked_belt,
            "checklist": (bp.gate_progress or {}).get("checklist", []),
        },
        "today_questions": dl.questions_completed if dl else 0,
        "cap": dl.cap if dl else 60,
        "notifications_unread": notif_count,
    }


# ── Mastery heatmap ────────────────────────────────────────────
@router.get("/mastery")
def mastery(db: DB = Depends(get_db)):
    child = get_only_child(db)
    rows = db.query(TopicMastery).filter_by(child_id=child.id).all()
    by_topic: dict[str, dict] = {}
    for r in rows:
        by_topic[r.topic] = {
            "subject": r.subject, "topic": r.topic,
            "attempts": r.attempts, "correct": r.correct,
            "accuracy": r.accuracy, "current_difficulty": r.current_difficulty,
            "suggested_difficulty": r.suggested_difficulty,
            "progression_pending": r.progression_pending,
            "last_attempted": r.last_attempted.isoformat() if r.last_attempted else None,
        }
    return {"rows": list(by_topic.values())}


@router.get("/mastery/{topic}/recent")
def mastery_topic_recent(topic: str, db: DB = Depends(get_db)):
    child = get_only_child(db)
    answers = (
        db.query(Answer, Question)
        .join(Question, Answer.question_id == Question.id)
        .filter(Answer.child_id == child.id, Question.topic == topic)
        .order_by(Answer.answered_at.desc())
        .limit(5)
        .all()
    )
    return {
        "topic": topic,
        "recent": [
            {
                "question": q.question_text,
                "is_correct": a.is_correct,
                "answered_at": a.answered_at.isoformat(),
            }
            for a, q in answers
        ],
    }


# ── Suggestions ────────────────────────────────────────────────
@router.get("/suggestions")
def suggestions(db: DB = Depends(get_db)):
    child = get_only_child(db)
    rows = db.query(ProgressionSuggestion).filter_by(child_id=child.id, status="pending").all()
    return {"suggestions": [
        {"id": r.id, "subject": r.subject, "topic": r.topic,
         "from": r.from_difficulty, "to": r.to_difficulty}
        for r in rows
    ]}


@router.post("/suggestion/{sid}/approve")
def suggestion_approve(sid: int, db: DB = Depends(get_db)):
    child = get_only_child(db)
    s = db.get(ProgressionSuggestion, sid)
    if not s or s.child_id != child.id:
        raise HTTPException(404, "Not found")
    tm = db.query(TopicMastery).filter_by(
        child_id=child.id, subject=s.subject, topic=s.topic
    ).first()
    if tm:
        tm.current_difficulty = s.to_difficulty
        tm.attempts_at_current = 0
        tm.correct_at_current = 0
        tm.progression_pending = False
        tm.suggested_difficulty = None
    s.status = "approved"
    s.approved_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.post("/suggestion/{sid}/dismiss")
def suggestion_dismiss(sid: int, db: DB = Depends(get_db)):
    child = get_only_child(db)
    s = db.get(ProgressionSuggestion, sid)
    if not s or s.child_id != child.id:
        raise HTTPException(404, "Not found")
    tm = db.query(TopicMastery).filter_by(
        child_id=child.id, subject=s.subject, topic=s.topic
    ).first()
    if tm:
        tm.progression_pending = False
        tm.suggested_difficulty = None
    s.status = "dismissed"
    db.commit()
    return {"ok": True}


# ── Bonus quest assignment ─────────────────────────────────────
@router.post("/assign-bonus")
def assign_bonus(body: AssignBonusIn, db: DB = Depends(get_db)):
    child = get_only_child(db)
    today = date.today()
    daily = db.query(DailyQuest).filter_by(child_id=child.id, date=today).first()
    if daily and daily.status != "completed":
        raise HTTPException(400, "Daily quest must be done first")
    bonus_today = db.query(DBSession).filter_by(
        child_id=child.id, session_type="bonus"
    ).filter(func.date(DBSession.assigned_at) == today).count()
    if bonus_today >= 2:
        raise HTTPException(400, "Bonus cap (2) reached today")

    dl = db.query(DailyLimit).filter_by(child_id=child.id, date=today).first()
    used = dl.questions_completed if dl else 0
    if used + 20 > 60:
        raise HTTPException(400, f"Daily 60-question cap would be exceeded ({used}/60)")

    topic = body.topic or _auto_topic(db, child.id, body.subject)
    if not topic:
        raise HTTPException(400, "No topic available for that subject")
    tm = db.query(TopicMastery).filter_by(child_id=child.id, subject=body.subject, topic=topic).first()
    difficulty = body.difficulty or (tm.current_difficulty if tm else "starter")

    sess = DBSession(
        child_id=child.id, subject=body.subject, difficulty=difficulty,
        session_type="bonus", status="pending", topic=topic,
        questions_count=20, source=body.source,
        template_id=body.template_id, assigned_by=child.parent_id,
    )
    db.add(sess); db.commit(); db.refresh(sess)
    _materialise_questions(db, sess, child.id, learn_mode=False)
    return {"session_id": sess.id}


def _auto_topic(db: DB, child_id: int, subject: str) -> str | None:
    """Weakest-attempted topic (≥3 attempts); fallback to least-attempted."""
    rows = db.query(TopicMastery).filter_by(child_id=child_id, subject=subject).all()
    if not rows:
        return None
    with_attempts = [r for r in rows if r.attempts >= 3]
    if with_attempts:
        with_attempts.sort(key=lambda r: r.accuracy)
        return with_attempts[0].topic
    rows.sort(key=lambda r: r.attempts)
    return rows[0].topic


def _materialise_questions(db: DB, sess: DBSession, child_id: int, learn_mode: bool):
    """Generate AI questions and persist them."""
    ctx = mastery_context.build_context(db, child_id, sess.subject, sess.topic or "")
    if sess.source == "template" and sess.template_id:
        tpl = db.get(ProblemSetTemplate, sess.template_id)
        if not tpl:
            raise HTTPException(404, "Template not found")
        qs = ai.generate_from_template({
            "subject": tpl.subject, "difficulty": tpl.difficulty,
            "year_group": tpl.year_group, "question_types": tpl.question_types,
            "format_notes": tpl.format_notes, "sample_questions": tpl.sample_questions,
            "visual_patterns": tpl.svg_patterns, "topic_tags": [sess.topic or "General"],
        }, sess.questions_count)
        tpl.times_used += 1
    else:
        # Belt exam needs mixed subjects — generate per subject
        if sess.session_type == "belt_exam":
            qs = _belt_exam_questions(db, child_id, sess)
        else:
            # Route to deterministic generator if topic has one — no AI hallucination
            from deterministic_questions import generate as _deterministic_gen
            topic_for_gen = sess.topic or mastery_context.TOPICS[sess.subject][0]
            det = _deterministic_gen(topic_for_gen, sess.questions_count)
            if det is not None:
                qs = det
            else:
                qs = ai.generate_questions(
                    count=sess.questions_count,
                    subject=sess.subject,
                    topic=topic_for_gen,
                    difficulty=sess.difficulty,
                    mastery_context=ctx,
                    learn_mode=learn_mode,
                )

    pos = 0
    for q in qs:
        if q.get("type") == "worked_example":
            db.add(Question(
                session_id=sess.id,
                question_text=q.get("question", ""),
                walkthrough=f"{q.get('walkthrough','')}\n\nExample: {q.get('example_question','')}\nAnswer: {q.get('example_answer','')}",
                options=[],
                correct_index=0,
                explanation="",
                topic=q.get("topic", sess.topic or ""),
                has_visual=False,
                is_worked_example=True,
                position=pos,
            ))
        else:
            db.add(Question(
                session_id=sess.id,
                question_text=q["question"],
                svg_content=q.get("svg_content"),
                image_bank_id=q.get("image_bank_id"),
                options=q["options"],
                correct_index=q["correct_index"],
                explanation=q.get("explanation", "Nice work."),
                topic=q.get("topic", sess.topic or ""),
                has_visual=bool(q.get("has_visual")),
                is_worked_example=False,
                position=pos,
            ))
        pos += 1
    sess.questions_count = pos
    # Mark learn_mode_seen
    if learn_mode and sess.topic:
        tm = db.query(TopicMastery).filter_by(
            child_id=child_id, subject=sess.subject, topic=sess.topic
        ).first()
        if tm:
            tm.learn_mode_seen = True
    db.commit()


def _belt_exam_questions(db: DB, child_id: int, sess: DBSession) -> list[dict]:
    """Mix subjects for belt exam based on belt level."""
    bp = db.query(BeltProgress).filter_by(child_id=child_id).first()
    target = bp.exam_unlocked_belt or (bp.current_belt + 1)
    # (maths, nvr, vr, diff_mix) per belt
    plan = {
        1: (5, 5, 5, [("starter", 1.0)]),
        2: (7, 7, 6, [("starter", 0.3), ("challenge", 0.7)]),
        3: (9, 8, 8, [("challenge", 0.5), ("olympiad", 0.5)]),
        4: (11, 10, 9, [("challenge", 0.3), ("olympiad", 0.7)]),
        5: (11, 10, 9, [("olympiad", 1.0)]),
    }.get(target, (5, 5, 5, [("starter", 1.0)]))
    m_count, n_count, v_count, mix = plan
    out: list[dict] = []

    def gen(subj: str, count: int):
        per_diff: list[tuple[str, int]] = []
        remaining = count
        for diff, frac in mix[:-1]:
            n = max(1, int(round(count * frac)))
            per_diff.append((diff, n))
            remaining -= n
        per_diff.append((mix[-1][0], remaining))
        for diff, n in per_diff:
            if n <= 0:
                continue
            topic = mastery_context.TOPICS[subj][0]
            ctx = mastery_context.build_context(db, child_id, subj, topic)
            out.extend(ai.generate_questions(
                count=n, subject=subj, topic=topic,
                difficulty=diff, mastery_context=ctx, learn_mode=False,
            ))

    gen("Maths", m_count)
    gen("NVR", n_count)
    gen("VR", v_count)
    return out


# ── Rest days ──────────────────────────────────────────────────
@router.post("/rest-day")
def rest_day(body: RestDayIn, db: DB = Depends(get_db)):
    child = get_only_child(db)
    parent = db.query(User).filter_by(role="parent").first()
    existing = db.query(RestDay).filter_by(child_id=child.id, date=body.date).first()
    if existing:
        return {"ok": True, "duplicate": True}
    db.add(RestDay(child_id=child.id, date=body.date, set_by=parent.id))
    db.commit()
    return {"ok": True}


@router.get("/rest-days")
def list_rest_days(db: DB = Depends(get_db)):
    child = get_only_child(db)
    rows = db.query(RestDay).filter_by(child_id=child.id).order_by(RestDay.date).all()
    return {"dates": [r.date.isoformat() for r in rows]}


# ── History ────────────────────────────────────────────────────
@router.get("/history")
def history(subject: str | None = None, db: DB = Depends(get_db)):
    child = get_only_child(db)
    q = db.query(DBSession).filter(DBSession.child_id == child.id, DBSession.status == "completed")
    if subject:
        q = q.filter(DBSession.subject == subject)
    sessions = q.order_by(DBSession.completed_at.desc()).limit(100).all()
    out = []
    for s in sessions:
        correct = (
            db.query(Answer).join(Question, Answer.question_id == Question.id)
            .filter(Question.session_id == s.id, Answer.is_correct.is_(True)).count()
        )
        out.append({
            "id": s.id, "date": s.completed_at.isoformat() if s.completed_at else None,
            "type": s.session_type, "subject": s.subject, "topic": s.topic,
            "difficulty": s.difficulty, "score": correct, "total": s.questions_count,
            "source": s.source,
        })
    return {"sessions": out}


@router.get("/weekly-summary")
def weekly_summary(db: DB = Depends(get_db)):
    child = get_only_child(db)
    today = date.today()
    start = today - timedelta(days=7)
    sessions = (
        db.query(DBSession)
        .filter(
            DBSession.child_id == child.id,
            DBSession.status == "completed",
            DBSession.completed_at >= datetime.combine(start, datetime.min.time()),
        )
        .all()
    )
    by_subject: dict[str, dict] = {}
    quests_done = 0
    for s in sessions:
        quests_done += 1
        bs = by_subject.setdefault(s.subject, {"sessions": 0, "correct": 0, "total": 0})
        bs["sessions"] += 1
        for q in db.query(Question).filter_by(session_id=s.id).all():
            a = db.query(Answer).filter_by(question_id=q.id, child_id=child.id).first()
            if a:
                bs["total"] += 1
                if a.is_correct:
                    bs["correct"] += 1
    suggs = db.query(ProgressionSuggestion).filter_by(child_id=child.id, status="pending").count()
    rival = max_engine.get_state(db)
    return {
        "quests_completed": quests_done,
        "by_subject": by_subject,
        "pending_suggestions": suggs,
        "rival": rival,
    }


# ── Belt management ────────────────────────────────────────────
@router.get("/belt-status")
def belt_status(db: DB = Depends(get_db)):
    child = get_only_child(db)
    return gate_engine.evaluate(db, child.id)


@router.post("/belt-exam/schedule")
def belt_schedule(db: DB = Depends(get_db)):
    """Toggle: 'enable now'. Child sees exam card on next home load."""
    child = get_only_child(db)
    bp = db.query(BeltProgress).filter_by(child_id=child.id).first()
    if not bp or bp.exam_unlocked_belt is None:
        raise HTTPException(400, "No belt exam currently unlocked")
    # Build the belt exam session now so child can start immediately
    sess = DBSession(
        child_id=child.id, subject="mixed",
        difficulty="exam", session_type="belt_exam", status="pending",
        questions_count=0, source="ai_generated",
        time_limit_seconds={1: 1200, 2: 1500, 3: 1800, 4: 2100, 5: 2400}.get(bp.exam_unlocked_belt, 1200),
        assigned_by=child.parent_id,
    )
    db.add(sess); db.commit(); db.refresh(sess)
    _materialise_questions(db, sess, child.id, learn_mode=False)
    return {"session_id": sess.id, "belt": bp.exam_unlocked_belt}


@router.post("/belt-exam/override-gate")
def belt_override(belt: int, db: DB = Depends(get_db)):
    child = get_only_child(db)
    bp = db.query(BeltProgress).filter_by(child_id=child.id).first()
    if not bp:
        raise HTTPException(404, "No belt progress")
    if not 1 <= belt <= 5:
        raise HTTPException(400, "Invalid belt")
    bp.exam_unlocked_belt = belt
    db.commit()
    return {"ok": True, "unlocked": belt}


@router.get("/belt-exam/history")
def belt_exam_history(db: DB = Depends(get_db)):
    child = get_only_child(db)
    rows = db.query(BeltExam).filter_by(child_id=child.id).order_by(BeltExam.attempted_at.desc()).all()
    return {"exams": [
        {"belt": r.belt_level, "score": r.score, "total": r.total, "passed": r.passed,
         "attempted_at": r.attempted_at.isoformat(), "time_taken_seconds": r.time_taken_seconds}
        for r in rows
    ]}


# ── Max controls ───────────────────────────────────────────────
@router.get("/max-controls")
def max_controls(db: DB = Depends(get_db)):
    mr = db.query(MaxRival).first()
    return {
        "current_xp": mr.current_xp,
        "cycle_day": mr.cycle_day,
        "daily_rate": mr.daily_rate,
        "base_difficulty": mr.base_difficulty,
        "surge_active": mr.surge_active,
        "history": mr.xp_history or [],
    }


@router.post("/max-controls/update")
def max_update(body: MaxControlsIn, db: DB = Depends(get_db)):
    mr = db.query(MaxRival).first()
    if body.base_difficulty in ("friendly", "standard", "competitive"):
        mr.base_difficulty = body.base_difficulty
    if body.manual_xp is not None:
        mr.current_xp = max(0, body.manual_xp)
    db.commit()
    return {"ok": True}


@router.post("/max-controls/reset")
def max_reset(db: DB = Depends(get_db)):
    """New Semester: reset child XP + Max XP + belts. Badges kept."""
    child = get_only_child(db)
    prog = db.query(Progress).filter_by(child_id=child.id).first()
    bp = db.query(BeltProgress).filter_by(child_id=child.id).first()
    mr = db.query(MaxRival).first()
    if prog:
        prog.total_xp = 0
        prog.level = "Apprentice"
    if bp:
        bp.current_belt = 0
        bp.bronze_gate_met = bp.silver_gate_met = bp.gold_gate_met = False
        bp.platinum_gate_met = bp.elite_gate_met = False
        bp.exam_unlocked_belt = None
    if mr:
        mr.current_xp = 0
        mr.cycle_day = 1
    db.commit()
    return {"ok": True}


# ── Notifications ──────────────────────────────────────────────
@router.get("/notifications")
def notifications(db: DB = Depends(get_db)):
    child = get_only_child(db)
    rows = (
        db.query(Notification)
        .filter_by(parent_id=child.parent_id)
        .order_by(Notification.created_at.desc())
        .limit(20).all()
    )
    return {"items": [
        {"id": r.id, "kind": r.kind, "message": r.message, "payload": r.payload,
         "created_at": r.created_at.isoformat(), "read": r.read}
        for r in rows
    ]}


@router.post("/notifications/{nid}/read")
def notif_read(nid: int, db: DB = Depends(get_db)):
    n = db.get(Notification, nid)
    if n:
        n.read = True
        db.commit()
    return {"ok": True}
