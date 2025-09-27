from pydantic_settings import BaseSettings


class Settings(BaseSettings):
	database_url: str = "sqlite:///./chat.db"
	secret_key: str = "change-this-in-production"
	algorithm: str = "HS256"
	access_token_expire_minutes: int = 60
	host: str = "0.0.0.0"
	port: int = 8000
	debug: bool = True

	class Config:
		env_file = ".env"


settings = Settings()





