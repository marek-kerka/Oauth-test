from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    JWT_SECRET_KEY: str = "dev-secret-key-please-change-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
