from pydantic import BaseModel
from datetime import datetime


class DirectMessageCreate(BaseModel):
	recipient_id: int
	content: str


class DirectMessageResponse(BaseModel):
	id: int
	sender_id: int
	recipient_id: int
	content: str
	created_at: datetime


