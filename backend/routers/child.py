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
    Notification, User,
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

# Per-day question ceiling, mirrors DailyLimit.cap model default. Extra
# ("keep playing") quests are blocked once the day's completed questions
# would exceed this.
DEFAULT_DAILY_CAP = 100
EXTRA_QUEST_QUESTIONS = 20


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


# Cosmetic XP-milestone unlocks. Pure collectibles — every 500 XP a new emoji
# avatar / theme item drops, so the dopamine flow doesn't depend on hitting
# rare belt exams.
XP_UNLOCKS = [
    {"at":   500, "item": "star_001",    "label": "🌟 Star",      "emoji": "🌟"},
    {"at":  1000, "item": "rocket_001",  "label": "🚀 Rocket",    "emoji": "🚀"},
    {"at":  2000, "item": "fire_001",    "label": "🔥 Fire",      "emoji": "🔥"},
    {"at":  3500, "item": "lightning",   "label": "⚡ Lightning", "emoji": "⚡"},
    {"at":  5000, "item": "wizard_hat",  "label": "🧙 Wizard Hat","emoji": "🧙"},
    {"at":  7000, "item": "crown",       "label": "👑 Crown",     "emoji": "👑"},
    {"at": 10000, "item": "robot",       "label": "🤖 Robot",     "emoji": "🤖"},
    {"at": 15000, "item": "unicorn",     "label": "🦄 Unicorn",   "emoji": "🦄"},
    {"at": 20000, "item": "shield",      "label": "🛡️ Shield",    "emoji": "🛡️"},
    {"at": 25000, "item": "rainbow",     "label": "🌈 Rainbow",   "emoji": "🌈"},
    {"at": 35000, "item": "dragon",      "label": "🐉 Dragon",    "emoji": "🐉"},
]


def _apply_xp_unlocks(db, child_id: int, xp_before: int, xp_after: int) -> list[dict]:
    """If this session's XP gain crossed any unlock thresholds, add them to the
    child's AvatarUnlocks and return the freshly-unlocked items so the
    completion screen can pop them as a reward."""
    crossed = [u for u in XP_UNLOCKS if xp_before < u["at"] <= xp_after]
    if not crossed:
        return []
    avu = db.query(AvatarUnlocks).filter_by(child_id=child_id).first()
    if not avu:
        return []
    existing = set(avu.unlocked_items or [])
    fresh = [u for u in crossed if u["item"] not in existing]
    if fresh:
        avu.unlocked_items = list(existing | {u["item"] for u in fresh})
        db.commit()
    return fresh


# ── Home ───────────────────────────────────────────────────────
@router.get("/home", response_model=ChildHomeOut)
def home(child: User = Depends(get_only_child), db: DB = Depends(get_db)):
    today = date.today()

    prog = db.query(Progress).filter_by(child_id=child.id).first()
    bp = db.query(BeltProgress).filter_by(child_id=child.id).first()
    avatar = db.query(AvatarUnlocks).filter_by(child_id=child.id).first()

    level_name, next_info = level_for_xp(prog.total_xp)

    # Daily quest today — create on demand if the midnight cron didn't run
    # (fresh deploy, restart, or process was down at 00:05). Returns the
    # existing row if present, or None on a rest day.
    from daily_scheduler import ensure_daily_quest
    daily = ensure_daily_quest(db, child.id)
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
    cap_remaining = (dl.cap - dl.questions_completed) if dl else DEFAULT_DAILY_CAP

    # Rival
    rival = max_engine.get_state(db, child.id)

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
        weak_spots=_compute_weak_spots(db, child.id),
        recent_quests=_recent_quests(db, child.id, limit=5),
    )


@router.post("/extra-quest")
def extra_quest(child: User = Depends(get_only_child), db: DB = Depends(get_db)):
    """Child-initiated 'keep playing' quest. Generates a fresh bonus session
    (full XP, feeds the Max rival) on the adaptively-picked weakest topic,
    bounded by the per-day question cap."""
    from daily_scheduler import ensure_daily_quest, subject_for_date, _pick_topic
    from routers.parent import _materialise_questions

    today = date.today()

    # The daily quest is the priority — it must be done before extras unlock.
    # ensure_daily_quest returns None on a rest day, where extras are allowed.
    daily = ensure_daily_quest(db, child.id)
    if daily is not None and daily.status != "completed":
        raise HTTPException(400, "Finish today's Daily Quest first.")

    # Per-day question cap
    dl = db.query(DailyLimit).filter_by(child_id=child.id, date=today).first()
    used = dl.questions_completed if dl else 0
    cap = dl.cap if dl else DEFAULT_DAILY_CAP
    if used + EXTRA_QUEST_QUESTIONS > cap:
        raise HTTPException(429, "You've smashed today's question limit — come back tomorrow!")

    subject = subject_for_date(today)
    topic = _pick_topic(db, child.id, subject)
    tm = db.query(TopicMastery).filter_by(child_id=child.id, subject=subject, topic=topic).first()
    difficulty = tm.current_difficulty if tm else "starter"

    sess = DBSession(
        child_id=child.id, subject=subject, difficulty=difficulty,
        session_type="bonus", status="pending", topic=topic,
        questions_count=EXTRA_QUEST_QUESTIONS, source="ai_generated",
    )
    db.add(sess); db.commit(); db.refresh(sess)

    _materialise_questions(db, sess, child.id, learn_mode=False)
    db.commit()  # persist the Question rows from _materialise_questions
    return {"session_id": sess.id, "subject": subject, "topic": topic}


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
def get_quest(session_id: int, child: User = Depends(get_only_child), db: DB = Depends(get_db)):
    sess = db.get(DBSession, session_id)
    if not sess or sess.child_id != child.id:
        raise HTTPException(404, "Session not found")

    # If the child is (re-)opening a daily/bonus quest they haven't started
    # answering yet, reshuffle the questions. Also self-heals: if the session
    # somehow has zero questions (silent generator failure, partial commit),
    # we always re-materialise so the quest renders instead of going blank.
    if sess.status != "completed" and sess.session_type in ("daily", "bonus"):
        answered = (
            db.query(Answer)
            .join(Question, Answer.question_id == Question.id)
            .filter(Question.session_id == session_id, Answer.child_id == child.id)
            .first()
        )
        if answered is None:
            db.query(Question).filter_by(session_id=session_id).delete(synchronize_session=False)
            from routers.parent import _materialise_questions
            _materialise_questions(db, sess, child.id, learn_mode=False)
            # MUST commit here — if sess.status is already 'active' the
            # status-transition commit below won't fire and the new questions
            # would get rolled back when the request ends.
            db.commit()

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
def submit_answer(body: AnswerIn, child: User = Depends(get_only_child), db: DB = Depends(get_db)):
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
def complete(session_id: int, child: User = Depends(get_only_child), db: DB = Depends(get_db)):
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
        # Streak
        if prog.last_active == today - timedelta(days=1) or prog.last_active == today:
            prog.streak_days = prog.streak_days + (0 if prog.last_active == today else 1)
        else:
            prog.streak_days = 1
        prog.longest_streak = max(prog.longest_streak, prog.streak_days)
        prog.last_active = today
        # Streak escalation — longer streaks compound the daily multiplier
        if prog.streak_days >= 30: streak_mult = 2.5
        elif prog.streak_days >= 14: streak_mult = 2.0
        elif prog.streak_days >= 7:  streak_mult = 1.75
        else: streak_mult = 1.5

    # Performance bonuses — visible "BONUS! +X" surprises on the completion screen
    perfect_bonus = 0
    strong_bonus = 0
    if sess.session_type != "belt_exam" and len(questions) > 0:
        pct = score / len(questions)
        if pct >= 1.0:
            perfect_bonus = 200
        elif pct >= 0.9:
            strong_bonus = 100

    total_session_xp = int(base_xp * streak_mult) + bonus_xp + perfect_bonus + strong_bonus

    # Belt exam outcomes
    level_up = None
    if sess.session_type == "belt_exam":
        total = len(questions)
        threshold = 0.80 if (sess.difficulty in ("starter", "challenge")) else 0.85
        # Top-tier belts ramp the pass bar — each rarer rank demands a tighter exam.
        if bp and bp.exam_unlocked_belt:
            threshold = {5: 0.90, 6: 0.92, 7: 0.94, 8: 0.96}.get(bp.exam_unlocked_belt, threshold)
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
            bonus = {1: 200, 2: 350, 3: 500, 4: 750, 5: 1000,
                     6: 1500, 7: 2500, 8: 5000}.get(new_belt, 0)
            total_session_xp += bonus
            # Theme + avatar items
            avu = db.query(AvatarUnlocks).filter_by(child_id=child.id).first()
            theme_map = {1: "gold", 2: "silver", 3: "royal", 4: "midnight", 5: "elite",
                         6: "diamond", 7: "mythic", 8: "legend"}
            item_map = {1: "bronze_badge", 2: "silver_cape", 3: "trophy", 4: "diamond", 5: "gold_crown",
                        6: "diamond_crown", 7: "mythic_star", 8: "dragon_emblem"}
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
    new_unlocks: list[dict] = []
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
                message=f"🎉 {child.name} reached {new_level}!",
                payload={"level": new_level},
            ))
        # XP-milestone cosmetic unlocks (run before commit so they persist together)
        new_unlocks = _apply_xp_unlocks(db, child.id, before, prog.total_xp)

    # Daily limit increment (everything except belt exams counts toward the cap)
    if sess.session_type in ("daily", "bonus", "weak_spot"):
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

    # Run engines — capture promotion events so we can award a graduation bonus
    promo_events = progression_engine.run(db, child.id, session_id)
    promotions = [e for e in promo_events if e["kind"] == "promoted"]
    graduation_bonus = 150 * len(promotions)
    if graduation_bonus and prog:
        prog.total_xp += graduation_bonus
        total_session_xp += graduation_bonus
        # Re-check level since the extra XP might cross a threshold
        new_level, _ = level_for_xp(prog.total_xp)
        if new_level != prog.level:
            level_up = {"from": prog.level, "to": new_level, "xp": prog.total_xp}
            prog.level = new_level
        db.commit()

    gate_state = gate_engine.evaluate(db, child.id)
    new_badges = badge_engine.evaluate(
        db, child.id,
        session_score=score, session_total=len(questions),
        max_combo=max_combo,
    )

    # Motivation extras: current rank, belt, personal best on this topic
    cur_level_name, next_info = level_for_xp(prog.total_xp) if prog else (None, None)
    belt_name = BELT_NAMES[bp.current_belt] if bp else None
    pb = _personal_best_for_topic(db, child.id, sess, current_score=score)
    has_wrong = any(
        not (a := db.query(Answer).filter_by(question_id=q.id, child_id=child.id).first())
        or not a.is_correct
        for q in questions if not q.is_worked_example
    )

    return CompleteSessionOut(
        score=score,
        total=len(questions),
        xp_breakdown={
            "base": base_xp,
            "streak_multiplier": streak_mult,
            "session_total": total_session_xp,
            "max_combo": max_combo,
            "perfect_bonus": perfect_bonus,
            "strong_bonus": strong_bonus,
            "graduation_bonus": graduation_bonus,
            "promotions": promotions,
        },
        xp_total_session=total_session_xp,
        new_badges=new_badges,
        level_up=level_up,
        belt_progress=gate_state,
        streak=prog.streak_days if prog else 0,
        daily_done=daily_done,
        rival=max_engine.get_state(db, child.id),
        level=cur_level_name,
        level_total_xp=prog.total_xp if prog else None,
        level_next=next_info,
        belt_name=belt_name,
        personal_best=pb,
        has_wrong_answers=has_wrong,
        new_unlocks=new_unlocks,
        weak_spots=_compute_weak_spots(db, child.id),
    )


def _personal_best_for_topic(db: DB, child_id: int, sess: DBSession, current_score: int) -> dict | None:
    """Compare current session score against prior completed sessions on the
    same topic. Returns None if no prior attempts. Daily/bonus only."""
    if not sess.topic or sess.session_type == "belt_exam":
        return None
    prior = (
        db.query(DBSession)
        .filter(
            DBSession.child_id == child_id,
            DBSession.topic == sess.topic,
            DBSession.id != sess.id,
            DBSession.status == "completed",
            DBSession.session_type.in_(["daily", "bonus"]),
        )
        .all()
    )
    if not prior:
        return None
    best_score = 0
    best_total = 0
    for s in prior:
        sc = _session_score(db, s.id)
        if sc > best_score:
            best_score = sc
            best_total = db.query(Question).filter_by(session_id=s.id).count()
    if best_total == 0:
        return None
    return {
        "is_new_best": current_score > best_score,
        "previous_best_score": best_score,
        "previous_best_total": best_total,
    }


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
        rival=max_engine.get_state(db, child.id),
    )


# ── Weak-spot detection + remedial quest ───────────────────────
WEAK_MIN_ATTEMPTS = 5      # need enough data to call a topic 'weak'
WEAK_ACC_THRESHOLD = 0.65  # overall accuracy below this = weak
WEAK_LAST5_MAX = 2         # OR ≤ 2/5 right recently = weak


def _compute_weak_spots(db: DB, child_id: int) -> list[dict]:
    """Look at TopicMastery rows and surface topics where the child is
    consistently underperforming. Two qualifying patterns:
      (a) accuracy < 65% over 5+ attempts (durable struggle)
      (b) last 5 answers had ≤ 2 right (recent slump)
    Returns up to 3 weakest, sorted hardest-first."""
    rows = (
        db.query(TopicMastery)
        .filter_by(child_id=child_id)
        .filter(TopicMastery.attempts >= WEAK_MIN_ATTEMPTS)
        .all()
    )
    weak = []
    for r in rows:
        durable = r.accuracy < WEAK_ACC_THRESHOLD
        recent = r.last5_correct <= WEAK_LAST5_MAX
        if not (durable or recent):
            continue
        reasons = []
        if durable:
            reasons.append(f"only {int(r.accuracy * 100)}% over {r.attempts} attempts")
        if recent:
            reasons.append(f"just {r.last5_correct}/5 right recently")
        weak.append({
            "subject": r.subject,
            "topic": r.topic,
            "accuracy": round(r.accuracy, 2),
            "attempts": r.attempts,
            "last5_correct": r.last5_correct,
            "difficulty": r.current_difficulty,
            "reason": " · ".join(reasons),
        })
    weak.sort(key=lambda w: (w["last5_correct"], w["accuracy"]))
    return weak[:3]


def _recent_quests(db: DB, child_id: int, limit: int = 5) -> list[dict]:
    sessions = (
        db.query(DBSession)
        .filter(
            DBSession.child_id == child_id,
            DBSession.status == "completed",
            DBSession.session_type.in_(("daily", "bonus", "weak_spot")),
        )
        .order_by(DBSession.completed_at.desc())
        .limit(limit)
        .all()
    )
    out = []
    for s in sessions:
        q_ids = [q.id for q in db.query(Question).filter_by(session_id=s.id).all()]
        if not q_ids:
            continue
        correct = (
            db.query(Answer)
            .filter(Answer.question_id.in_(q_ids), Answer.child_id == child_id, Answer.is_correct.is_(True))
            .count()
        )
        wrong = (
            db.query(Answer)
            .filter(Answer.question_id.in_(q_ids), Answer.child_id == child_id, Answer.is_correct.is_(False))
            .count()
        )
        out.append({
            "id": s.id,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            "subject": s.subject,
            "topic": s.topic,
            "difficulty": s.difficulty,
            "session_type": s.session_type,
            "score": correct,
            "total": s.questions_count,
            "has_wrong_answers": wrong > 0,
        })
    return out


@router.get("/recent-quests")
def recent_quests(child: User = Depends(get_only_child), db: DB = Depends(get_db)):
    return {"quests": _recent_quests(db, child.id, limit=10)}


@router.get("/weak-spots")
def weak_spots(child: User = Depends(get_only_child), db: DB = Depends(get_db)):
    return {"weak_spots": _compute_weak_spots(db, child.id)}


@router.post("/weak-spot-quest")
def weak_spot_quest(child: User = Depends(get_only_child), db: DB = Depends(get_db)):
    """Generates a focused remedial session on the weakest topic. Bypasses
    the 'daily must be complete' gate — these are therapeutic, not bonus."""
    from routers.parent import _materialise_questions

    weak = _compute_weak_spots(db, child.id)
    if not weak:
        raise HTTPException(400, "Nothing flagged as weak — keep playing to build the signal.")
    target = weak[0]

    today = date.today()
    dl = db.query(DailyLimit).filter_by(child_id=child.id, date=today).first()
    used = dl.questions_completed if dl else 0
    cap = dl.cap if dl else DEFAULT_DAILY_CAP
    questions_count = 10  # shorter than a daily — gives a small confidence win
    if used + questions_count > cap:
        raise HTTPException(429, "You've smashed today's question limit — come back tomorrow!")

    # Drop one difficulty tier to give them a warm-up if they've been struggling
    softer = {"olympiad": "challenge", "challenge": "starter", "starter": "starter"}.get(target["difficulty"], "starter")

    sess = DBSession(
        child_id=child.id, subject=target["subject"], difficulty=softer,
        session_type="weak_spot", status="pending", topic=target["topic"],
        questions_count=questions_count, source="weak_spot",
    )
    db.add(sess); db.commit(); db.refresh(sess)
    _materialise_questions(db, sess, child.id, learn_mode=False)
    db.commit()  # persist the Question rows
    return {
        "session_id": sess.id, "topic": target["topic"],
        "difficulty": softer, "reason": target["reason"],
    }


# ── Child-initiated belt exam start ────────────────────────────
@router.post("/belt-exam/start")
def start_belt_exam(child: User = Depends(get_only_child), db: DB = Depends(get_db)):
    """Child kicks off their belt exam — no parent gate. The exam has only
    unlocked if they already met every checklist item, so there's no friction
    benefit to making the parent click an approval button."""
    bp = db.query(BeltProgress).filter_by(child_id=child.id).first()
    if not bp or bp.exam_unlocked_belt is None:
        raise HTTPException(400, "No belt exam currently unlocked")
    # If a pending belt_exam session for this child already exists, return it
    existing = (
        db.query(DBSession)
        .filter_by(child_id=child.id, session_type="belt_exam", status="pending")
        .order_by(DBSession.id.desc())
        .first()
    )
    if existing:
        return {"session_id": existing.id, "belt": bp.exam_unlocked_belt}

    sess = DBSession(
        child_id=child.id, subject="mixed",
        difficulty="exam", session_type="belt_exam", status="pending",
        questions_count=0, source="ai_generated",
        time_limit_seconds={1: 1200, 2: 1500, 3: 1800, 4: 2100, 5: 2400}.get(bp.exam_unlocked_belt, 1200),
        assigned_by=child.parent_id,
    )
    db.add(sess); db.commit(); db.refresh(sess)
    from routers.parent import _materialise_questions
    _materialise_questions(db, sess, child.id, learn_mode=False)
    db.commit()  # persist the Question rows
    return {"session_id": sess.id, "belt": bp.exam_unlocked_belt}


# ── Review wrong answers ───────────────────────────────────────
@router.get("/session/{session_id}/review")
def review_session(session_id: int, child: User = Depends(get_only_child), db: DB = Depends(get_db)):
    """Returns every question this child got wrong (or skipped) in the session,
    with the option they picked, the correct option, and the explanation."""
    sess = db.get(DBSession, session_id)
    if not sess or sess.child_id != child.id:
        raise HTTPException(404, "Session not found")
    wrong = []
    for q in db.query(Question).filter_by(session_id=sess.id).order_by(Question.position).all():
        if q.is_worked_example:
            continue
        a = db.query(Answer).filter_by(question_id=q.id, child_id=child.id).first()
        if a and a.is_correct:
            continue
        wrong.append({
            "question_id": q.id,
            "question_text": q.question_text,
            "svg_content": q.svg_content,
            "image_bank_id": q.image_bank_id,
            "options": q.options,
            "picked_index": a.selected_index if a else None,
            "correct_index": q.correct_index,
            "explanation": q.explanation,
            "topic": q.topic,
        })
    return {"wrong": wrong, "session_subject": sess.subject, "session_topic": sess.topic}


# ── Settings ───────────────────────────────────────────────────
@router.post("/sound-toggle")
def sound_toggle(child: User = Depends(get_only_child), db: DB = Depends(get_db)):
    prog = db.query(Progress).filter_by(child_id=child.id).first()
    prog.sound_enabled = not prog.sound_enabled
    db.commit()
    return {"sound_enabled": prog.sound_enabled}


@router.get("/hint/{question_id}")
def hint(question_id: int, child: User = Depends(get_only_child), db: DB = Depends(get_db)):
    """Generate a thinking-direction hint without revealing the answer."""
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
