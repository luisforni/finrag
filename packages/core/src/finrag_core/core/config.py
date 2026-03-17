from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "FinRAG"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    secret_key: str = Field(min_length=32)
    access_token_expire_minutes: int = 30
    algorithm: str = "HS256"

    database_url: PostgresDsn
    db_pool_size: int = 20
    db_max_overflow: int = 10

    redis_url: str = "redis://localhost:6379/0"

    s3_bucket_name: str
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    use_secrets_manager: bool = False
    secrets_manager_secret_name: str = ""

    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_max_retries: int = 3

    chroma_host: str = "localhost"
    chroma_port: int = 8000
    chroma_collection_name: str = "finrag_documents"

    rate_limit_per_minute: int = 60

    chunk_size: int = 1000
    chunk_overlap: int = 200

    retrieval_top_k: int = 5
    embedding_model: str = "text-embedding-3-small"

    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str) -> str:
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
