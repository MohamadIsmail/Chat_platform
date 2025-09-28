from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, BigInteger, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class DirectMessage(Base):
	__tablename__ = "direct_messages"

	# Use BigInteger for better Citus distribution
	id = Column(BigInteger, primary_key=True, index=True)
	content = Column(Text, nullable=False)
	sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
	recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
	
	# Add message type for future extensibility
	message_type = Column(Text, default="text", nullable=False)
	
	# Add read status for better user experience
	is_read = Column(Integer, default=0, nullable=False)  # 0=unread, 1=read

	# Relationships
	sender = relationship("User", foreign_keys=[sender_id])
	recipient = relationship("User", foreign_keys=[recipient_id])
	
	# Indexes optimized for Citus queries
	__table_args__ = (
		Index('idx_direct_messages_sender_created', 'sender_id', 'created_at'),
		Index('idx_direct_messages_recipient_created', 'recipient_id', 'created_at'),
		Index('idx_direct_messages_conversation', 'sender_id', 'recipient_id', 'created_at'),
	)


