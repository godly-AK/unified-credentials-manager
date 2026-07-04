from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_name: str = "test"
    db_user: str = "postgres"
    db_password: str = "strongpassword"
    db_host: str = "localhost"
    db_port: str = "5432"
    
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expires_seconds: int = 3600
    
    fcm_server_key: str | None = None
    
    class Config:
        env_file = "../.env" # Pointing to root .env from backend/app/core/
        extra = "ignore"

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

settings = Settings()
