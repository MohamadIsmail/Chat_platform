from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token, decode_token
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.schemas.message import DirectMessageCreate, DirectMessageResponse
from app.services.user_service import UserService
from app.services.message_service import MessageService


router = APIRouter(prefix="", tags=["core"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login/token")
# Ensure tables exist in this minimal step


@router.post("/register", response_model=UserResponse)
async def register(user_in: UserCreate, db: Session = Depends(get_db)):
	user_service = UserService(db)
	
	# Check existing using cached service
	user_exists = await user_service.check_user_exists(
		username=user_in.username, 
		email=user_in.email
	)
	if user_exists:
		raise HTTPException(status_code=400, detail="Username or email already registered")

	# Create user using cached service
	user = await user_service.create_user(
		user_in, 
		get_password_hash(user_in.password)
	)
	return UserResponse(id=user.id, username=user.username, email=user.email)


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
	user_service = UserService(db)
	
	# Use cached service to get user
	user = await user_service.get_user_by_username(form_data.username)
	if not user or not verify_password(form_data.password, user.hashed_password):
		raise HTTPException(status_code=400, detail="Incorrect username or password")

	# Update user's online status
	await user_service.update_user_online_status(user.id, True)

	access_token = create_access_token(data={"sub": str(user.id)})
	return {"access_token": access_token, "token_type": "bearer"}


async def get_current_user(token: str, db: Session) -> User:
	payload = decode_token(token)
	if not payload or not payload.get("sub"):
		raise HTTPException(status_code=401, detail="Invalid token")
	
	user_service = UserService(db)
	user = await user_service.get_user_by_id(int(payload["sub"]))
	if not user:
		raise HTTPException(status_code=401, detail="User not found")
	return user


@router.post("/send", response_model=DirectMessageResponse)
async def send_message(message_in: DirectMessageCreate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
	current_user = await get_current_user(token, db)
	
	user_service = UserService(db)
	recipient = await user_service.get_user_by_id(message_in.recipient_id)
	if not recipient:
		raise HTTPException(status_code=404, detail="Recipient not found")

	message_service = MessageService(db)
	msg = await message_service.create_message(message_in, current_user.id)
	
	return DirectMessageResponse(
		id=msg.id,
		sender_id=msg.sender_id,
		recipient_id=msg.recipient_id,
		content=msg.content,
		created_at=msg.created_at
	)


@router.get("/messages", response_model=List[DirectMessageResponse])
async def get_messages(with_user_id: int, token: str, db: Session = Depends(get_db)):
	current_user = await get_current_user(token, db)
	
	message_service = MessageService(db)
	messages = await message_service.get_conversation_messages(current_user.id, with_user_id)

	return [
		DirectMessageResponse(
			id=m.id,
			sender_id=m.sender_id,
			recipient_id=m.recipient_id,
			content=m.content,
			created_at=m.created_at
		) for m in messages
	]


@router.get("/conversations")
async def get_conversations(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
	"""Get list of conversation partners with unread counts"""
	current_user = await get_current_user(token, db)
	
	message_service = MessageService(db)
	conversations = await message_service.get_conversation_partners(current_user.id)
	
	return [
		{
			"user_id": partner_id,
			"username": username,
			"unread_count": unread_count
		}
		for partner_id, username, unread_count in conversations
	]


@router.get("/unread-count")
async def get_unread_count(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
	"""Get total unread message count for current user"""
	current_user = await get_current_user(token, db)
	
	message_service = MessageService(db)
	count = await message_service.get_unread_count(current_user.id)
	
	return {"unread_count": count}


@router.post("/messages/{message_id}/read")
async def mark_message_read(message_id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
	"""Mark a message as read"""
	current_user = await get_current_user(token, db)
	
	message_service = MessageService(db)
	success = await message_service.mark_message_as_read(message_id, current_user.id)
	
	if not success:
		raise HTTPException(status_code=404, detail="Message not found or not accessible")
	
	return {"message": "Message marked as read"}


@router.get("/users/search")
async def search_users(query: str, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
	"""Search users by username or display name"""
	current_user = await get_current_user(token, db)
	
	user_service = UserService(db)
	users = await user_service.search_users(query)
	
	return [
		{
			"id": user.id,
			"username": user.username,
			"display_name": user.display_name,
			"is_online": user.last_seen is not None
		}
		for user in users if user.id != current_user.id  # Exclude current user
	]


@router.get("/users/online")
async def get_online_users(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
	"""Get list of online users"""
	current_user = await get_current_user(token, db)
	
	user_service = UserService(db)
	online_users = await user_service.get_online_users()
	
	return [
		{
			"id": user.id,
			"username": user.username,
			"display_name": user.display_name,
			"last_seen": user.last_seen
		}
		for user in online_users if user.id != current_user.id  # Exclude current user
	]


