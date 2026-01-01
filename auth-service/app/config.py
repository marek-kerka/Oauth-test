from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    JWT_SECRET_KEY: str = "dev-secret-key-please-change-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    REDIS_URL: str = "redis://localhost:6379"
    ALLOWED_PROXY_IPS: str = "127.0.0.1,::1"

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def allowed_ips_list(self) -> List[str]:
        return [ip.strip() for ip in self.ALLOWED_PROXY_IPS.split(",")]


settings = Settings()
