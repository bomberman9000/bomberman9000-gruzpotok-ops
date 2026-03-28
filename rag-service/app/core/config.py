from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    postgres_dsn: str = Field(
        default="postgresql://ollama_app:changeme@localhost:5432/ollama_app",
        validation_alias=AliasChoices("DATABASE_URL", "POSTGRES_DSN"),
    )
    redis_url: str | None = Field(default=None, validation_alias="REDIS_URL")

    ollama_base_url: str = Field(
        default="http://host.docker.internal:11434",
        validation_alias="OLLAMA_BASE_URL",
    )

    ollama_model: str = Field(default="llama3:8b", validation_alias="OLLAMA_MODEL")
    ollama_chat_model: str | None = Field(default=None, validation_alias="OLLAMA_CHAT_MODEL")

    embedding_model: str = Field(
        default="nomic-embed-text",
        validation_alias="EMBEDDING_MODEL",
    )

    embedding_dimensions: int = Field(default=768, validation_alias="EMBEDDING_DIMENSIONS")

    ollama_num_ctx: int = Field(
        default=8192,
        ge=512,
        le=131072,
        validation_alias="OLLAMA_NUM_CTX",
        description="Размер контекста для /api/chat (options.num_ctx); совместимо с Modelfile.",
    )
    ollama_temperature: float | None = Field(
        default=None,
        validation_alias="OLLAMA_TEMPERATURE",
        description="Если задано — передаётся в options.temperature и переопределяет дефолт модели.",
    )

    rag_top_k: int = Field(default=12, validation_alias="RAG_TOP_K")
    rag_final_k: int = Field(default=6, validation_alias="RAG_FINAL_K")
    rag_mode_default: Literal["balanced", "strict", "draft"] = Field(
        default="balanced",
        validation_alias="RAG_MODE_DEFAULT",
    )

    rerank_alpha: float = Field(default=0.65, validation_alias="RERANK_ALPHA")
    rerank_beta: float = Field(default=0.25, validation_alias="RERANK_BETA")
    rerank_gamma: float = Field(default=0.1, validation_alias="RERANK_GAMMA")

    strict_min_rerank_score: float = Field(
        default=0.22,
        validation_alias="STRICT_MIN_RERANK_SCORE",
    )
    strict_max_vector_distance: float = Field(
        default=0.55,
        validation_alias="STRICT_MAX_VECTOR_DISTANCE",
    )

    strict_min_chunks: int = Field(
        default=1,
        ge=0,
        le=50,
        validation_alias="STRICT_MIN_CHUNKS",
        description="В режиме strict не вызывать LLM, если релевантных чанков меньше порога (после rerank).",
    )

    knowledge_dir: str = Field(default="/app/data/knowledge", validation_alias="KNOWLEDGE_DIR")

    libreoffice_soffice_path: str | None = Field(
        default=None,
        validation_alias="LIBREOFFICE_SOFFICE_PATH",
        description="Полный путь к soffice (LibreOffice) для pdf_engine=libreoffice; иначе поиск в PATH и стандартные пути Windows.",
    )
    libreoffice_convert_timeout_sec: float = Field(
        default=90.0,
        ge=5.0,
        le=600.0,
        validation_alias="LIBREOFFICE_CONVERT_TIMEOUT_SEC",
        description="Таймаут subprocess для soffice --convert-to pdf (секунды).",
    )

    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_json: bool = Field(default=False, validation_alias="LOG_JSON")

    @model_validator(mode="after")
    def legacy_env(self) -> "Settings":
        import os

        if os.environ.get("OLLAMA_BASE"):
            self.ollama_base_url = os.environ["OLLAMA_BASE"]
        if os.environ.get("EMBED_MODEL"):
            self.embedding_model = os.environ["EMBED_MODEL"]
        if os.environ.get("OLLAMA_CHAT_MODEL"):
            self.ollama_chat_model = os.environ["OLLAMA_CHAT_MODEL"]
        return self

    @property
    def chat_model(self) -> str:
        return self.ollama_chat_model or self.ollama_model


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
