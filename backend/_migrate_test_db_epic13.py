"""Add Epic 13 license columns to test DB (designs + content_reports)."""

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


async def migrate() -> None:
    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.begin() as conn:
        # Epic 13: design license columns
        await conn.execute(
            text("ALTER TABLE designs ADD COLUMN IF NOT EXISTS license_type VARCHAR(30)")
        )
        await conn.execute(
            text("ALTER TABLE designs ADD COLUMN IF NOT EXISTS custom_license_text TEXT")
        )
        await conn.execute(
            text(
                "ALTER TABLE designs ADD COLUMN IF NOT EXISTS custom_allows_remix BOOLEAN DEFAULT FALSE"
            )
        )
        # Epic 13: content_reports evidence_url
        await conn.execute(
            text(
                "ALTER TABLE content_reports ADD COLUMN IF NOT EXISTS evidence_url VARCHAR(2048)"
            )
        )
    await engine.dispose()
    print("Done: added license columns to designs and evidence_url to content_reports")


asyncio.run(migrate())
