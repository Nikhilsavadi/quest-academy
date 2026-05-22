import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from routers import auth as auth_router
from routers import child as child_router
from routers import parent as parent_router
from routers import tables as tables_router
from routers import templates as templates_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
log = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # -- Alembic migrations (run in thread: sync psycopg must not block the event loop) --
    print("STARTUP [1/4]: running alembic migrations...", flush=True)
    try:
        def _run_migrations():
            from alembic.config import Config
            from alembic import command as alembic_cmd
            cfg = Config(str(Path(__file__).parent / "alembic.ini"))
            cfg.set_main_option("script_location", str(Path(__file__).parent / "alembic"))
            cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
            alembic_cmd.upgrade(cfg, "head")
        await asyncio.to_thread(_run_migrations)
        print("STARTUP [1/4]: alembic done", flush=True)
        log.info("Alembic migrations applied")
    except Exception:
        log.exception("Alembic migrations failed (continuing)")

    # -- Seed (run in thread: sync DB calls) --
    print("STARTUP [2/4]: running seed...", flush=True)
    try:
        from seed import seed
        await asyncio.to_thread(seed)
        print("STARTUP [2/4]: seed done", flush=True)
    except Exception:
        log.exception("Seed failed")

    # -- Scheduler --
    print("STARTUP [3/4]: starting scheduler...", flush=True)
    try:
        from daily_scheduler import start_scheduler
        start_scheduler(app)
        print("STARTUP [3/4]: scheduler started", flush=True)
        log.info("Scheduler started")
    except Exception:
        log.exception("Scheduler failed to start")

    print("STARTUP [4/4]: yielding to uvicorn", flush=True)
    yield

    sched = getattr(app.state, "scheduler", None)
    if sched:
        sched.shutdown(wait=False)


app = FastAPI(title="Quest Academy", lifespan=lifespan)

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    settings.FRONTEND_URL,
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https?://.*\.up\.railway\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(child_router.router)
app.include_router(parent_router.router)
app.include_router(tables_router.router)
app.include_router(templates_router.router)

# Static -- matrices + scans
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "matrices").mkdir(exist_ok=True)
(STATIC_DIR / "scans").mkdir(exist_ok=True)
app.mount("/api/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/api/health")
def health():
    return {"status": "ok"}
