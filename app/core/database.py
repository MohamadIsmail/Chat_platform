from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config import settings
import logging

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
	pass


# Create async engine for PostgreSQL
if settings.database_url.startswith("postgresql"):
	# Use async engine for PostgreSQL
	engine = create_async_engine(
		settings.database_url,
		echo=settings.debug,
		pool_pre_ping=True,
		pool_recycle=300,
	)
	SessionLocal = async_sessionmaker(
		engine,
		class_=AsyncSession,
		expire_on_commit=False
	)
else:
	# Fallback to sync engine for SQLite
	engine = create_engine(
		settings.database_url,
		connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
		echo=settings.debug
	)
	SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


async def get_db():
	"""Async database dependency for FastAPI"""
	if isinstance(SessionLocal, async_sessionmaker):
		async with SessionLocal() as session:
			try:
				yield session
			finally:
				await session.close()
	else:
		# Fallback for sync sessions
		db = SessionLocal()
		try:
			yield db
		finally:
			db.close()


async def init_citus_extension():
	"""Initialize Citus extension if using PostgreSQL"""
	if not settings.database_url.startswith("postgresql"):
		return
	
	try:
		async with engine.begin() as conn:
			# Enable Citus extension
			await conn.execute(text("CREATE EXTENSION IF NOT EXISTS citus;"))
			logger.info("Citus extension enabled successfully")
	except Exception as e:
		logger.warning(f"Could not enable Citus extension: {e}")


async def setup_citus_distribution():
	"""Set up Citus distribution for tables"""
	if not settings.citus_enabled or not settings.database_url.startswith("postgresql"):
		return
	
	try:
		async with engine.begin() as conn:
			# Convert tables to distributed tables
			# Users table - distributed by user ID
			await conn.execute(text("""
				SELECT create_distributed_table('users', 'id');
			"""))
			
			# Messages table - distributed by sender_id for better query performance
			await conn.execute(text("""
				SELECT create_distributed_table('direct_messages', 'sender_id');
			"""))
			
			logger.info("Citus distribution setup completed")
	except Exception as e:
		logger.warning(f"Could not setup Citus distribution: {e}")


async def create_tables():
	"""Create all tables"""
	async with engine.begin() as conn:
		await conn.run_sync(Base.metadata.create_all)


