"""
NexCall AI — Couche base de donnees
Le moteur est cree dans une fonction pour eviter les crashes
quand le dossier data/ n'existe pas encore au moment de l'import.
"""
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings, BASE_DIR

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def _build_engine() -> AsyncEngine:
    """Construit le moteur en s'assurant que le dossier SQLite existe."""
    url = settings.DATABASE_URL

    if "sqlite" in url:
        # Extraire le chemin fichier depuis sqlite+aiosqlite:///path/to/db
        path_part = url.split("///")[-1]
        if path_part and path_part != ":memory:":
            db_path = Path(path_part)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"SQLite: {db_path}")

    return create_async_engine(
        url,
        echo=settings.DEBUG,
        future=True,
    )


# ── Moteur et session factory ─────────────────────────────────────
engine: AsyncEngine = _build_engine()

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """Dependance FastAPI: session avec commit/rollback automatique."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Cree toutes les tables manquantes."""
    from app.models import call, lead, campaign, configuration  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Base de donnees initialisee")
