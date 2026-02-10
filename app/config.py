from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://daycast:daycast@localhost:5432/daycast"
    AUTH_MODE: str = "none"
    OPENAI_API_KEY: str = ""
    JWT_SECRET: str = "change-me-in-production"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
