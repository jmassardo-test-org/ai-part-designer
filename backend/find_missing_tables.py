#!/usr/bin/env python
"""Find missing database tables and generate migration."""

import asyncio
import inspect

from sqlalchemy import text

from app.core.database import engine
from app.models import *  # noqa: F403 - intentional star import to discover all models


async def main():
    # Get all table names from models
    model_tables = set()
    for _name, obj in list(globals().items()):
        if inspect.isclass(obj) and hasattr(obj, '__tablename__'):
            model_tables.add(obj.__tablename__)

    # Get existing tables from DB
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
        db_tables = {row[0] for row in result.fetchall()}

    missing = model_tables - db_tables

    print("=" * 60)
    print("MISSING TABLES (in models but not in database):")
    print("=" * 60)
    for t in sorted(missing):
        print(f"  - {t}")

    print()
    print("=" * 60)
    print(f"Total: {len(missing)} missing tables")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
