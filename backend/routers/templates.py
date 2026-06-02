"""Bond Book Scanner: upload → vision → store template → generate from template."""
import io
import os
from datetime import date
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from PIL import Image
from sqlalchemy.orm import Session as DB

from auth import require_parent, default_child
from database import get_db
from models import (
    ProblemSetTemplate, Session as DBSession, BeltProgress, DailyQuest,
    DailyLimit, User,
)
from schemas import TemplateConfirmIn, AssignFromTemplateIn
import ai

router = APIRouter(prefix="/api/parent", tags=["templates"], dependencies=[Depends(require_parent)])

SCANS_DIR = Path(__file__).parent.parent / "static" / "scans"
SCANS_DIR.mkdir(parents=True, exist_ok=True)



def _require_bronze(db: DB, child_id: int):
    bp = db.query(BeltProgress).filter_by(child_id=child_id).first()
    if not bp or bp.current_belt < 1:
        raise HTTPException(403, "Bond Scanner unlocks at Bronze Belt")


@router.post("/scan-template")
async def scan_template(file: UploadFile = File(...), db: DB = Depends(get_db)):
    child = default_child(db)
    _require_bronze(db, child.id)

    if file.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(400, "Only JPEG or PNG")
    raw = await file.read()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(400, "Max 10MB")

    # Compress to max 1600px longest edge
    try:
        img = Image.open(io.BytesIO(raw))
        img = img.convert("RGB")
        w, h = img.size
        longest = max(w, h)
        if longest > 1600:
            scale = 1600 / longest
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=82)
        compressed = buf.getvalue()
    except Exception as e:
        raise HTTPException(400, f"Could not read image: {e}")

    try:
        result = ai.scan_workbook_image(compressed, media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(500, f"Vision failed: {e}")

    parent = db.query(User).filter_by(role="parent").first()
    tpl = ProblemSetTemplate(
        parent_id=parent.id,
        source_name=f"Scan {date.today().isoformat()}",
        subject=result.get("subject", "Maths"),
        difficulty=result.get("difficulty", "challenge"),
        year_group=result.get("year_group", "Age 8-10"),
        question_types=result.get("question_types", []),
        format_notes=result.get("format_notes", ""),
        sample_questions=result.get("sample_questions", []),
        svg_patterns=result.get("visual_patterns"),
    )
    db.add(tpl); db.commit(); db.refresh(tpl)

    thumb_path = SCANS_DIR / f"{tpl.id}.jpg"
    thumb_path.write_bytes(compressed)
    tpl.thumbnail_path = f"/api/static/scans/{tpl.id}.jpg"
    db.commit()

    return {"template": _serialise(tpl), "analysis": result}


@router.post("/template/confirm")
def confirm_template(body: TemplateConfirmIn, db: DB = Depends(get_db)):
    tpl = db.get(ProblemSetTemplate, body.template_id)
    if not tpl:
        raise HTTPException(404, "Not found")
    tpl.source_name = body.source_name
    db.commit()
    return {"template": _serialise(tpl)}


@router.get("/templates")
def list_templates(db: DB = Depends(get_db)):
    rows = db.query(ProblemSetTemplate).order_by(ProblemSetTemplate.created_at.desc()).all()
    return {"templates": [_serialise(t) for t in rows]}


@router.delete("/template/{tid}")
def delete_template(tid: int, db: DB = Depends(get_db)):
    tpl = db.get(ProblemSetTemplate, tid)
    if not tpl:
        raise HTTPException(404, "Not found")
    db.delete(tpl)
    db.commit()
    if tpl.thumbnail_path:
        try:
            os.remove(SCANS_DIR / f"{tid}.jpg")
        except OSError:
            pass
    return {"ok": True}


@router.post("/assign-from-template")
def assign_from_template(body: AssignFromTemplateIn, db: DB = Depends(get_db)):
    child = default_child(db)
    _require_bronze(db, child.id)
    tpl = db.get(ProblemSetTemplate, body.template_id)
    if not tpl:
        raise HTTPException(404, "Template not found")
    today = date.today()
    daily = db.query(DailyQuest).filter_by(child_id=child.id, date=today).first()
    if daily and daily.status != "completed":
        raise HTTPException(400, "Daily quest must be done first")
    dl = db.query(DailyLimit).filter_by(child_id=child.id, date=today).first()
    used = dl.questions_completed if dl else 0
    from routers.child import DEFAULT_DAILY_CAP
    if used + body.questions_count > DEFAULT_DAILY_CAP:
        raise HTTPException(400, f"Daily {DEFAULT_DAILY_CAP}-question cap would be exceeded")

    sess = DBSession(
        child_id=child.id, subject=tpl.subject, difficulty=tpl.difficulty,
        session_type="bonus", status="pending",
        topic=tpl.question_types[0] if tpl.question_types else "General",
        questions_count=body.questions_count, source="template",
        template_id=tpl.id, assigned_by=child.parent_id,
    )
    db.add(sess); db.commit(); db.refresh(sess)

    # Materialise via the same path the parent router uses
    from routers.parent import _materialise_questions
    _materialise_questions(db, sess, child.id, learn_mode=False)
    return {"session_id": sess.id}


def _serialise(t: ProblemSetTemplate) -> dict:
    return {
        "id": t.id, "source_name": t.source_name, "subject": t.subject,
        "difficulty": t.difficulty, "year_group": t.year_group,
        "question_types": t.question_types, "format_notes": t.format_notes,
        "sample_questions": t.sample_questions,
        "visual_patterns": t.svg_patterns, "thumbnail_path": t.thumbnail_path,
        "times_used": t.times_used,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }
