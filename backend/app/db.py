from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import settings

engine = create_async_engine(settings.database_url, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def init_db() -> None:
    from .models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Migration: add mode column to existing DBs that predate this column
        try:
            await conn.execute(
                text("ALTER TABLE conversations ADD COLUMN mode VARCHAR(20) NOT NULL DEFAULT 'nova'")
            )
        except Exception:
            pass  # column already exists
