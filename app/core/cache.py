import json
import pickle
import asyncio
from typing import Any, Optional, Union, Dict, List
from functools import wraps
import aioredis
from aioredis import Redis
from config import settings
import logging

logger = logging.getLogger(__name__)


class CacheManager:
	"""Redis cache manager with connection pooling and error handling"""
	
	def __init__(self):
		self.redis: Optional[Redis] = None
		self._connection_pool = None
	
	async def connect(self):
		"""Initialize Redis connection"""
		if not settings.cache_enabled:
			logger.info("Cache is disabled")
			return
		
		try:
			self._connection_pool = aioredis.ConnectionPool.from_url(
				settings.get_redis_url,
				max_connections=settings.redis_max_connections,
				retry_on_timeout=settings.redis_retry_on_timeout,
				decode_responses=False  # We'll handle encoding ourselves
			)
			self.redis = aioredis.Redis(connection_pool=self._connection_pool)
			
			# Test connection
			await self.redis.ping()
			logger.info("Redis connection established successfully")
			
		except Exception as e:
			logger.error(f"Failed to connect to Redis: {e}")
			self.redis = None
	
	async def disconnect(self):
		"""Close Redis connection"""
		if self.redis:
			await self.redis.close()
			if self._connection_pool:
				await self._connection_pool.disconnect()
			logger.info("Redis connection closed")
	
	async def is_available(self) -> bool:
		"""Check if Redis is available"""
		if not self.redis:
			return False
		try:
			await self.redis.ping()
			return True
		except Exception:
			return False


# Global cache manager instance
cache_manager = CacheManager()


class CacheService:
	"""High-level cache service with serialization and error handling"""
	
	def __init__(self, cache_manager: CacheManager):
		self.cache_manager = cache_manager
	
	async def get(self, key: str) -> Optional[Any]:
		"""Get value from cache"""
		if not await self.cache_manager.is_available():
			return None
		
		try:
			value = await self.cache_manager.redis.get(key)
			if value is None:
				return None
			
			# Try JSON first, fallback to pickle
			try:
				return json.loads(value.decode('utf-8'))
			except (json.JSONDecodeError, UnicodeDecodeError):
				return pickle.loads(value)
				
		except Exception as e:
			logger.warning(f"Cache get error for key {key}: {e}")
			return None
	
	async def set(
		self, 
		key: str, 
		value: Any, 
		ttl: Optional[int] = None,
		serialize_method: str = "json"
	) -> bool:
		"""Set value in cache"""
		if not await self.cache_manager.is_available():
			return False
		
		try:
			# Serialize value
			if serialize_method == "json":
				serialized_value = json.dumps(value, default=str)
			else:
				serialized_value = pickle.dumps(value)
			
			# Set with TTL
			ttl = ttl or settings.cache_default_ttl
			await self.cache_manager.redis.setex(key, ttl, serialized_value)
			return True
			
		except Exception as e:
			logger.warning(f"Cache set error for key {key}: {e}")
			return False
	
	async def delete(self, key: str) -> bool:
		"""Delete key from cache"""
		if not await self.cache_manager.is_available():
			return False
		
		try:
			result = await self.cache_manager.redis.delete(key)
			return result > 0
		except Exception as e:
			logger.warning(f"Cache delete error for key {key}: {e}")
			return False
	
	async def delete_pattern(self, pattern: str) -> int:
		"""Delete all keys matching pattern"""
		if not await self.cache_manager.is_available():
			return 0
		
		try:
			keys = await self.cache_manager.redis.keys(pattern)
			if keys:
				return await self.cache_manager.redis.delete(*keys)
			return 0
		except Exception as e:
			logger.warning(f"Cache delete pattern error for {pattern}: {e}")
			return 0
	
	async def exists(self, key: str) -> bool:
		"""Check if key exists in cache"""
		if not await self.cache_manager.is_available():
			return False
		
		try:
			return await self.cache_manager.redis.exists(key)
		except Exception as e:
			logger.warning(f"Cache exists error for key {key}: {e}")
			return False
	
	async def get_or_set(
		self, 
		key: str, 
		func, 
		ttl: Optional[int] = None,
		*args, 
		**kwargs
	) -> Any:
		"""Get from cache or set using function result"""
		# Try to get from cache first
		cached_value = await self.get(key)
		if cached_value is not None:
			return cached_value
		
		# Execute function and cache result
		if asyncio.iscoroutinefunction(func):
			value = await func(*args, **kwargs)
		else:
			value = func(*args, **kwargs)
		
		await self.set(key, value, ttl)
		return value


# Global cache service instance
cache_service = CacheService(cache_manager)


def cache_key(prefix: str, *args, **kwargs) -> str:
	"""Generate cache key from prefix and arguments"""
	key_parts = [prefix]
	
	# Add positional arguments
	for arg in args:
		if isinstance(arg, (str, int, float)):
			key_parts.append(str(arg))
		else:
			key_parts.append(str(hash(str(arg))))
	
	# Add keyword arguments
	for k, v in sorted(kwargs.items()):
		if isinstance(v, (str, int, float)):
			key_parts.append(f"{k}:{v}")
		else:
			key_parts.append(f"{k}:{hash(str(v))}")
	
	return ":".join(key_parts)


def cached(
	key_prefix: str,
	ttl: Optional[int] = None,
	invalidate_on: Optional[List[str]] = None
):
	"""Decorator for caching function results"""
	def decorator(func):
		@wraps(func)
		async def async_wrapper(*args, **kwargs):
			# Generate cache key
			key = cache_key(key_prefix, *args, **kwargs)
			
			# Try to get from cache
			cached_result = await cache_service.get(key)
			if cached_result is not None:
				return cached_result
			
			# Execute function
			result = await func(*args, **kwargs)
			
			# Cache result
			await cache_service.set(key, result, ttl)
			
			return result
		
		@wraps(func)
		def sync_wrapper(*args, **kwargs):
			# Generate cache key
			key = cache_key(key_prefix, *args, **kwargs)
			
			# Try to get from cache (sync version)
			import asyncio
			loop = asyncio.get_event_loop()
			cached_result = loop.run_until_complete(cache_service.get(key))
			if cached_result is not None:
				return cached_result
			
			# Execute function
			result = func(*args, **kwargs)
			
			# Cache result
			loop.run_until_complete(cache_service.set(key, result, ttl))
			
			return result
		
		# Return appropriate wrapper
		if asyncio.iscoroutinefunction(func):
			return async_wrapper
		else:
			return sync_wrapper
	
	return decorator


class CacheInvalidation:
	"""Cache invalidation strategies"""
	
	@staticmethod
	async def invalidate_user_cache(user_id: int):
		"""Invalidate all cache entries related to a user"""
		patterns = [
			f"user:{user_id}:*",
			f"user_profile:{user_id}",
			f"user_messages:{user_id}:*",
			f"conversation:{user_id}:*",
			f"*:{user_id}:*"
		]
		
		total_deleted = 0
		for pattern in patterns:
			deleted = await cache_service.delete_pattern(pattern)
			total_deleted += deleted
		
		logger.info(f"Invalidated {total_deleted} cache entries for user {user_id}")
	
	@staticmethod
	async def invalidate_message_cache(message_id: int, sender_id: int, recipient_id: int):
		"""Invalidate cache entries related to a specific message"""
		patterns = [
			f"message:{message_id}",
			f"conversation:{sender_id}:{recipient_id}:*",
			f"conversation:{recipient_id}:{sender_id}:*",
			f"user_messages:{sender_id}:*",
			f"user_messages:{recipient_id}:*"
		]
		
		total_deleted = 0
		for pattern in patterns:
			deleted = await cache_service.delete_pattern(pattern)
			total_deleted += deleted
		
		logger.info(f"Invalidated {total_deleted} cache entries for message {message_id}")
	
	@staticmethod
	async def invalidate_conversation_cache(user1_id: int, user2_id: int):
		"""Invalidate cache entries for a conversation between two users"""
		patterns = [
			f"conversation:{user1_id}:{user2_id}:*",
			f"conversation:{user2_id}:{user1_id}:*",
			f"user_messages:{user1_id}:*",
			f"user_messages:{user2_id}:*"
		]
		
		total_deleted = 0
		for pattern in patterns:
			deleted = await cache_service.delete_pattern(pattern)
			total_deleted += deleted
		
		logger.info(f"Invalidated {total_deleted} cache entries for conversation {user1_id}-{user2_id}")


# Cache key generators for different data types
class CacheKeys:
	"""Standardized cache key generators"""
	
	@staticmethod
	def user_profile(user_id: int) -> str:
		return f"user_profile:{user_id}"
	
	@staticmethod
	def user_by_username(username: str) -> str:
		return f"user_username:{username}"
	
	@staticmethod
	def user_by_email(email: str) -> str:
		return f"user_email:{email}"
	
	@staticmethod
	def message(message_id: int) -> str:
		return f"message:{message_id}"
	
	@staticmethod
	def conversation_messages(user1_id: int, user2_id: int, limit: int = 50, offset: int = 0) -> str:
		# Sort user IDs to ensure consistent key
		sorted_ids = sorted([user1_id, user2_id])
		return f"conversation:{sorted_ids[0]}:{sorted_ids[1]}:messages:{limit}:{offset}"
	
	@staticmethod
	def user_conversations(user_id: int) -> str:
		return f"user_conversations:{user_id}"
	
	@staticmethod
	def user_messages(user_id: int, limit: int = 50, offset: int = 0) -> str:
		return f"user_messages:{user_id}:{limit}:{offset}"
	
	@staticmethod
	def online_users() -> str:
		return "online_users"
	
	@staticmethod
	def user_online_status(user_id: int) -> str:
		return f"user_online:{user_id}"
