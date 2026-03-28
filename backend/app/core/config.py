from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    rag_api_base_url: str = Field(
        default="http://localhost:8080",
        validation_alias="RAG_API_BASE_URL",
        description="Базовый URL rag-api (без завершающего /).",
    )
    rag_api_timeout_sec: float = Field(
        default=120.0,
        validation_alias="RAG_API_TIMEOUT_SEC",
    )
    rag_api_enabled: bool = Field(default=True, validation_alias="RAG_API_ENABLED")

    @field_validator("rag_api_enabled", mode="before")
    @classmethod
    def _bool_env(cls, v: object) -> bool:
        if isinstance(v, bool):
            return v
        if v is None:
            return True
        s = str(v).strip().lower()
        if s in ("0", "false", "no", "off", ""):
            return False
        if s in ("1", "true", "yes", "on"):
            return True
        return bool(v)
    rag_api_debug_default: bool = Field(default=False, validation_alias="RAG_API_DEBUG_DEFAULT")
    rag_api_retry_count: int = Field(default=2, ge=0, le=10, validation_alias="RAG_API_RETRY_COUNT")

    backend_host: str = Field(default="0.0.0.0", validation_alias="BACKEND_HOST")
    backend_port: int = Field(default=8090, validation_alias="BACKEND_PORT")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    cors_origins: str | None = Field(
        default=None,
        validation_alias="CORS_ORIGINS",
        description="Список origin через запятую для браузерного UI; если пусто — localhost:5173.",
    )

    internal_auth_enabled: bool = Field(
        default=False,
        validation_alias="INTERNAL_AUTH_ENABLED",
        description="Защита /api/v1/internal/* и /internal/ops* общим токеном.",
    )
    internal_auth_token: str | None = Field(
        default=None,
        validation_alias="INTERNAL_AUTH_TOKEN",
        description="Секрет для X-Internal-Token или Authorization: Bearer.",
    )

    operator_ui_dist: str | None = Field(
        default=None,
        validation_alias="OPERATOR_UI_DIST",
        description="Путь к frontend/dist для раздачи под /operator (опционально).",
    )

    ui_require_auth: bool = Field(
        default=False,
        validation_alias="UI_REQUIRE_AUTH",
        description="Подсказка для ops: фронт ожидает VITE_UI_REQUIRE_AUTH (сам backend не гейтит UI).",
    )

    database_url: str | None = Field(
        default=None,
        validation_alias="DATABASE_URL",
        description="PostgreSQL для ai_calls / ai_feedback; если не задан — история не пишется.",
    )

    alert_webhook_url: str | None = Field(
        default=None,
        validation_alias="ALERT_WEBHOOK_URL",
        description="HTTPS URL для JSON POST при high-priority алерте (тело: text, source, severity).",
    )
    alert_telegram_bot_token: str | None = Field(
        default=None,
        validation_alias="ALERT_TELEGRAM_BOT_TOKEN",
    )
    alert_telegram_chat_id: str | None = Field(
        default=None,
        validation_alias="ALERT_TELEGRAM_CHAT_ID",
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def _empty_database_url(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
