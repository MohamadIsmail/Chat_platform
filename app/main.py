from fastapi import FastAPI
from app.api.core import router as core_router
from app.core.database import (
	Base, engine, create_tables, 
	init_citus_extension, setup_citus_distribution
)
from app.core.cache import cache_manager
from app.core.metrics import setup_metrics
from app.core.logging import setup_logging, chat_logger
import logging

# Setup structured logging
setup_logging()

app = FastAPI(
	title="Chat Platform API",
	description="Distributed chat platform with PostgreSQL, Citus, Redis caching, and monitoring",
	version="1.0.0"
)

# Setup Prometheus metrics
setup_metrics(app)


@app.on_event("startup")
async def on_startup():
	"""Initialize database, Citus extension, and Redis cache on startup"""
	try:
		chat_logger.system_event(
			event_type="application_startup",
			component="chat-platform",
			status="starting",
			details="Initializing services"
		)
		
		# Initialize Redis cache
		await cache_manager.connect()
		chat_logger.system_event(
			event_type="service_initialized",
			component="redis",
			status="started",
			details="Redis cache initialized successfully"
		)
		
		# Create tables
		await create_tables()
		chat_logger.system_event(
			event_type="service_initialized",
			component="database",
			status="started",
			details="Database tables created successfully"
		)
		
		# Initialize Citus extension
		await init_citus_extension()
		chat_logger.system_event(
			event_type="service_initialized",
			component="citus",
			status="started",
			details="Citus extension initialized"
		)
		
		# Setup Citus distribution
		await setup_citus_distribution()
		chat_logger.system_event(
			event_type="service_initialized",
			component="citus",
			status="configured",
			details="Citus distribution setup completed"
		)
		
		chat_logger.system_event(
			event_type="application_startup",
			component="chat-platform",
			status="completed",
			details="All services initialized successfully"
		)
	except Exception as e:
		chat_logger.system_event(
			event_type="application_startup",
			component="chat-platform",
			status="failed",
			details=f"Startup failed: {str(e)}"
		)
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

