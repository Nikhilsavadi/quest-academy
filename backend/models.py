from datetime import datetime, date
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Date, ForeignKey, JSON, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20))  # parent | child
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject: Mapped[str] = mapped_column(String(20))
    difficulty: Mapped[str] = mapped_column(String(20))
    session_type: Mapped[str] = mapped_column(String(30))  # daily|bonus|belt_exam|speed_round|weak_spot|mock_exam|exam_sim
    status: Mapped[str] = mapped_column(String(20), default="pending")
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    questions_count: Mapped[int] = mapped_column(Integer, default=20)
    source: Mapped[str] = mapped_column(String(30), default="ai_generated")
    template_id: Mapped[int | None] = mapped_column(ForeignKey("problem_set_templates.id"), nullable=True)
    topic: Mapped[str | None] = mapped_column(String(80), nullable=True)
    time_limit_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    questions: Mapped[list["Question"]] = relationship(back_populates="session", cascade="all,delete")


class Question(Base):
    __tablename__ = "questions"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    question_text: Mapped[str] = mapped_column(Text)
    svg_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_bank_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    options: Mapped[list] = mapped_column(JSON)
    correct_index: Mapped[int] = mapped_column(Integer)
    explanation: Mapped[str] = mapped_column(Text)
    topic: Mapped[str] = mapped_column(String(80))
    has_visual: Mapped[bool] = mapped_column(Boolean, default=False)
    is_worked_example: Mapped[bool] = mapped_column(Boolean, default=False)
    walkthrough: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    session: Mapped[Session] = relationship(back_populates="questions")


class Answer(Base):
    __tablename__ = "answers"
    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    selected_index: Mapped[int] = mapped_column(Integer)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    answered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    time_taken_ms: Mapped[int] = mapped_column(Integer, default=0)
    used_hint: Mapped[bool] = mapped_column(Boolean, default=False)


class TopicMastery(Base):
    __tablename__ = "topic_mastery"
    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject: Mapped[str] = mapped_column(String(20))
    topic: Mapped[str] = mapped_column(String(80))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct: Mapped[int] = mapped_column(Integer, default=0)
    accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    current_difficulty: Mapped[str] = mapped_column(String(20), default="starter")
    suggested_difficulty: Mapped[str | None] = mapped_column(String(20), nullable=True)
    progression_pending: Mapped[bool] = mapped_column(Boolean, default=False)
    learn_mode_seen: Mapped[bool] = mapped_column(Boolean, default=False)
    last_attempted: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Track attempts at current_difficulty specifically for promotion gate
    attempts_at_current: Mapped[int] = mapped_column(Integer, default=0)
    correct_at_current: Mapped[int] = mapped_column(Integer, default=0)
    last5_correct: Mapped[int] = mapped_column(Integer, default=0)  # rolling window of last 5
    hint_usage_count: Mapped[int] = mapped_column(Integer, default=0)


class ProgressionSuggestion(Base):
    __tablename__ = "progression_suggestions"
    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject: Mapped[str] = mapped_column(String(20))
    topic: Mapped[str] = mapped_column(String(80))
    from_difficulty: Mapped[str] = mapped_column(String(20))
    to_difficulty: Mapped[str] = mapped_column(String(20))
    suggested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DailyQuest(Base):
    __tablename__ = "daily_quests"
    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    subject: Mapped[str] = mapped_column(String(20))
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    xp_awarded: Mapped[int] = mapped_column(Integer, default=0)


class Progress(Base):
    __tablename__ = "progress"
    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    total_xp: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[str] = mapped_column(String(40), default="Apprentice")
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
    badges: Mapped[list] = mapped_column(JSON, default=list)
    last_active: Mapped[date | None] = mapped_column(Date, nullable=True)
    rest_days_used: Mapped[int] = mapped_column(Integer, default=0)
    sound_enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class DailyLimit(Base):
    __tablename__ = "daily_limits"
    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    questions_completed: Mapped[int] = mapped_column(Integer, default=0)
    cap: Mapped[int] = mapped_column(Integer, default=60)


class BeltProgress(Base):
    __tablename__ = "belt_progress"
    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    current_belt: Mapped[int] = mapped_column(Integer, default=0)
    bronze_gate_met: Mapped[bool] = mapped_column(Boolean, default=False)
    silver_gate_met: Mapped[bool] = mapped_column(Boolean, default=False)
    gold_gate_met: Mapped[bool] = mapped_column(Boolean, default=False)
    platinum_gate_met: Mapped[bool] = mapped_column(Boolean, default=False)
    elite_gate_met: Mapped[bool] = mapped_column(Boolean, default=False)
    exam_unlocked_belt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exam_attempts: Mapped[dict] = mapped_column(JSON, default=dict)
    gate_progress: Mapped[dict] = mapped_column(JSON, default=dict)  # checklist detail


class BeltExam(Base):
    __tablename__ = "belt_exams"
    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    belt_level: Mapped[int] = mapped_column(Integer)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    score: Mapped[int] = mapped_column(Integer)
    total: Mapped[int] = mapped_column(Integer)
    passed: Mapped[bool] = mapped_column(Boolean)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    time_taken_seconds: Mapped[int] = mapped_column(Integer, default=0)


class AvatarUnlocks(Base):
    __tablename__ = "avatar_unlocks"
    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    unlocked_items: Mapped[list] = mapped_column(JSON, default=list)
    active_items: Mapped[list] = mapped_column(JSON, default=list)
    theme: Mapped[str] = mapped_column(String(40), default="default")


class TablesSession(Base):
    __tablename__ = "tables_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    mode: Mapped[str] = mapped_column(String(20))  # blitz | target | fix_it
    total_questions: Mapped[int] = mapped_column(Integer)
    correct: Mapped[int] = mapped_column(Integer)
    duration_seconds: Mapped[int] = mapped_column(Integer)
    personal_best_broken: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TablesFactStats(Base):
    __tablename__ = "tables_fact_stats"
    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    multiplicand: Mapped[int] = mapped_column(Integer)
    multiplier: Mapped[int] = mapped_column(Integer)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct: Mapped[int] = mapped_column(Integer, default=0)
    avg_response_ms: Mapped[int] = mapped_column(Integer, default=0)
    last_attempted: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TablesTargets(Base):
    __tablename__ = "tables_targets"
    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    correct_target: Mapped[int] = mapped_column(Integer, default=20)
    time_limit_seconds: Mapped[int] = mapped_column(Integer, default=60)
    set_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    include_division: Mapped[bool] = mapped_column(Boolean, default=False)
    best_blitz_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    best_blitz_correct: Mapped[int] = mapped_column(Integer, default=0)


class ProblemSetTemplate(Base):
    __tablename__ = "problem_set_templates"
    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    source_name: Mapped[str] = mapped_column(String(200))
    subject: Mapped[str] = mapped_column(String(20))
    difficulty: Mapped[str] = mapped_column(String(20))
    year_group: Mapped[str] = mapped_column(String(40))
    question_types: Mapped[list] = mapped_column(JSON)
    format_notes: Mapped[str] = mapped_column(Text)
    sample_questions: Mapped[list] = mapped_column(JSON)
    svg_patterns: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    times_used: Mapped[int] = mapped_column(Integer, default=0)


class MaxRival(Base):
    __tablename__ = "max_rival"
    id: Mapped[int] = mapped_column(primary_key=True)
    current_xp: Mapped[int] = mapped_column(Integer, default=0)
    daily_rate: Mapped[int] = mapped_column(Integer, default=45)
    cycle_day: Mapped[int] = mapped_column(Integer, default=1)
    surge_active: Mapped[bool] = mapped_column(Boolean, default=False)
    surge_days_remaining: Mapped[int] = mapped_column(Integer, default=0)
    base_difficulty: Mapped[str] = mapped_column(String(20), default="standard")
    days_child_ahead: Mapped[int] = mapped_column(Integer, default=0)
    last_tick_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    xp_history: Mapped[list] = mapped_column(JSON, default=list)  # last 30 days: [{date, child, max}]


class RestDay(Base):
    __tablename__ = "rest_days"
    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    set_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))  # belt_exam_ready | suggestion | quest_at_risk | max_gap | level_up
    message: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
