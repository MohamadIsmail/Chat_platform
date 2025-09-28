from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
	# Database configuration
	database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/chat_platform"
	# Fallback to SQLite for development if PostgreSQL is not available
	use_sqlite_fallback: bool = True
	
	# Application settings
	secret_key: str = "change-this-in-production"
	algorithm: str = "HS256"
	access_token_expire_minutes: int = 60
	host: str = "0.0.0.0"
	port: int = 8000
	debug: bool = True
	
	# Citus-specific settings
	citus_enabled: bool = True
	citus_distribution_column: str = "user_id"  # For distributing messages by user
	
	class Config:
		env_file = ".env"
	
	@property
	def get_database_url(self) -> str:
		"""Get the appropriate database URL based on environment"""
		if self.use_sqlite_fallback and not self._is_postgres_available():
			return "sqlite:///./chat.db"
		return self.database_url
	
	def _is_postgres_available(self) -> bool:
		"""Check if PostgreSQL is available"""
		try:
			import asyncpg
			# You could add a more sophisticated check here
			return True
		except ImportError:
			return False


settings = Settings()





