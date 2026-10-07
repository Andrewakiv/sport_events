import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, database_url: str) -> None:
        self._engine: AsyncEngine = create_async_engine(database_url, pool_pre_ping=True)

    async def is_available(self) -> bool:
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            logger.exception("Database connection check failed")
            return False
        return True

    def read_session(self) -> AsyncSession:
        """Create a caller-owned session using the database's default isolation."""
        return AsyncSession(self._engine)

    async def close(self) -> None:
        await self._engine.dispose()
