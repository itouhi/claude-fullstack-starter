from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """アプリ設定 (.env で上書き可能)。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "develop-backend"
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
