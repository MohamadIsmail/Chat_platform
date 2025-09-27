from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class DirectMessage(Base):
	__tablename__ = "direct_messages"

	id = Column(Integer, primary_key=True, index=True)
	content = Column(Text, nullable=False)
	sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
	recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
	created_at = Column(DateTime(timezone=True), server_default=func.now())

	# Relationships
	sender = relationship("User", foreign_keys=[sender_id])
	recipient = relationship("User", foreign_keys=[recipient_id])


