"""Child-facing endpoints. No JWT — single-child app."""
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DB
from sqlalchemy import func

from auth import get_only_child
from database import get_db
from models import (
    Session as DBSession, Question, Answer, Progress, BeltProgress,
    AvatarUnlocks, DailyQuest, DailyLimit, TopicMastery, RestDay, BeltExam,
    Notification,
)
from schemas import (
    ChildHomeOut, SessionOut, QuestionOut, AnswerIn, AnswerResultOut,
    CompleteSessionOut,
)
import progression_engine
import gate_engine
import badge_engine
import max_engine
from gate_engine import BELT_NAMES

router = APIRouter(prefix="/api/child", tags=["child"])


# ── XP + Level helpers ─────────────────────────────────────────
LEVELS = [
    ("Apprentice", 0),
    ("Scholar", 500),
    ("Champion", 1500),
    ("Wizard", 3500),
    ("Olympiad Master", 7000),
]


def level_for_xp(xp: int) -> tuple[str, dict | None]:
    name = LEVELS[0][0]
    next_info = None
    for i, (n, thr) in enumerate(LEVELS):
        if xp >= thr:
            name = n
            if i + 1 < len(LEVELS):
                nname, nthr = LEVELS[i + 1]
                next_info = {"name": nname, "at": nthr, "remaining": nthr - xp}
    return name, next_info


def xp_for_correct(difficulty: str) -> int:
    return {"starter": 10, "challenge": 15, "olympiad": 25}.get(difficulty, 10)


def hint_cost(base: int) -> int:
    return max(1, base // 2)


# ── Home ───────────────────────────────────────────────────────
@router.get("/home", response_model=ChildHomeOut)
def home(db: DB = Depends(get_db)):
    child = get_only_child(db)
    today = date.today()

    prog = db.query(Progress).filter_by(child_id=child.id).first()
    bp = db.query(BeltProgress).filter_by(child_id=child.id).first()
    avatar = db.query(AvatarUnlocks).filter_by(child_id=child.id).first()

    level_name, next_info = level_for_xp(prog.total_xp)

    # Daily quest today
    daily = (
        db.query(DailyQuest)
        .filter_by(child_id=child.id, date=today)
        .first()
    )
    daily_card = None
    if daily:
        sess = db.get(DBSession, daily.session_id)
        daily_card = {
            "id": daily.session_id,
            "subject": daily.subject,
            "status": daily.status,
            "xp_awarded": daily.xp_awarded,
            "score": _session_score(db, daily.session_id),
            "total": sess.questions_count if sess else 5,
        }

    # Rest day?
    is_rest = db.query(RestDay).filter_by(child_id=child.id, date=today).first() is not None
    if is_rest and daily_card is None:
        daily_card = {"id": None, "subject": "Rest", "status": "rest_day", "xp_awarded": 0, "score": 0, "total": 0}

    # Bonus quests
    bonus_q = []
    if daily and daily.status == "completed":
        bonus_sessions = (
            db.query(DBSession)
            .filter_by(child_id=child.id, session_type="bonus", status="pending")
            .filter(func.date(DBSession.assigned_at) == today)
            .all()
        )
        for s in bonus_sessions:
            bonus_q.append({
                "id": s.id, "subject": s.subject, "topic": s.topic,
                "difficulty": s.difficulty, "questions_count": s.questions_count,
            })

    # Belt exam ready
    belt_exam_ready = bp.exam_unlocked_belt is not None and bp.exam_unlocked_belt > bp.current_belt

    # Daily cap remaining
    dl = db.query(DailyLimit).filter_by(child_id=child.id, date=today).first()
    cap_remaining = (dl.cap - dl.questions_completed) if dl else 25

    # Rival
    rival = max_engine.get_state(db)

    # Weekly XP
    week_start = today - timedelta(days=today.weekday())
    weekly_xp = _xp_since(db, child.id, datetime.combine(week_start, datetime.min.time()))
    last_week_start = week_start - timedelta(days=7)
    weekly_best = _xp_since(db, child.id, datetime.combine(last_week_start, datetime.min.time())) - weekly_xp
    weekly_best = max(weekly_best, weekly_xp)

    return ChildHomeOut(
        name=child.name,
        xp=prog.total_xp,
        level=level_name,
        next_level=next_info,
        streak=prog.streak_days,
        longest_streak=prog.longest_streak,
        belt={
            "current": bp.current_belt,
            "current_name": BELT_NAMES[bp.current_belt],
            "next_name": BELT_NAMES[bp.current_belt + 1] if bp.current_belt < 5 else None,
            "exam_unlocked": belt_exam_ready,
            "exam_unlocked_belt": bp.exam_unlocked_belt,
            "checklist": (bp.gate_progress or {}).get("checklist", []),
        },
        daily_quest=daily_card,
        bonus_quests=bonus_q,
        badges=prog.badges or [],
        avatar={
            "active_items": avatar.active_items if avatar else [],
            "theme": avatar.theme if avatar else "default",
            "unlocked_items": avatar.unlocked_items if avatar else [],
        },
        rival=rival,
        sound_enabled=prog.sound_enabled,
        weekly_xp=weekly_xp,
        weekly_best_xp=weekly_best,
        cap_remaining=cap_remaining,
    )


def _xp_since(db: DB, child_id: int, since: datetime) -> int:
    """Approximate weekly XP from completed sessions since timestamp."""
    rows = (
        db.query(DBSession)
        .filter(
            DBSession.child_id == child_id,
            DBSession.status == "completed",
            DBSession.completed_at >= since,
        )
        .all()
    )
    # Crude: 10 XP per correct answer in completed sessions
    total = 0
    for s in rows:
        for q in db.query(Question).filter_by(session_id=s.id).all():
            a = db.query(Answer).filter_by(question_id=q.id, child_id=child_id, is_correct=True).first()
            if a:
                total += xp_for_correct(s.difficulty)
    return total


def _session_score(db: DB, session_id: int) -> int:
    return (
        db.query(Answer)
        .join(Question, Answer.question_id == Question.id)
        .filter(Question.session_id == session_id, Answer.is_correct.is_(True))
        .count()
    )


# ── Quest fetch ────────────────────────────────────────────────
@router.get("/quest/{session_id}", response_model=SessionOut)
def get_quest(session_id: int, db: DB = Depends(get_db)):
    child = get_only_child(db)
    sess = db.get(DBSession, session_id)
    if not sess or sess.child_id != child.id:
        raise HTTPException(404, "Session not found")
    if sess.status == "pending":
        sess.status = "active"
        db.commit()
    qs = db.query(Question).filter_by(session_id=session_id).order_by(Question.position).all()
    return SessionOut.model_validate({
        "id": sess.id,
        "subject": sess.subject,
        "difficulty": sess.difficulty,
        "session_type": sess.session_type,
        "status": sess.status,
        "questions_count": sess.questions_count,
        "topic": sess.topic,
        "time_limit_seconds": sess.time_limit_seconds,
        "questions": [QuestionOut.model_validate(q) for q in qs],
    })


# ── Answer ─────────────────────────────────────────────────────
@router.post("/answer", response_model=AnswerResultOut)
def submit_answer(body: AnswerIn, db: DB = Depends(get_db)):
    child = get_only_child(db)
    q = db.get(Question, body.question_id)
    if not q:
        raise HTTPException(404, "Question not found")
    sess = db.get(DBSession, q.session_id)
    if not sess or sess.child_id != child.id:
        raise HTTPException(403, "Not your question")

    existing = db.query(Answer).filter_by(question_id=q.id, child_id=child.id).first()
    if existing:
        # Idempotent re-answer
        return AnswerResultOut(
            is_correct=existing.is_correct,
            correct_index=q.correct_index,
            explanation=q.explanation,
            xp_awarded=0,
            combo=0,
        )

    correct = body.selected_index == q.correct_index
    ans = Answer(
        question_id=q.id, child_id=child.id,
        selected_index=body.selected_index, is_correct=correct,
        time_taken_ms=body.time_taken_ms, used_hint=body.used_hint,
    )
    db.add(ans)

    # XP rules — belt exams award no in-session XP
    xp = 0
    if sess.session_type != "belt_exam":
        if correct:
            xp = xp_for_correct(sess.difficulty)
            if body.used_hint:
                xp = hint_cost(xp)
        else:
            xp = 5  # never zero

    # Combo — count consecutive corrects in this session up to and including this question
    combo = 0
    if sess.session_type != "belt_exam":
        prior = (
            db.query(Answer)
            .join(Question, Answer.question_id == Question.id)
            .filter(Question.session_id == sess.id, Answer.child_id == child.id)
            .order_by(Answer.answered_at.asc())
            .all()
        )
        combo = 1 if correct else 0
        for a in reversed(prior):
            if a.is_correct:
                combo += 1
            else:
                break
        # Apply combo multiplier on top of base XP
        if combo >= 5:
            xp = int(xp * 3)
        elif combo >= 3:
            xp = int(xp * 2)

    db.commit()

    return AnswerResultOut(
        is_correct=correct,
        correct_index=q.correct_index,
        explanation=q.explanation,
        xp_awarded=xp,
        combo=combo,
    )


# ── Complete session ───────────────────────────────────────────
@router.post("/complete/{session_id}", response_model=CompleteSessionOut)
def complete(session_id: int, db: DB = Depends(get_db)):
    child = get_only_child(db)
    sess = db.get(DBSession, session_id)
    if not sess or sess.child_id != child.id:
        raise HTTPException(404, "Session not found")
    if sess.status == "completed":
        return _build_complete_response(db, child.id, sess)

    sess.status = "completed"
    sess.completed_at = datetime.utcnow()
    db.commit()

    # Score and XP
    questions = db.query(Question).filter_by(session_id=session_id).all()
    answers = []
    score = 0
    base_xp = 0
    bonus_xp = 0
    max_combo = 0
    running_combo = 0
    for q in sorted(questions, key=lambda x: x.position):
        a = db.query(Answer).filter_by(question_id=q.id, child_id=child.id).first()
        if not a:
            continue
        answers.append(a)
        if a.is_correct:
            score += 1
            if sess.session_type != "belt_exam":
                xp = xp_for_correct(sess.difficulty)
                if a.used_hint:
                    xp = hint_cost(xp)
                running_combo += 1
                if running_combo >= 5:
                    xp *= 3
                elif running_combo >= 3:
                    xp *= 2
                base_xp += xp
                max_combo = max(max_combo, running_combo)
        else:
            if sess.session_type != "belt_exam":
                base_xp += 5
            running_combo = 0

    # Streak handling — only daily quest completion increments streak
    today = date.today()
    prog = db.query(Progress).filter_by(child_id=child.id).first()
    bp = db.query(BeltProgress).filter_by(child_id=child.id).first()
    daily_done = False
    streak_mult = 1.0

    daily = db.query(DailyQuest).filter_by(child_id=child.id, date=today, session_id=session_id).first()
    if daily and sess.session_type == "daily":
        daily.status = "completed"
        daily.completed_at = datetime.utcnow()
        daily_done = True
        streak_mult = 1.5
        # Streak
        if prog.last_active == today - timedelta(days=1) or prog.last_active == today:
            prog.streak_days = prog.streak_days + (0 if prog.last_active == today else 1)
        else:
            prog.streak_days = 1
        prog.longest_streak = max(prog.longest_streak, prog.streak_days)
        prog.last_active = today

    total_session_xp = int(base_xp * streak_mult) + bonus_xp

    # Belt exam outcomes
    level_up = None
    if sess.session_type == "belt_exam":
        total = len(questions)
        threshold = 0.80 if (sess.difficulty in ("starter", "challenge")) else 0.85
        if (bp and bp.exam_unlocked_belt and bp.exam_unlocked_belt == 5):
            threshold = 0.90
        passed = total > 0 and (score / total) >= threshold
        attempt = BeltExam(
            child_id=child.id,
            belt_level=bp.exam_unlocked_belt or (bp.current_belt + 1),
            session_id=sess.id, score=score, total=total, passed=passed,
            time_taken_seconds=int((sess.completed_at - sess.assigned_at).total_seconds()),
        )
        db.add(attempt)
        if passed:
            new_belt = bp.exam_unlocked_belt
            bp.current_belt = new_belt
            bp.exam_unlocked_belt = None
            # XP bonus per belt
            bonus = {1: 200, 2: 350, 3: 500, 4: 750, 5: 1000}.get(new_belt, 0)
            total_session_xp += bonus
            # Theme + avatar items
            avu = db.query(AvatarUnlocks).filter_by(child_id=child.id).first()
            theme_map = {1: "gold", 2: "silver", 3: "royal", 4: "midnight", 5: "elite"}
            item_map = {1: "bronze_badge", 2: "silver_cape", 3: "trophy", 4: "diamond", 5: "gold_crown"}
            if avu:
                avu.theme = theme_map.get(new_belt, avu.theme)
                avu.unlocked_items = list({*avu.unlocked_items, item_map.get(new_belt, "")})
                avu.active_items = avu.unlocked_items
        else:
            # Record attempt cooldown
            attempts = bp.exam_attempts or {}
            attempts[str(bp.exam_unlocked_belt or (bp.current_belt + 1))] = datetime.utcnow().isoformat()
            bp.exam_attempts = attempts

    # Apply XP
    if prog and total_session_xp:
        before = prog.total_xp
        prog.total_xp = before + total_session_xp
        new_level, _ = level_for_xp(prog.total_xp)
        if new_level != prog.level:
            level_up = {"from": prog.level, "to": new_level, "xp": prog.total_xp}
            prog.level = new_level
            db.add(Notification(
                parent_id=child.parent_id,
                kind="level_up",
                message=f"🎉 Samihan reached {new_level}!",
                payload={"level": new_level},
            ))

    # Daily limit increment (regular daily + bonus only)
    if sess.session_type in ("daily", "bonus"):
        dl = db.query(DailyLimit).filter_by(child_id=child.id, date=today).first()
        if not dl:
            dl = DailyLimit(child_id=child.id, date=today, questions_completed=0)
            db.add(dl)
            db.flush()
        dl.questions_completed += len(questions)

    db.commit()

    # Award daily quest XP record
    if daily and daily_done:
        daily.xp_awarded = total_session_xp
        db.commit()

    # Run engines
    progression_engine.run(db, child.id, session_id)
    gate_state = gate_engine.evaluate(db, child.id)
    new_badges = badge_engine.evaluate(
        db, child.id,
        session_score=score, session_total=len(questions),
        max_combo=max_combo,
    )

    return CompleteSessionOut(
        score=score,
        total=len(questions),
        xp_breakdown={
            "base": base_xp,
            "streak_multiplier": streak_mult,
            "session_total": total_session_xp,
            "max_combo": max_combo,
        },
        xp_total_session=total_session_xp,
        new_badges=new_badges,
        level_up=level_up,
        belt_progress=gate_state,
        streak=prog.streak_days if prog else 0,
        daily_done=daily_done,
        rival=max_engine.get_state(db),
    )


def _build_complete_response(db: DB, child_id: int, sess: DBSession) -> CompleteSessionOut:
    questions = db.query(Question).filter_by(session_id=sess.id).all()
    score = sum(
        1 for q in questions
        if (a := db.query(Answer).filter_by(question_id=q.id, child_id=child_id).first()) and a.is_correct
    )
    prog = db.query(Progress).filter_by(child_id=child_id).first()
    return CompleteSessionOut(
        score=score, total=len(questions),
        xp_breakdown={"base": 0, "streak_multiplier": 1.0, "session_total": 0, "max_combo": 0},
        xp_total_session=0, new_badges=[], level_up=None,
        belt_progress=gate_engine.evaluate(db, child_id),
        streak=prog.streak_days if prog else 0,
        daily_done=False,
        rival=max_engine.get_state(db),
    )


# ── Settings ───────────────────────────────────────────────────
@router.post("/sound-toggle")
def sound_toggle(db: DB = Depends(get_db)):
    child = get_only_child(db)
    prog = db.query(Progress).filter_by(child_id=child.id).first()
    prog.sound_enabled = not prog.sound_enabled
    db.commit()
    return {"sound_enabled": prog.sound_enabled}


@router.get("/hint/{question_id}")
def hint(question_id: int, db: DB = Depends(get_db)):
    """Generate a thinking-direction hint without revealing the answer."""
    child = get_only_child(db)
    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(404, "Question not found")
    sess = db.get(DBSession, q.session_id)
    if not sess or sess.child_id != child.id:
        raise HTTPException(403, "Not yours")
    if sess.session_type == "belt_exam":
        raise HTTPException(403, "No hints during belt exams")

    # Track hint usage on topic
    tm = db.query(TopicMastery).filter_by(child_id=child.id, subject=sess.subject, topic=q.topic).first()
    if tm:
        tm.hint_usage_count += 1
        db.commit()

    return {"hint": _build_hint(q)}


def _build_hint(q: Question) -> str:
    t = q.topic.lower()
    if "sequence" in t or "pattern" in t:
        return "Look at the difference between each number — is it growing, shrinking, or repeating?"
    if "fraction" in t:
        return "Make the denominators the same first, then compare the numerators."
    if "area" in t:
        return "Area = length × width. Read the diagram carefully."
    if "perimeter" in t:
        return "Add up all the sides. Count them twice if you must."
    if "factor" in t or "multiple" in t:
        return "Try dividing — if it divides evenly, it's a factor."
    if "nvr" in t:
        return "What's changing between the shapes — size, rotation, count, or shading?"
    if "analog" in t:
        return "Find the relationship in the first pair, then apply it to the second."
    return "Read the question twice. What is it actually asking for?"
