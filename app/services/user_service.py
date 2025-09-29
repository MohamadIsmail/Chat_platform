from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.user import User
from app.core.cache import cache_service, CacheKeys, CacheInvalidation
from app.schemas.user import UserCreate, UserResponse
from config import settings
import logging

logger = logging.getLogger(__name__)


class UserService:
	"""Cached user service with Redis integration"""
	
	def __init__(self, db: Session):
		self.db = db
	
	async def get_user_by_id(self, user_id: int) -> Optional[User]:
		"""Get user by ID with caching"""
		cache_key = CacheKeys.user_profile(user_id)
		
		# Try cache first
		cached_user = await cache_service.get(cache_key)
		if cached_user:
			logger.debug(f"Cache hit for user {user_id}")
			return User(**cached_user) if isinstance(cached_user, dict) else cached_user
		
		# Query database
		user = self.db.query(User).filter(User.id == user_id).first()
		if user:
			# Cache the result
			await cache_service.set(
				cache_key, 
				user.__dict__, 
				ttl=settings.cache_user_ttl
			)
			logger.debug(f"Cached user {user_id}")
		
		return user
	
	async def get_user_by_username(self, username: str) -> Optional[User]:
		"""Get user by username with caching"""
		cache_key = CacheKeys.user_by_username(username)
		
		# Try cache first
		cached_user = await cache_service.get(cache_key)
		if cached_user:
			logger.debug(f"Cache hit for username {username}")
			return User(**cached_user) if isinstance(cached_user, dict) else cached_user
		
		# Query database
		user = self.db.query(User).filter(User.username == username).first()
		if user:
			# Cache the result
			await cache_service.set(
				cache_key, 
				user.__dict__, 
				ttl=settings.cache_user_ttl
			)
			# Also cache by user ID
			await cache_service.set(
				CacheKeys.user_profile(user.id), 
				user.__dict__, 
				ttl=settings.cache_user_ttl
			)
			logger.debug(f"Cached user {username}")
		
		return user
	
	async def get_user_by_email(self, email: str) -> Optional[User]:
		"""Get user by email with caching"""
		cache_key = CacheKeys.user_by_email(email)
		
		# Try cache first
		cached_user = await cache_service.get(cache_key)
		if cached_user:
			logger.debug(f"Cache hit for email {email}")
			return User(**cached_user) if isinstance(cached_user, dict) else cached_user
		
		# Query database
		user = self.db.query(User).filter(User.email == email).first()
		if user:
			# Cache the result
			await cache_service.set(
				cache_key, 
				user.__dict__, 
				ttl=settings.cache_user_ttl
			)
			# Also cache by user ID
			await cache_service.set(
				CacheKeys.user_profile(user.id), 
				user.__dict__, 
				ttl=settings.cache_user_ttl
			)
			logger.debug(f"Cached user {email}")
		
		return user
	
	async def create_user(self, user_data: UserCreate, hashed_password: str) -> User:
		"""Create a new user and invalidate related caches"""
		user = User(
			username=user_data.username,
			email=user_data.email,
			hashed_password=hashed_password
		)
		
		self.db.add(user)
		self.db.commit()
		self.db.refresh(user)
		
		# Cache the new user
		await cache_service.set(
			CacheKeys.user_profile(user.id), 
			user.__dict__, 
			ttl=settings.cache_user_ttl
		)
		await cache_service.set(
			CacheKeys.user_by_username(user.username), 
			user.__dict__, 
			ttl=settings.cache_user_ttl
		)
		await cache_service.set(
			CacheKeys.user_by_email(user.email), 
			user.__dict__, 
			ttl=settings.cache_user_ttl
		)
		
		logger.info(f"Created and cached new user {user.id}")
		return user
	
	async def update_user(self, user_id: int, **kwargs) -> Optional[User]:
		"""Update user and invalidate caches"""
		user = self.db.query(User).filter(User.id == user_id).first()
		if not user:
			return None
		
		# Update fields
		for key, value in kwargs.items():
			if hasattr(user, key):
				setattr(user, key, value)
		
		self.db.commit()
		self.db.refresh(user)
		
		# Invalidate and refresh cache
		await CacheInvalidation.invalidate_user_cache(user_id)
		
		# Re-cache the updated user
		await cache_service.set(
			CacheKeys.user_profile(user.id), 
			user.__dict__, 
			ttl=settings.cache_user_ttl
		)
		await cache_service.set(
			CacheKeys.user_by_username(user.username), 
			user.__dict__, 
			ttl=settings.cache_user_ttl
		)
		await cache_service.set(
			CacheKeys.user_by_email(user.email), 
			user.__dict__, 
			ttl=settings.cache_user_ttl
		)
		
		logger.info(f"Updated and re-cached user {user_id}")
		return user
	
	async def check_user_exists(self, username: str = None, email: str = None) -> bool:
		"""Check if user exists by username or email"""
		if username:
			user = await self.get_user_by_username(username)
			return user is not None
		elif email:
			user = await self.get_user_by_email(email)
			return user is not None
		return False
	
	async def get_online_users(self) -> List[User]:
		"""Get list of online users with caching"""
		cache_key = CacheKeys.online_users()
		
		# Try cache first
		cached_users = await cache_service.get(cache_key)
		if cached_users:
			logger.debug("Cache hit for online users")
			return [User(**user_data) if isinstance(user_data, dict) else user_data 
					for user_data in cached_users]
		
		# Query database for recently active users
		from datetime import datetime, timedelta
		recent_time = datetime.utcnow() - timedelta(minutes=5)
		
		users = self.db.query(User).filter(
			and_(
				User.is_active == True,
				User.last_seen >= recent_time
			)
		).all()
		
		# Cache the result
		user_dicts = [user.__dict__ for user in users]
		await cache_service.set(
			cache_key, 
			user_dicts, 
			ttl=60  # Short TTL for online status
		)
		
		logger.debug(f"Cached {len(users)} online users")
		return users
	
	async def update_user_online_status(self, user_id: int, is_online: bool = True):
		"""Update user's online status and cache"""
		from datetime import datetime
		
		user = await self.get_user_by_id(user_id)
		if user:
			user.last_seen = datetime.utcnow()
			self.db.commit()
			
			# Update online status cache
			online_key = CacheKeys.user_online_status(user_id)
			await cache_service.set(online_key, is_online, ttl=300)  # 5 minutes
			
			# Invalidate online users list
			await cache_service.delete(CacheKeys.online_users())
			
			logger.debug(f"Updated online status for user {user_id}")
	
	async def search_users(self, query: str, limit: int = 10) -> List[User]:
		"""Search users by username or display name"""
		cache_key = f"user_search:{query}:{limit}"
		
		# Try cache first
		cached_users = await cache_service.get(cache_key)
		if cached_users:
			logger.debug(f"Cache hit for user search: {query}")
			return [User(**user_data) if isinstance(user_data, dict) else user_data 
					for user_data in cached_users]
		
		# Search database
		users = self.db.query(User).filter(
			and_(
				User.is_active == True,
				or_(
					User.username.ilike(f"%{query}%"),
					User.display_name.ilike(f"%{query}%")
				)
			)
		).limit(limit).all()
		
		# Cache the result
		user_dicts = [user.__dict__ for user in users]
		await cache_service.set(
			cache_key, 
			user_dicts, 
			ttl=settings.cache_user_ttl
		)
		
		logger.debug(f"Cached search results for: {query}")
		return users
