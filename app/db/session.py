from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.base import make_sessionmaker

_sessionmaker = None


def get_sessionmaker():
    global _sessionmaker
    if _sessionmaker is None:
        database_url = get_settings().database_url
        if not database_url:
            raise RuntimeError("DATABASE_URL is not configured")
        _sessionmaker = make_sessionmaker(database_url)
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        yield session
