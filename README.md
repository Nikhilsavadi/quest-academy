# Quest Academy

A UK 11+ exam prep platform for **Samihan**, targeting Ripon Grammar School entry.
Built around streak-based daily quests, a Grade Belt system, a fictional rival (Max),
Tables Trainer, and a Bond-book vision scanner powered by Claude.

---

## Tech

- **Frontend**: React + Vite + Tailwind CSS
- **Backend**: FastAPI + SQLAlchemy + Alembic
- **DB**: PostgreSQL (Railway managed)
- **AI**: Anthropic `claude-sonnet-4-6` (questions + workbook vision)
- **Auth**: JWT for parent dashboard; child uses shared-device mode (no login)
- **Sounds**: Web Audio API (no audio files)
- **Hosting**: Railway (2 services + 1 Postgres + 1 volume)

---

## Local development

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # edit ANTHROPIC_API_KEY if you have one

# Generate the 80 NVR matrix PNGs (commit the output to git)
python scripts/generate_matrix_bank.py

# Start Postgres any way you like; point DATABASE_URL at it.
# Then:
uvicorn main:app --reload --port 8000
# (Migrations + seed run automatically on startup via the lifespan hook.)

# 2. Frontend
cd ../frontend
cp .env.example .env
npm install
npm run dev   # http://localhost:5173
```

Visit `http://localhost:5173` for the child view.
Visit `http://localhost:5173/parent/login` for the parent dashboard:

- Email: `parent@quest-academy.app`
- Password: `changeme123`

---

## Railway deployment

1. Run `python backend/scripts/generate_matrix_bank.py` locally and commit the 80 PNGs + manifest.json. Static assets, not generated at runtime.
2. Create a new Railway project.
3. Add the **PostgreSQL** plugin. Railway sets `DATABASE_URL` automatically.
4. Create the **backend** service from `/backend`. Variables:
   - `ANTHROPIC_API_KEY` — your real key
   - `JWT_SECRET` — strong random string (the default `1123` is fine for a private family install but rotate before any public exposure)
   - `FRONTEND_URL` — the frontend Railway URL (after step 5)
   - `BACKEND_URL` — the backend Railway URL
5. Create the **frontend** service from `/frontend`. Variables:
   - `VITE_API_URL` — the backend Railway URL (build-arg; Railway injects it at build time)
6. Add a **volume** to the backend at `/app/static` so matrices + scans persist across deploys.
7. Backend auto-runs Alembic migrations and seeds the database on first start.
8. Open the frontend URL → log into the parent dashboard with the credentials above and (a) change the password, (b) rotate the JWT secret if you didn't already, (c) start scanning Bond pages once you've earned Bronze Belt.

---

## What's implemented vs stubbed

### Implemented
- Child home + Quest flow with combo, hints, learn mode, worked examples
- All 5 belts with full gate evaluation + exam scheduling toggle
- Daily quest scheduler (deterministic by weekday)
- Max rival with 28-day cycle, surge mechanics, catch-up protection
- Bond Scanner (vision API + template storage + generation)
- Tables Trainer (Blitz / Target / Fix It) with MCQ/typed alternation
- Mastery heatmap + progression suggestions (approve/dismiss)
- Badges, level-up, streak, rest days, notifications
- Web Audio sounds (opt-in; off by default)

### Minimally stubbed (per the v1 scope decision)
- **Speed Round** — session type wired, no dedicated UI yet
- **Weak Spot Drills** — session type wired, no dedicated UI yet
- **Mock Exam Mode** — session type wired
- **Exam Simulator** — session type wired
- **RGS Readiness Score** — no formula yet; placeholder for future Platinum unlock

---

## Architecture notes

- **Child auth**: shared device. App lands on `/` (child home) with no login. Parent dashboard at `/parent/login` requires JWT. Child endpoints (`/api/child/*`, `/api/tables/*`) do not require auth and operate on the seeded child user.
- **AI offline fallback**: if `ANTHROPIC_API_KEY` is missing or a placeholder, all generation paths return a deterministic offline stub of 10 sample questions so the app stays usable.
- **Streak preservation**: `longest_streak >= N` is what gate conditions check, so missing a day doesn't permanently lock progress.
- **25-question daily cap**: applies to `daily` + `bonus` sessions only. Belt exams and Tables Trainer are exempt.
- **Matrix bank**: 80 PNGs + `manifest.json` are committed to `/backend/static/matrices/`. The AI references them by `id` (e.g. `matrix_037`) and the frontend serves them via `/api/static/matrices/{id}.png`.

---

## File map

```
backend/
├── main.py                  FastAPI app + lifespan
├── config.py                pydantic-settings env loader
├── database.py              SQLAlchemy engine + session
├── models.py                All tables
├── schemas.py               Pydantic request/response models
├── auth.py                  JWT + bcrypt
├── seed.py                  Idempotent seed routine
├── ai.py                    Anthropic client (questions + vision)
├── mastery_context.py       Topic taxonomy + per-child mastery string
├── progression_engine.py    Difficulty promotion/demotion suggestions
├── gate_engine.py           Belt gate evaluation
├── badge_engine.py          Badge awarder
├── max_engine.py            Rival cycle, surge, catch-up
├── daily_scheduler.py       Midnight job + risk notifications
├── routers/
│   ├── auth.py              Login
│   ├── child.py             Home, quest, answer, complete, hint, sound
│   ├── parent.py            Dashboard, mastery, belt, suggestions, Max
│   ├── tables.py            Blitz/Target/Fix-It logging + heatmap
│   └── templates.py         Bond Scanner upload + assignment
├── static/
│   ├── matrices/            80 NVR PNGs + manifest.json
│   └── scans/               Parent-uploaded workbook thumbnails
├── scripts/
│   └── generate_matrix_bank.py
└── alembic/
    ├── env.py
    └── versions/0001_initial.py

frontend/
├── src/
│   ├── main.jsx             Bootstrap + router
│   ├── App.jsx              Routes
│   ├── api.js               axios + endpoints
│   ├── auth.js              localStorage token
│   ├── sounds.js            Web Audio tones
│   ├── pages/               Login, ChildHome, Quest, ParentDashboard
│   └── components/          17 UI components + Confetti helper
├── index.html
├── tailwind.config.js
├── vite.config.js
└── nginx.conf
```

---

## Default credentials & secrets

| What | Value | Notes |
|------|-------|-------|
| Parent email | `parent@quest-academy.app` | seed |
| Parent password | `changeme123` | **change after first login** |
| JWT secret | `1123` | **rotate before public exposure** |
| Anthropic key | placeholder | required for live AI; without it, offline stubs are used |
