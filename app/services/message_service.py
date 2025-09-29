from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from app.models.message import DirectMessage
from app.models.user import User
from app.core.cache import cache_service, CacheKeys, CacheInvalidation
from app.schemas.message import DirectMessageCreate, DirectMessageResponse
from config import settings
import logging

logger = logging.getLogger(__name__)


class MessageService:
	"""Cached message service with Redis integration"""
	
	def __init__(self, db: Session):
		self.db = db
	
	async def get_message_by_id(self, message_id: int) -> Optional[DirectMessage]:
		"""Get message by ID with caching"""
		cache_key = CacheKeys.message(message_id)
		
		# Try cache first
		cached_message = await cache_service.get(cache_key)
		if cached_message:
			logger.debug(f"Cache hit for message {message_id}")
			return DirectMessage(**cached_message) if isinstance(cached_message, dict) else cached_message
		
		# Query database
		message = self.db.query(DirectMessage).filter(DirectMessage.id == message_id).first()
		if message:
			# Cache the result
			await cache_service.set(
				cache_key, 
				message.__dict__, 
				ttl=settings.cache_message_ttl
			)
			logger.debug(f"Cached message {message_id}")
		
		return message
	
	async def get_conversation_messages(
		self, 
		user1_id: int, 
		user2_id: int, 
		limit: int = 50, 
		offset: int = 0
	) -> List[DirectMessage]:
		"""Get conversation messages between two users with caching"""
		cache_key = CacheKeys.conversation_messages(user1_id, user2_id, limit, offset)
		
		# Try cache first
		cached_messages = await cache_service.get(cache_key)
		if cached_messages:
			logger.debug(f"Cache hit for conversation {user1_id}-{user2_id}")
			return [DirectMessage(**msg_data) if isinstance(msg_data, dict) else msg_data 
					for msg_data in cached_messages]
		
		# Query database
		messages = self.db.query(DirectMessage).filter(
			or_(
				and_(DirectMessage.sender_id == user1_id, DirectMessage.recipient_id == user2_id),
				and_(DirectMessage.sender_id == user2_id, DirectMessage.recipient_id == user1_id)
			)
		).order_by(desc(DirectMessage.created_at)).offset(offset).limit(limit).all()
		
		# Cache the result
		message_dicts = [message.__dict__ for message in messages]
		await cache_service.set(
			cache_key, 
			message_dicts, 
			ttl=settings.cache_conversation_ttl
		)
		
		logger.debug(f"Cached {len(messages)} messages for conversation {user1_id}-{user2_id}")
		return messages
	
	async def get_user_messages(
		self, 
		user_id: int, 
		limit: int = 50, 
		offset: int = 0
	) -> List[DirectMessage]:
		"""Get all messages for a user (sent and received) with caching"""
		cache_key = CacheKeys.user_messages(user_id, limit, offset)
		
		# Try cache first
		cached_messages = await cache_service.get(cache_key)
		if cached_messages:
			logger.debug(f"Cache hit for user messages {user_id}")
			return [DirectMessage(**msg_data) if isinstance(msg_data, dict) else msg_data 
					for msg_data in cached_messages]
		
		# Query database
		messages = self.db.query(DirectMessage).filter(
			or_(
				DirectMessage.sender_id == user_id,
				DirectMessage.recipient_id == user_id
			)
		).order_by(desc(DirectMessage.created_at)).offset(offset).limit(limit).all()
		
		# Cache the result
		message_dicts = [message.__dict__ for message in messages]
		await cache_service.set(
			cache_key, 
			message_dicts, 
			ttl=settings.cache_message_ttl
		)
		
		logger.debug(f"Cached {len(messages)} messages for user {user_id}")
		return messages
	
	async def create_message(
		self, 
		message_data: DirectMessageCreate, 
		sender_id: int
	) -> DirectMessage:
		"""Create a new message and invalidate related caches"""
		message = DirectMessage(
			content=message_data.content,
			sender_id=sender_id,
			recipient_id=message_data.recipient_id,
			message_type=getattr(message_data, 'message_type', 'text')
		)
		
		self.db.add(message)
		self.db.commit()
		self.db.refresh(message)
		
		# Cache the new message
		await cache_service.set(
			CacheKeys.message(message.id), 
			message.__dict__, 
			ttl=settings.cache_message_ttl
		)
		
		# Invalidate related caches
		await CacheInvalidation.invalidate_message_cache(
			message.id, 
			sender_id, 
			message_data.recipient_id
		)
		
		logger.info(f"Created and cached new message {message.id}")
		return message
	
	async def mark_message_as_read(self, message_id: int, user_id: int) -> bool:
		"""Mark a message as read and update cache"""
		message = await self.get_message_by_id(message_id)
		if not message:
			return False
		
		# Only recipient can mark as read
		if message.recipient_id != user_id:
			return False
		
		# Update in database
		message.is_read = 1
		self.db.commit()
		
		# Update cache
		await cache_service.set(
			CacheKeys.message(message_id), 
			message.__dict__, 
			ttl=settings.cache_message_ttl
		)
		
		# Invalidate conversation caches
		await CacheInvalidation.invalidate_conversation_cache(
			message.sender_id, 
			message.recipient_id
		)
		
		logger.info(f"Marked message {message_id} as read")
		return True
	
	async def get_unread_count(self, user_id: int) -> int:
		"""Get unread message count for a user with caching"""
		cache_key = f"unread_count:{user_id}"
		
		# Try cache first
		cached_count = await cache_service.get(cache_key)
		if cached_count is not None:
			logger.debug(f"Cache hit for unread count {user_id}")
			return cached_count
		
		# Query database
		count = self.db.query(DirectMessage).filter(
			and_(
				DirectMessage.recipient_id == user_id,
				DirectMessage.is_read == 0
			)
		).count()
		
		# Cache the result
		await cache_service.set(cache_key, count, ttl=60)  # Short TTL for real-time data
		
		logger.debug(f"Cached unread count {count} for user {user_id}")
		return count
	
	async def get_conversation_partners(self, user_id: int) -> List[Tuple[int, str, int]]:
		"""Get list of conversation partners with unread counts"""
		cache_key = f"conversation_partners:{user_id}"
		
		# Try cache first
		cached_partners = await cache_service.get(cache_key)
		if cached_partners:
			logger.debug(f"Cache hit for conversation partners {user_id}")
			return cached_partners
		
		# Query database for unique conversation partners
		partners_query = self.db.query(
			User.id,
			User.username,
			User.display_name
		).join(
			DirectMessage,
			or_(
				and_(DirectMessage.sender_id == user_id, DirectMessage.recipient_id == User.id),
				and_(DirectMessage.recipient_id == user_id, DirectMessage.sender_id == User.id)
			)
		).distinct().all()
		
		# Get unread counts for each partner
		partners_with_counts = []
		for partner_id, username, display_name in partners_query:
			unread_count = self.db.query(DirectMessage).filter(
				and_(
					DirectMessage.sender_id == partner_id,
					DirectMessage.recipient_id == user_id,
					DirectMessage.is_read == 0
				)
			).count()
			
			partners_with_counts.append((
				partner_id,
				display_name or username,
				unread_count
			))
		
		# Sort by unread count (descending) then by username
		partners_with_counts.sort(key=lambda x: (-x[2], x[1]))
		
		# Cache the result
		await cache_service.set(
			cache_key, 
			partners_with_counts, 
			ttl=settings.cache_conversation_ttl
		)
		
		logger.debug(f"Cached {len(partners_with_counts)} conversation partners for user {user_id}")
		return partners_with_counts
	
	async def search_messages(
		self, 
		user_id: int, 
		query: str, 
		limit: int = 20
	) -> List[DirectMessage]:
		"""Search messages containing query text"""
		cache_key = f"message_search:{user_id}:{query}:{limit}"
		
		# Try cache first
		cached_messages = await cache_service.get(cache_key)
		if cached_messages:
			logger.debug(f"Cache hit for message search: {query}")
			return [DirectMessage(**msg_data) if isinstance(msg_data, dict) else msg_data 
					for msg_data in cached_messages]
		
		# Search database
		messages = self.db.query(DirectMessage).filter(
			and_(
				or_(
					DirectMessage.sender_id == user_id,
					DirectMessage.recipient_id == user_id
				),
				DirectMessage.content.ilike(f"%{query}%")
			)
		).order_by(desc(DirectMessage.created_at)).limit(limit).all()
		
		# Cache the result
		message_dicts = [message.__dict__ for message in messages]
		await cache_service.set(
			cache_key, 
			message_dicts, 
			ttl=settings.cache_message_ttl
		)
		
		logger.debug(f"Cached {len(messages)} search results for: {query}")
		return messages
	
	async def delete_message(self, message_id: int, user_id: int) -> bool:
		"""Delete a message (only sender can delete)"""
		message = await self.get_message_by_id(message_id)
		if not message or message.sender_id != user_id:
			return False
		
		# Delete from database
		self.db.delete(message)
		self.db.commit()
		
		# Invalidate caches
		await cache_service.delete(CacheKeys.message(message_id))
		await CacheInvalidation.invalidate_message_cache(
			message_id, 
			message.sender_id, 
			message.recipient_id
		)
		
		logger.info(f"Deleted message {message_id}")
		return True
	
	async def get_recent_messages(self, user_id: int, limit: int = 10) -> List[DirectMessage]:
		"""Get recent messages for a user (for notifications/activity feed)"""
		cache_key = f"recent_messages:{user_id}:{limit}"
		
		# Try cache first
		cached_messages = await cache_service.get(cache_key)
		if cached_messages:
			logger.debug(f"Cache hit for recent messages {user_id}")
			return [DirectMessage(**msg_data) if isinstance(msg_data, dict) else msg_data 
					for msg_data in cached_messages]
		
		# Query database
		messages = self.db.query(DirectMessage).filter(
			DirectMessage.recipient_id == user_id
		).order_by(desc(DirectMessage.created_at)).limit(limit).all()
		
		# Cache the result
		message_dicts = [message.__dict__ for message in messages]
		await cache_service.set(
			cache_key, 
			message_dicts, 
			ttl=300  # 5 minutes for recent messages
		)
		
		logger.debug(f"Cached {len(messages)} recent messages for user {user_id}")
		return messages
