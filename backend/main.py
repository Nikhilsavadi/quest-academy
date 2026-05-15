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
    # Run Alembic migrations
    try:
        from alembic.config import Config
        from alembic import command
        cfg = Config(str(Path(__file__).parent / "alembic.ini"))
        cfg.set_main_option("script_location", str(Path(__file__).parent / "alembic"))
        cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
        command.upgrade(cfg, "head")
        log.info("Alembic migrations applied")
    except Exception:
        log.exception("Alembic migrations failed (continuing — assuming DB already initialised)")

    # Seed
    try:
        from seed import seed
        seed()
    except Exception:
        log.exception("Seed failed")

    # Scheduler
    try:
        from daily_scheduler import start_scheduler
        start_scheduler(app)
        log.info("Scheduler started")
    except Exception:
        log.exception("Scheduler failed to start")

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
# Allow Railway subdomains (best-effort wildcard via regex)
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

# Static — matrices + scans
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "matrices").mkdir(exist_ok=True)
(STATIC_DIR / "scans").mkdir(exist_ok=True)
app.mount("/api/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/api/health")
def health():
    return {"status": "ok"}
