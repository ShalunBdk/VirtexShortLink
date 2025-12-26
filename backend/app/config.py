from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Database
    DATABASE_URL: str = "sqlite:///./shortlinks.db"

    # Security
    SECRET_KEY: str = "virtexfood-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Rate Limiting
    RATE_LIMIT_PER_HOUR: int = 10
    RATE_LIMIT_PER_DAY: int = 50

    # Short codes
    SHORT_CODE_LENGTH: int = 5  # 4 or 5 characters

    # Domain
    BASE_URL: str = "https://vrxf.ru"

    class Config:
        env_file = ".env"


settings = Settings()
