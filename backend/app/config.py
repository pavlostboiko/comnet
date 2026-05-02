from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    first_admin_username: str = "admin"
    first_admin_password: str = "admin123"

    class Config:
        env_file = ".env"


settings = Settings()
