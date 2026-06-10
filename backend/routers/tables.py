"""Tables Trainer endpoints. Client-side question generation; server logs results."""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DB

from auth import require_parent, get_only_child, default_child
from database import get_db
from models import (
    TablesSession, TablesFactStats, TablesTargets, Progress, User
)
from schemas import TablesSessionIn, TablesTargetIn
import badge_engine
import gate_engine

router = APIRouter(prefix="/api/tables", tags=["tables"])


@router.post("/session/log")
def log_session(body: TablesSessionIn, child: User = Depends(get_only_child), db: DB = Depends(get_db)):
    pb_broken = False

    if body.mode == "blitz":
        tgt = db.query(TablesTargets).filter_by(child_id=child.id).first()
        if tgt and (tgt.best_blitz_seconds is None or body.duration_seconds < tgt.best_blitz_seconds):
            tgt.best_blitz_seconds = body.duration_seconds
            tgt.best_blitz_correct = body.correct
            pb_broken = True

    sess = TablesSession(
        child_id=child.id, mode=body.mode,
        total_questions=body.total_questions, correct=body.correct,
        duration_seconds=body.duration_seconds,
        personal_best_broken=pb_broken,
    )
    db.add(sess)

    # Update per-fact stats
    for f in body.facts:
        row = db.query(TablesFactStats).filter_by(
            child_id=child.id, multiplicand=f.multiplicand, multiplier=f.multiplier
        ).first()
        if not row:
            row = TablesFactStats(
                child_id=child.id, multiplicand=f.multiplicand, multiplier=f.multiplier
            )
            db.add(row); db.flush()
        old_total_ms = row.avg_response_ms * row.attempts
        row.attempts += 1
        if f.correct:
            row.correct += 1
        row.avg_response_ms = int((old_total_ms + f.response_ms) / row.attempts)
        row.last_attempted = datetime.utcnow()

    # XP per spec
    xp_map = {"blitz": 30, "target": 40, "fix_it": 50}
    xp = xp_map.get(body.mode, 30)
    if pb_broken:
        xp += 20
    prog = db.query(Progress).filter_by(child_id=child.id).first()
    if prog:
        prog.total_xp += xp

    db.commit()

    new_badges = badge_engine.evaluate(
        db, child.id, blitz_seconds=body.duration_seconds if body.mode == "blitz" else None,
    )
    gate_engine.evaluate(db, child.id)
    return {"xp": xp, "pb_broken": pb_broken, "new_badges": new_badges}


@router.get("/heatmap")
def heatmap(child: User = Depends(get_only_child), db: DB = Depends(get_db)):
    rows = db.query(TablesFactStats).filter_by(child_id=child.id).all()
    cells = []
    for r in rows:
        cells.append({
            "m": r.multiplicand, "n": r.multiplier,
            "attempts": r.attempts, "correct": r.correct,
            "avg_response_ms": r.avg_response_ms,
        })
    tgt = db.query(TablesTargets).filter_by(child_id=child.id).first()
    return {
        "cells": cells,
        "target": {
            "correct_target": tgt.correct_target if tgt else 20,
            "time_limit_seconds": tgt.time_limit_seconds if tgt else 60,
            "include_division": tgt.include_division if tgt else False,
            "best_blitz_seconds": tgt.best_blitz_seconds if tgt else None,
            "best_blitz_correct": tgt.best_blitz_correct if tgt else 0,
        },
    }


@router.post("/target", dependencies=[Depends(require_parent)])
def set_target(body: TablesTargetIn, db: DB = Depends(get_db)):
    # Parent-authed endpoint — the JWT here is the parent's, so we use
    # default_child (legacy single-child behaviour) instead of decoding a
    # child JWT.
    child = default_child(db)
    parent = db.query(User).filter_by(role="parent").first()
    tgt = db.query(TablesTargets).filter_by(child_id=child.id).first()
    if not tgt:
        tgt = TablesTargets(child_id=child.id, set_by=parent.id)
        db.add(tgt)
    tgt.correct_target = body.correct_target
    tgt.time_limit_seconds = body.time_limit_seconds
    tgt.include_division = body.include_division
    tgt.set_by = parent.id
    db.commit()
    return {"ok": True}


@router.get("/weak-facts")
def weak_facts(child: User = Depends(get_only_child), db: DB = Depends(get_db)):
    """Facts where avg_response_ms > 2× the child's overall avg (used by Fix It mode)."""
    rows = db.query(TablesFactStats).filter_by(child_id=child.id).all()
    rows = [r for r in rows if r.attempts > 0]
    if not rows:
        return {"facts": []}
    overall = sum(r.avg_response_ms for r in rows) / len(rows)
    threshold = overall * 2
    weak = [
        {"m": r.multiplicand, "n": r.multiplier, "avg_ms": r.avg_response_ms,
         "accuracy": r.correct / r.attempts if r.attempts else 0}
        for r in rows if r.avg_response_ms > threshold or (r.attempts and r.correct / r.attempts < 0.7)
    ][:12]
    return {"facts": weak}
