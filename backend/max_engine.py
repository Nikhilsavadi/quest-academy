"""Max — the fictional rival. Daily XP cycle + surge + catch-up + speech."""
import random
from datetime import date, timedelta
from sqlalchemy.orm import Session

from models import MaxRival, Progress, Answer


WEEK_RATES = {1: 60, 2: 30, 3: 45, 4: 15}
SURGE_RATE = 90


def _week_of_cycle(cycle_day: int) -> int:
    if cycle_day <= 7: return 1
    if cycle_day <= 14: return 2
    if cycle_day <= 21: return 3
    return 4


def _difficulty_mult(difficulty: str) -> float:
    return {"friendly": 0.8, "standard": 1.0, "competitive": 1.2}.get(difficulty, 1.0)


def tick_daily(db: Session) -> None:
    """Advance Max one day. Called by daily_scheduler at midnight."""
    mr = db.query(MaxRival).first()
    if not mr:
        return
    today = date.today()
    if mr.last_tick_date == today:
        return  # already ticked

    # Pull child XP for gap-based logic
    prog = db.query(Progress).first()
    child_xp = prog.total_xp if prog else 0

    base = SURGE_RATE if mr.surge_active else WEEK_RATES[_week_of_cycle(mr.cycle_day)]
    base = int(base * _difficulty_mult(mr.base_difficulty))

    # Catch-up protection (silent): if child >500 XP behind, halve Max rate until <200
    gap = mr.current_xp - child_xp
    if gap > 500:
        base = base // 2
    elif gap > 200 and base > 10:
        pass  # normal rate

    mr.current_xp += base
    mr.daily_rate = base

    # Track days child ahead
    if child_xp > mr.current_xp:
        mr.days_child_ahead += 1
    else:
        mr.days_child_ahead = 0

    # Comeback surge trigger
    if mr.days_child_ahead >= 7 and not mr.surge_active:
        mr.surge_active = True
        mr.surge_days_remaining = 3

    if mr.surge_active:
        mr.surge_days_remaining -= 1
        if mr.surge_days_remaining <= 0:
            mr.surge_active = False

    # Advance cycle
    mr.cycle_day += 1
    if mr.cycle_day > 28:
        mr.cycle_day = 1

    # Record history
    hist = (mr.xp_history or [])[-29:]
    hist.append({"date": today.isoformat(), "child": child_xp, "max": mr.current_xp})
    mr.xp_history = hist
    mr.last_tick_date = today
    db.commit()


def get_state(db: Session) -> dict:
    mr = db.query(MaxRival).first()
    prog = db.query(Progress).first()
    child_xp = prog.total_xp if prog else 0
    if not mr:
        return {"max_xp": 0, "child_xp": child_xp, "gap": -child_xp, "child_ahead": True, "trend": "neutral"}

    gap = mr.current_xp - child_xp
    hist = mr.xp_history or []
    trend = "neutral"
    if len(hist) >= 4:
        recent_gap = hist[-1]["max"] - hist[-1]["child"]
        older_gap = hist[-4]["max"] - hist[-4]["child"]
        if recent_gap < older_gap:
            trend = "closing"
        elif recent_gap > older_gap:
            trend = "widening"

    return {
        "max_xp": mr.current_xp,
        "child_xp": child_xp,
        "gap": gap,
        "child_ahead": gap < 0,
        "trend": trend,
        "surge_active": mr.surge_active,
        "cycle_day": mr.cycle_day,
        "daily_rate": mr.daily_rate,
        "base_difficulty": mr.base_difficulty,
        "history": hist,
        "lead_or_deficit": abs(gap),
    }


# ── Speech bubbles ──────────────────────────────────────────────
def pick_speech(db: Session, *, context: str = "session", difficulty: str = "starter", just_answered_olympiad_correct: bool = False) -> str | None:
    """Return at most 1 speech bubble for this session. Returns None to suppress."""
    mr = db.query(MaxRival).first()
    prog = db.query(Progress).first()
    if not mr or not prog:
        return None

    state = get_state(db)
    gap = state["gap"]
    surge = state["surge_active"]

    pool: list[str] = []
    if state["child_ahead"]:
        pool.append("Enjoy it while it lasts... 😤")
        if prog.streak_days >= 14:
            pool.append("Okay, I respect the dedication. 😅")
    else:
        pool.append("I've still got the lead. 😎")
        if surge:
            pool.append("I've been training extra hard this week.")
    if just_answered_olympiad_correct and difficulty == "olympiad":
        pool.append("Max got this wrong 😅")
    if context == "logout":
        pool.append("See you tomorrow... if you show up.")

    return random.choice(pool) if pool else None
