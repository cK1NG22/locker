import os
import asyncpg
from typing import Optional

_pool: Optional[asyncpg.Pool] = None


async def init_db() -> None:
    global _pool
    dsn = os.environ.get("DATABASE_URL", "postgresql://localhost/locker")
    _pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)


async def close_db() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_db() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database not initialized. Did app lifespan run?")
    return _pool
