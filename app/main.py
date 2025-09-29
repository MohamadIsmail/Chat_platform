from fastapi import FastAPI
from app.api.core import router as core_router
from app.core.database import (
	Base, engine, create_tables, 
	init_citus_extension, setup_citus_distribution
)
from app.core.cache import cache_manager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
	title="Chat Platform API",
	description="Distributed chat platform with PostgreSQL, Citus, and Redis caching",
	version="1.0.0"
)


@app.on_event("startup")
async def on_startup():
	"""Initialize database, Citus extension, and Redis cache on startup"""
	try:
		# Initialize Redis cache
		await cache_manager.connect()
		logger.info("Redis cache initialized successfully")
		
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


@app.on_event("shutdown")
async def on_shutdown():
	"""Cleanup on shutdown"""
	try:
		# Close Redis connection
		await cache_manager.disconnect()
		logger.info("Application shutdown completed successfully")
	except Exception as e:
		logger.error(f"Error during shutdown: {e}")


app.include_router(core_router)


@app.get("/")
def root():
	return {
		"service": "chat-platform", 
		"docs": "/docs",
		"database": "PostgreSQL with Citus",
		"cache": "Redis",
		"status": "running"
	}


@app.get("/health")
async def health_check():
	"""Health check endpoint"""
	health_status = {"status": "healthy"}
	
	try:
		# Test database connection
		async with engine.begin() as conn:
			await conn.execute("SELECT 1")
		health_status["database"] = "connected"
	except Exception as e:
		health_status["database"] = f"error: {str(e)}"
		health_status["status"] = "unhealthy"
	
	try:
		# Test Redis connection
		redis_available = await cache_manager.is_available()
		health_status["cache"] = "connected" if redis_available else "disconnected"
	except Exception as e:
		health_status["cache"] = f"error: {str(e)}"
		health_status["status"] = "unhealthy"
	
	return health_status


@app.get("/cache/stats")
async def cache_stats():
	"""Get cache statistics"""
	if not await cache_manager.is_available():
		return {"error": "Redis not available"}
	
	try:
		info = await cache_manager.redis.info()
		return {
			"connected_clients": info.get("connected_clients", 0),
			"used_memory": info.get("used_memory_human", "0B"),
			"keyspace_hits": info.get("keyspace_hits", 0),
			"keyspace_misses": info.get("keyspace_misses", 0),
			"total_commands_processed": info.get("total_commands_processed", 0),
			"uptime_in_seconds": info.get("uptime_in_seconds", 0)
		}
	except Exception as e:
		return {"error": str(e)}

