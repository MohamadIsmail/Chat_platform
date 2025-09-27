from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db, Base, engine
from app.core.security import get_password_hash, verify_password, create_access_token, decode_token
from app.models.user import User
from app.models.message import DirectMessage
from app.schemas.user import UserCreate, UserResponse
from app.schemas.message import DirectMessageCreate, DirectMessageResponse


router = APIRouter(prefix="", tags=["core"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login/token")
# Ensure tables exist in this minimal step
Base.metadata.create_all(bind=engine)


@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
	# Check existing
	if db.query(User).filter((User.username == user_in.username) | (User.email == user_in.email)).first():
		raise HTTPException(status_code=400, detail="Username or email already registered")

	user = User(
		username=user_in.username,
		email=user_in.email,
		hashed_password=get_password_hash(user_in.password)
	)
	db.add(user)
	db.commit()
	db.refresh(user)
	return UserResponse(id=user.id, username=user.username, email=user.email)


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
	user = db.query(User).filter(User.username == form_data.username).first()
	if not user or not verify_password(form_data.password, user.hashed_password):
		raise HTTPException(status_code=400, detail="Incorrect username or password")

	access_token = create_access_token(data={"sub": str(user.id)})
	return {"access_token": access_token, "token_type": "bearer"}


def get_current_user(token: str, db: Session) -> User:
	payload = decode_token(token)
	if not payload or not payload.get("sub"):
		raise HTTPException(status_code=401, detail="Invalid token")
	user = db.query(User).get(int(payload["sub"]))
	if not user:
		raise HTTPException(status_code=401, detail="User not found")
	return user


@router.post("/send", response_model=DirectMessageResponse)
def send_message(message_in: DirectMessageCreate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
	current_user = get_current_user(token, db)
	recipient = db.query(User).get(message_in.recipient_id)
	if not recipient:
		raise HTTPException(status_code=404, detail="Recipient not found")

	msg = DirectMessage(
		content=message_in.content,
		sender_id=current_user.id,
		recipient_id=message_in.recipient_id
	)
	db.add(msg)
	db.commit()
	db.refresh(msg)
	return DirectMessageResponse(
		id=msg.id,
		sender_id=msg.sender_id,
		recipient_id=msg.recipient_id,
		content=msg.content,
		created_at=msg.created_at
	)


@router.get("/messages", response_model=List[DirectMessageResponse])
def get_messages(with_user_id: int, token: str, db: Session = Depends(get_db)):
	current_user = get_current_user(token, db)
	messages = db.query(DirectMessage).filter(
		((DirectMessage.sender_id == current_user.id) & (DirectMessage.recipient_id == with_user_id)) |
		((DirectMessage.sender_id == with_user_id) & (DirectMessage.recipient_id == current_user.id))
	).order_by(DirectMessage.created_at.asc()).all()

	return [
		DirectMessageResponse(
			id=m.id,
			sender_id=m.sender_id,
			recipient_id=m.recipient_id,
			content=m.content,
			created_at=m.created_at
		) for m in messages
	]


