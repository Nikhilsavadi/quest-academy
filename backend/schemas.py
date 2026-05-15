from datetime import datetime, date
from typing import Any, Optional
from pydantic import BaseModel, EmailStr


# ── Auth ──────────────────────────────────────────────────────────
class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    role: str
    name: str


# ── Questions / Sessions ──────────────────────────────────────────
class QuestionOut(BaseModel):
    id: int
    question_text: str
    svg_content: Optional[str] = None
    image_bank_id: Optional[str] = None
    options: list[str]
    has_visual: bool
    topic: str
    is_worked_example: bool = False
    walkthrough: Optional[str] = None
    position: int

    class Config:
        from_attributes = True


class SessionOut(BaseModel):
    id: int
    subject: str
    difficulty: str
    session_type: str
    status: str
    questions_count: int
    topic: Optional[str] = None
    time_limit_seconds: Optional[int] = None
    questions: list[QuestionOut] = []

    class Config:
        from_attributes = True


class AnswerIn(BaseModel):
    question_id: int
    selected_index: int
    time_taken_ms: int = 0
    used_hint: bool = False


class AnswerResultOut(BaseModel):
    is_correct: bool
    correct_index: int
    explanation: str
    xp_awarded: int
    combo: int


class CompleteSessionOut(BaseModel):
    score: int
    total: int
    xp_breakdown: dict
    xp_total_session: int
    new_badges: list[dict]
    level_up: Optional[dict] = None
    belt_progress: dict
    streak: int
    daily_done: bool
    rival: dict


# ── Child Home ────────────────────────────────────────────────────
class ChildHomeOut(BaseModel):
    name: str
    xp: int
    level: str
    next_level: Optional[dict] = None
    streak: int
    longest_streak: int
    belt: dict
    daily_quest: Optional[dict] = None
    bonus_quests: list[dict]
    badges: list[dict]
    avatar: dict
    rival: dict
    sound_enabled: bool
    weekly_xp: int
    weekly_best_xp: int
    cap_remaining: int


# ── Parent ────────────────────────────────────────────────────────
class AssignBonusIn(BaseModel):
    subject: str
    topic: Optional[str] = None  # None = auto
    difficulty: Optional[str] = None  # None = auto (current)
    source: str = "ai_generated"  # ai_generated | template
    template_id: Optional[int] = None


class RestDayIn(BaseModel):
    date: date


class MaxControlsIn(BaseModel):
    base_difficulty: Optional[str] = None
    manual_xp: Optional[int] = None


class TablesTargetIn(BaseModel):
    correct_target: int
    time_limit_seconds: int
    include_division: bool = False


class TemplateConfirmIn(BaseModel):
    template_id: int
    source_name: str


class AssignFromTemplateIn(BaseModel):
    template_id: int
    questions_count: int = 20


# ── Tables ────────────────────────────────────────────────────────
class TablesAnswerIn(BaseModel):
    multiplicand: int
    multiplier: int
    correct: bool
    response_ms: int


class TablesSessionIn(BaseModel):
    mode: str  # blitz | target | fix_it
    total_questions: int
    correct: int
    duration_seconds: int
    facts: list[TablesAnswerIn]
