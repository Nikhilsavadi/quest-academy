"""The rival engine. Originally single-rival (Max); now drives a small league
of named characters (Max + Aisha + Tom) so Samihan has a real leaderboard to
chase.

Public surface used elsewhere:
- tick_daily(db): advance every rival one day (called by midnight cron)
- get_state(db): returns the league state + Samihan's position + a "what to
  do" action hint. Back-compat fields for the legacy Max-only widget kept.
- pick_speech(db, ...): rival speech-bubble picker (unchanged for Max)
"""
import random
from datetime import date
from sqlalchemy.orm import Session

from models import MaxRival, Progress, User


# Max's 28-day cycle (legacy)
WEEK_RATES = {1: 60, 2: 30, 3: 45, 4: 15}
SURGE_RATE = 90


def _week_of_cycle(cycle_day: int) -> int:
    if cycle_day <= 7: return 1
    if cycle_day <= 14: return 2
    if cycle_day <= 21: return 3
    return 4


def _difficulty_mult(difficulty: str) -> float:
    return {"friendly": 0.8, "standard": 1.0, "competitive": 1.2}.get(difficulty, 1.0)


def _base_rate_for(mr: MaxRival) -> int:
    """Personality drives how a rival gains XP day to day."""
    if mr.personality == "balanced":
        # Max — surge mechanic + 28-day cycle
        return SURGE_RATE if mr.surge_active else WEEK_RATES[_week_of_cycle(mr.cycle_day)]
    if mr.personality == "mathlete":
        # Aisha — steady, low variance grinder
        return 45 + random.randint(0, 10)
    if mr.personality == "strategist":
        # Tom — bursty. ~30% of days are 'sprint days'
        return 85 if random.random() < 0.30 else 25
    return 45  # fallback


def tick_daily(db: Session) -> None:
    """Advance every rival one day. Idempotent: skips rivals already ticked today."""
    rivals = db.query(MaxRival).all()
    if not rivals:
        return
    prog = db.query(Progress).first()
    child_xp = prog.total_xp if prog else 0
    today = date.today()

    for mr in rivals:
        if mr.last_tick_date == today:
            continue

        base = int(_base_rate_for(mr) * _difficulty_mult(mr.base_difficulty))

        # Per-rival catch-up: if rival is >500 XP ahead of child, halve rate
        # (silent — lets Samihan claw back without it feeling rigged).
        if mr.current_xp - child_xp > 500:
            base = base // 2

        mr.current_xp += base
        mr.daily_rate = base

        # Days-child-ahead bookkeeping (kept per-rival)
        if child_xp > mr.current_xp:
            mr.days_child_ahead += 1
        else:
            mr.days_child_ahead = 0

        # Comeback surge — only Max has this (others have their own variance built in)
        if mr.personality == "balanced":
            if mr.days_child_ahead >= 7 and not mr.surge_active:
                mr.surge_active = True
                mr.surge_days_remaining = 3
            if mr.surge_active:
                mr.surge_days_remaining -= 1
                if mr.surge_days_remaining <= 0:
                    mr.surge_active = False
            mr.cycle_day = (mr.cycle_day % 28) + 1

        hist = (mr.xp_history or [])[-29:]
        hist.append({"date": today.isoformat(), "child": child_xp, "max": mr.current_xp})
        mr.xp_history = hist
        mr.last_tick_date = today

    db.commit()


def _personality_why(rival: dict) -> str:
    if rival.get("surge_active"):
        return f"{rival['name']} is training extra hard this week — close the gap before it grows."
    p = rival.get("personality")
    if p == "sibling":
        return f"It's {rival['name']} — every quest you do is XP they don't get. Stack a few in a row."
    if p == "mathlete":
        return f"{rival['name']} grinds ~50 XP every day. Consistency beats them — keep your streak alive."
    if p == "strategist":
        return f"{rival['name']} has burst days and slow days. When they're slow, sprint to overtake."
    if p == "balanced":
        return f"{rival['name']} runs a 4-week training cycle. Catch them during a slow week."
    return f"{rival['name']} is steady today — your daily quest plus a bonus should catch them."


def _action_hint(child_xp: int, leaderboard: list[dict]) -> dict:
    """leaderboard is rank-sorted (desc XP) and includes child + all rivals."""
    child_row = next((r for r in leaderboard if r["is_child"]), None)
    if not child_row:
        return {"headline": "Keep playing!", "action": "Do a quest to climb the league.", "why": ""}
    rank = child_row["rank"]
    if rank == 1:
        return {
            "headline": "🏆 You're #1!",
            "action": "Defend your lead — do another quest to extend it.",
            "why": "Combos × streaks compound fast. Stack XP while you're ahead.",
        }
    ahead = leaderboard[rank - 2]  # row immediately above child
    gap = ahead["xp"] - child_xp
    # Rough XP-per-quest estimate at base difficulty: ~50–80 XP per 10-question round.
    quests_needed = max(1, (gap + 49) // 50)
    return {
        "headline": f"🎯 Beat {ahead['name']}",
        "action": (
            f"Do 1 more quest (~{gap + 10} XP needed)"
            if quests_needed == 1
            else f"Do {quests_needed} more quests (~{gap + 20} XP needed)"
        ),
        "why": _personality_why(ahead),
    }


def get_state(db: Session, child_id: int | None = None) -> dict:
    """Returns the full league + this child's position + an action hint.

    The league now includes any *sibling* child as a real rival alongside
    Max/Aisha/Tom — sibling competition is more motivating than fictional
    avatars. Sibling rows are flagged is_sibling=True so the frontend can
    visually distinguish them. Legacy Max-only fields kept populated for the
    old RivalWidget."""
    rivals = db.query(MaxRival).order_by(MaxRival.id).all()
    # Resolve the requesting child + Progress
    if child_id is None:
        # Legacy call with no child — fall back to first child (parent dashboards)
        prog = db.query(Progress).order_by(Progress.id).first()
        child_id = prog.child_id if prog else None
    else:
        prog = db.query(Progress).filter_by(child_id=child_id).first()
    child_xp = prog.total_xp if prog else 0

    rows = [{
        "name": "You",
        "avatar": "🧑",
        "xp": child_xp,
        "is_child": True,
        "is_sibling": False,
        "personality": None,
        "daily_rate": None,
        "surge_active": False,
    }]

    # Siblings — other child users
    if child_id is not None:
        sibling_users = db.query(User).filter(User.role == "child", User.id != child_id).all()
        for sib in sibling_users:
            sp = db.query(Progress).filter_by(child_id=sib.id).first()
            rows.append({
                "name": sib.name,
                "avatar": "🧒",
                "xp": sp.total_xp if sp else 0,
                "is_child": False,
                "is_sibling": True,
                "personality": "sibling",
                "daily_rate": None,
                "surge_active": False,
            })

    for mr in rivals:
        rows.append({
            "name": mr.name,
            "avatar": mr.avatar,
            "xp": mr.current_xp,
            "is_child": False,
            "is_sibling": False,
            "personality": mr.personality,
            "daily_rate": mr.daily_rate,
            "surge_active": mr.surge_active,
        })
    rows.sort(key=lambda r: r["xp"], reverse=True)
    for i, r in enumerate(rows, start=1):
        r["rank"] = i

    action_hint = _action_hint(child_xp, rows)

    # Legacy Max-only block for back-compat with existing RivalWidget.
    max_row = next((mr for mr in rivals if mr.name == "Max"), None)
    if max_row is None:
        return {
            "leaderboard": rows,
            "child_position": next(r["rank"] for r in rows if r["is_child"]),
            "action_hint": action_hint,
            "max_xp": 0, "child_xp": child_xp, "gap": -child_xp,
            "child_ahead": True, "trend": "neutral", "lead_or_deficit": child_xp,
        }

    gap = max_row.current_xp - child_xp
    hist = max_row.xp_history or []
    trend = "neutral"
    if len(hist) >= 4:
        recent_gap = hist[-1]["max"] - hist[-1]["child"]
        older_gap = hist[-4]["max"] - hist[-4]["child"]
        if recent_gap < older_gap:
            trend = "closing"
        elif recent_gap > older_gap:
            trend = "widening"

    return {
        # New multi-rival fields:
        "leaderboard": rows,
        "child_position": next(r["rank"] for r in rows if r["is_child"]),
        "action_hint": action_hint,
        # Legacy Max-only fields (existing UI continues to render):
        "max_xp": max_row.current_xp,
        "child_xp": child_xp,
        "gap": gap,
        "child_ahead": gap < 0,
        "trend": trend,
        "surge_active": max_row.surge_active,
        "cycle_day": max_row.cycle_day,
        "daily_rate": max_row.daily_rate,
        "base_difficulty": max_row.base_difficulty,
        "history": hist,
        "lead_or_deficit": abs(gap),
    }


# ── Speech bubbles ──────────────────────────────────────────────
def pick_speech(db: Session, *, context: str = "session", difficulty: str = "starter",
                just_answered_olympiad_correct: bool = False) -> str | None:
    """Max's speech bubble (legacy single-rival behavior; unchanged)."""
    mr = db.query(MaxRival).filter_by(name="Max").first()
    prog = db.query(Progress).first()
    if not mr or not prog:
        return None

    state = get_state(db)
    surge = state.get("surge_active", False)

    pool: list[str] = []
    if state.get("child_ahead"):
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
