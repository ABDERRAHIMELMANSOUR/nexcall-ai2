"""
Base de données async — SQLAlchemy 2.x + aiosqlite
"""
from __future__ import annotations
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Chemin absolu DB (compatible Render/Gunicorn)
_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_DB_PATH  = _BASE_DIR / "data" / "nexcall.db"
_DB_PATH.parent.mkdir(exist_ok=True)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{_DB_PATH}"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
