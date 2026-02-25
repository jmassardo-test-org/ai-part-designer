"""Migrate test DB to add archive columns."""
import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

os.environ["TESTING"] = "true"
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-minimum-32-characters-long"

host = os.environ.get("POSTGRES_HOST", "localhost")
port = os.environ.get("POSTGRES_PORT", "5432")
user = os.environ.get("POSTGRES_USER", "postgres")
pw = os.environ.get("POSTGRES_PASSWORD", "postgres")
db = os.environ.get("POSTGRES_DB", "test_db")
url = f"postgresql+asyncpg://{user}:{pw}@{host}:{port}/{db}"


async def migrate():
    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(
            text("ALTER TABLE designs ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP WITH TIME ZONE")
        )
        await conn.execute(
            text("ALTER TABLE designs ADD COLUMN IF NOT EXISTS archive_location VARCHAR(500)")
        )
        await conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_designs_archived ON designs (archived_at) WHERE archived_at IS NOT NULL")
        )
    await engine.dispose()
    print("Done: added archived_at and archive_location columns")


asyncio.run(migrate())
