from fastapi import FastAPI
from app.api.core import router as core_router
from app.core.database import (
	Base, engine, create_tables, 
	init_citus_extension, setup_citus_distribution
)
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
	title="Chat Platform API",
	description="Distributed chat platform with PostgreSQL and Citus",
	version="1.0.0"
)


@app.on_event("startup")
async def on_startup():
	"""Initialize database and Citus extension on startup"""
	try:
		# Create tables
		await create_tables()
		logger.info("Database tables created successfully")
		
		# Initialize Citus extension
		await init_citus_extension()
		
		# Setup Citus distribution
		await setup_citus_distribution()
		
		logger.info("Application startup completed successfully")
	except Exception as e:
		logger.error(f"Error during startup: {e}")
		raise


app.include_router(core_router)


@app.get("/")
def root():
	return {
		"service": "chat-platform", 
		"docs": "/docs",
		"database": "PostgreSQL with Citus",
		"status": "running"
	}


@app.get("/health")
async def health_check():
	"""Health check endpoint"""
	try:
		# Test database connection
		async with engine.begin() as conn:
			await conn.execute("SELECT 1")
		return {"status": "healthy", "database": "connected"}
	except Exception as e:
		return {"status": "unhealthy", "error": str(e)}

