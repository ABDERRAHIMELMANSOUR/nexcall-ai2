"""
NexCall AI v2.0 — Point d'entrée principal
FastAPI + Gunicorn/UvicornWorker — compatible Render
"""
import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# ── Chemin absolu (CRITIQUE pour Gunicorn/Render) ────────────────
BASE_DIR = Path(__file__).resolve().parent
(BASE_DIR / "data").mkdir(exist_ok=True)
(BASE_DIR / "logs").mkdir(exist_ok=True)

# ── Config & DB ───────────────────────────────────────────────────
from app.config import settings
from app.models.database import init_db
from app.routers import (
    pages_router, calls_router, leads_router,
    campaigns_router, config_router, webhooks_router, ivr_router,
)

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("nexcall")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 52)
    logger.info("  NexCall AI v2.0 — Démarrage")
    logger.info("=" * 52)
    try:
        await init_db()
        logger.info("  BDD .............. OK")
    except Exception as e:
        logger.error(f"  BDD .............. ERREUR: {e}")

    logger.info(f"  Ringover ......... {'✓ OK' if settings.is_ringover_configured else '⚠ Non configuré'}")
    logger.info(f"  OpenAI ........... {'✓ OK' if settings.is_openai_configured else '⚠ Non configuré'}")
    logger.info(f"  Agent ............ {settings.AI_AGENT_NAME} @ {settings.AI_COMPANY_NAME}")
    logger.info(f"  BASE_DIR ......... {BASE_DIR}")
    logger.info("=" * 52)
    yield
    logger.info("NexCall AI — Arrêt propre")


app = FastAPI(
    title="NexCall AI",
    description="Centre d'appels IA — Ringover + OpenAI",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files (chemin absolu — sinon crash avec Gunicorn)
_static = BASE_DIR / "app" / "static"
if _static.is_dir():
    app.mount("/static", StaticFiles(directory=str(_static)), name="static")

# Routers
app.include_router(pages_router)
app.include_router(calls_router)
app.include_router(leads_router)
app.include_router(campaigns_router)
app.include_router(config_router)
app.include_router(webhooks_router)
app.include_router(ivr_router)


@app.get("/health", tags=["system"])
async def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "2.0.0",
        "integrations": {
            "ringover": settings.is_ringover_configured,
            "openai":   settings.is_openai_configured,
        },
    }
