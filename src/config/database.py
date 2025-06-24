import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
import structlog
from contextlib import asynccontextmanager

from src.config.settings import get_settings

logger = structlog.get_logger()

class Base(DeclarativeBase):
    """Base class for all database models"""
    pass

# Global variables for database connection
engine = None
async_session_maker = None

async def init_db():
    """Initialize database connection"""
    global engine, async_session_maker
    
    settings = get_settings()
    
    # Create engine configuration
    engine_config = {
        "echo": settings.DEBUG,
        "future": True
    }
    
    # Add pooling configuration only if not in debug mode
    if settings.DEBUG:
        engine_config["poolclass"] = NullPool
    else:
        engine_config["pool_size"] = settings.DATABASE_POOL_SIZE
        engine_config["max_overflow"] = settings.DATABASE_MAX_OVERFLOW
    
    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        **engine_config
    )
    
    # Create session factory
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    logger.info("Database connection initialized", database_url=settings.DATABASE_URL.split("@")[-1])

async def create_tables():
    """Create all database tables"""
    global engine
    
    if engine is None:
        await init_db()
    
    # Import all models to register them
    from src.models.user import User, UserProfile, DriverDetails
    
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created/verified")

async def close_db_connection():
    """Close database connection"""
    global engine
    
    if engine:
        await engine.dispose()
        logger.info("Database connection closed")

@asynccontextmanager
async def get_db_session():
    """Get database session context manager"""
    global async_session_maker
    
    if async_session_maker is None:
        await init_db()
    
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def get_db():
    """Dependency for FastAPI to get database session"""
    async with get_db_session() as session:
        yield session

# Health check function
async def check_db_health():
    """Check database connection health"""
    try:
        async with get_db_session() as session:
            # Simple query to test connection
            result = await session.execute("SELECT 1")
            result.fetchone()
            return True
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return False