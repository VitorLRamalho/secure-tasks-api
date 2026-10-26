from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Toda configuração vem do ambiente. Nada sensível tem valor padrão."""

    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    env: str = "production"  # "dev" liga o /docs
    database_url: str = "sqlite:///./data/app.db"
    jwt_secret: str = Field(min_length=32)  # obrigatório: sem ele a app não sobe
    jwt_algorithm: str = "HS256"
    jwt_ttl_minutes: int = 30


settings = Settings()
