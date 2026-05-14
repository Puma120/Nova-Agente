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
        # Lightweight migrations for DBs that predate a column. Each ALTER is
        # wrapped on its own so an "already exists" error doesn't skip the rest.
        migrations = [
            "ALTER TABLE conversations ADD COLUMN mode VARCHAR(20) NOT NULL DEFAULT 'nova'",
            "ALTER TABLE users ADD COLUMN is_onboarded BOOLEAN NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN google_sub VARCHAR(64)",
            "ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500)",
        ]
        for stmt in migrations:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass  # column already exists
