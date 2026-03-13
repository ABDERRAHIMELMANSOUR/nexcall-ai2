"""
NexCall AI v2.0 — Point d'entree principal
"""
import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# ── Chemin absolu du projet (CRITIQUE pour Gunicorn/Render) ───────
BASE_DIR = Path(__file__).resolve().parent

# ── Creer les dossiers avant tout import de config ────────────────
(BASE_DIR / "data").mkdir(exist_ok=True)
(BASE_DIR / "logs").mkdir(exist_ok=True)

from app.config import settings
from app.database import init_db
from app.routers import (
    pages_router,
    calls_router,
    leads_router,
    campaigns_router,
    config_router,
    webhooks_router,
)

# ── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("nexcall")


# ── Lifespan (startup / shutdown) ─────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 50)
    logger.info("  NexCall AI v2.0 - Demarrage")
    logger.info("=" * 50)

    # Init BDD avec protection anti-crash
    try:
        await init_db()
        logger.info("  BDD ........... OK")
    except Exception as e:
        logger.error(f"  BDD ........... ERREUR: {e}")
        # On ne crash PAS - l'app demarre quand meme

    port = os.environ.get("PORT", settings.APP_PORT)
    logger.info(f"  PORT .......... {port}")
    logger.info(f"  Ringover ...... {'OK' if settings.is_ringover_configured else 'Non configure'}")
    logger.info(f"  OpenAI ........ {'OK' if settings.is_openai_configured else 'Non configure'}")
    logger.info(f"  Agent ......... {settings.AI_AGENT_NAME} @ {settings.AI_COMPANY_NAME}")
    logger.info(f"  BASE_DIR ...... {BASE_DIR}")
    logger.info("=" * 50)

    yield

    logger.info("NexCall AI - Arret propre")


# ── Application FastAPI ───────────────────────────────────────────
app = FastAPI(
    title="NexCall AI",
    description="Centre d'appels IA - Ringover + OpenAI",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files (chemin ABSOLU - sinon crash avec Gunicorn) ──────
_static_dir = BASE_DIR / "app" / "static"
if _static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")
    logger.info(f"Static files: {_static_dir}")

# ── Routeurs ──────────────────────────────────────────────────────
app.include_router(pages_router)
app.include_router(calls_router)
app.include_router(leads_router)
app.include_router(campaigns_router)
app.include_router(config_router)
app.include_router(webhooks_router)


# ── Health Check (Render utilise cet endpoint) ────────────────────
@app.get("/health", tags=["system"])
async def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "2.0.0",
        "integrations": {
            "ringover": settings.is_ringover_configured,
            "openai": settings.is_openai_configured,
        },
    }
