from fastapi import FastAPI
from app.api.core import router as core_router
from app.core.database import Base, engine


app = FastAPI(title="Chat Core API")


@app.on_event("startup")
def on_startup():
	Base.metadata.create_all(bind=engine)


app.include_router(core_router)


@app.get("/")
def root():
	return {"service": "chat-core", "docs": "/docs"}

