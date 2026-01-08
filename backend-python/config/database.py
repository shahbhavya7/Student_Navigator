from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging

from config.settings import settings

logger = logging.getLogger(__name__)

# SQLAlchemy Base
Base = declarative_base()

# Sync engine for compatibility
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.LOG_LEVEL == "DEBUG"
)

# Async engine for non-blocking operations
async_database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
async_engine = create_async_engine(
    async_database_url,
    poolclass=NullPool,
    echo=settings.LOG_LEVEL == "DEBUG"
)

# Session factories
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


def get_db():
    """Dependency for sync database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for async database sessions"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


async def init_db():
    """Initialize database connections"""
    try:
        # Test async connection
        async with async_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection initialized")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise


async def close_db():
    """Close database connections"""
    await async_engine.dispose()
    logger.info("🔌 Database connections closed")
