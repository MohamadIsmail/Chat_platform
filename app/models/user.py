from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Index
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
	__tablename__ = "users"

	id = Column(Integer, primary_key=True, index=True)
	username = Column(String(50), unique=True, index=True, nullable=False)
	email = Column(String(100), unique=True, index=True, nullable=False)
	hashed_password = Column(String(255), nullable=False)
	is_active = Column(Boolean, default=True, index=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
	
	# Additional fields for better user experience
	display_name = Column(String(100), nullable=True)
	avatar_url = Column(Text, nullable=True)
	last_seen = Column(DateTime(timezone=True), nullable=True)
	
	# User preferences
	timezone = Column(String(50), default="UTC", nullable=False)
	
	# Indexes optimized for Citus queries
	__table_args__ = (
		Index('idx_users_active_created', 'is_active', 'created_at'),
		Index('idx_users_last_seen', 'last_seen'),
	)


