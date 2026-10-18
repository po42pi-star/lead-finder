from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.proxyapi.ru/openai/v1", alias="OPENAI_BASE_URL")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL"
    )
    openai_chat_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_CHAT_MODEL")
    openai_embedding_dimensions: int = Field(
        default=1536, alias="OPENAI_EMBEDDING_DIMENSIONS"
    )
    openai_max_retries: int = Field(default=3, alias="OPENAI_MAX_RETRIES")
    openai_retry_base_delay_sec: float = Field(
        default=1.0, alias="OPENAI_RETRY_BASE_DELAY_SEC"
    )

    rag_docs_path: Path = Field(default=Path("rag_docs"), alias="RAG_DOCS_PATH")
    chroma_persist_path: Path = Field(
        default=Path("data/chroma"), alias="CHROMA_PERSIST_PATH"
    )
    chroma_collection_name: str = Field(
        default="nevatom_kb_v1", alias="CHROMA_COLLECTION_NAME"
    )

    chunk_max_tokens: int = Field(default=900, alias="CHUNK_MAX_TOKENS")
    chunk_overlap_tokens: int = Field(default=120, alias="CHUNK_OVERLAP_TOKENS")
    chunk_batch_size: int = Field(default=32, alias="CHUNK_BATCH_SIZE")

    retrieval_top_k: int = Field(default=4, alias="RETRIEVAL_TOP_K")
    similarity_score_threshold: float = Field(
        default=0.35, alias="SIMILARITY_SCORE_THRESHOLD"
    )
    max_context_tokens: int = Field(default=4000, alias="MAX_CONTEXT_TOKENS")
    intent_cache_ttl_sec: int = Field(default=300, alias="INTENT_CACHE_TTL_SEC")
    intent_use_llm: bool = Field(default=False, alias="INTENT_USE_LLM")

    lru_cache_maxsize: int = Field(default=256, alias="LRU_CACHE_MAXSIZE")
    disk_cache_path: Path = Field(default=Path("data/diskcache"), alias="DISK_CACHE_PATH")
    disk_cache_ttl_faq_hours: int = Field(default=24, alias="DISK_CACHE_TTL_FAQ_HOURS")
    disk_cache_ttl_technical_hours: int = Field(
        default=4, alias="DISK_CACHE_TTL_TECHNICAL_HOURS"
    )

    analytics_db_path: Path = Field(
        default=Path("data/analytics.db"), alias="ANALYTICS_DB_PATH"
    )

    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ORIGINS",
    )

    database_url: str = Field(
        default="sqlite+aiosqlite:///data/app.db",
        alias="DATABASE_URL",
    )

    search_page_size: int = Field(default=20, alias="SEARCH_PAGE_SIZE")
    search_max_results: int = Field(default=500, alias="SEARCH_MAX_RESULTS")
    search_http_timeout_sec: float = Field(default=30.0, alias="SEARCH_HTTP_TIMEOUT_SEC")
    search_http_retry_attempts: int = Field(default=3, alias="SEARCH_HTTP_RETRY_ATTEMPTS")
    search_request_delay_sec: float = Field(default=1.0, alias="SEARCH_REQUEST_DELAY_SEC")

    score_okved_match: int = Field(default=20, alias="SCORE_OKVED_MATCH")
    score_tenders_12m: int = Field(default=15, alias="SCORE_TENDERS_12M")
    score_active_website: int = Field(default=10, alias="SCORE_ACTIVE_WEBSITE")
    score_revenue_50m: int = Field(default=10, alias="SCORE_REVENUE_50M")
    score_revenue_200m: int = Field(default=5, alias="SCORE_REVENUE_200M")
    score_sro: int = Field(default=10, alias="SCORE_SRO")
    score_ventilation_mention: int = Field(default=10, alias="SCORE_VENTILATION_MENTION")
    score_lpr_missing_penalty: int = Field(default=10, alias="SCORE_LPR_MISSING_PENALTY")
    score_no_vent_penalty: int = Field(default=7, alias="SCORE_NO_VENT_PENALTY")
    score_region_match: int = Field(default=15, alias="SCORE_REGION_MATCH")
    score_company_age_2y: int = Field(default=5, alias="SCORE_COMPANY_AGE_2Y")

    zakupki_api_base_url: str = Field(
        default="https://zakupki.gov.ru",
        alias="ZAKUPKI_API_BASE_URL",
    )
    zakupki_rss_path: str = Field(
        default="/epz/order/extendedsearch/rss.html",
        alias="ZAKUPKI_RSS_PATH",
    )
    zakupki_open_api_url: str = Field(
        default="",
        alias="ZAKUPKI_OPEN_API_URL",
    )
    zakupki_open_api_key: str = Field(default="", alias="ZAKUPKI_OPEN_API_KEY")
    fns_egrul_base_url: str = Field(
        default="https://egrul.nalog.ru",
        alias="FNS_EGRUL_BASE_URL",
    )
    registry_abok_url: str = Field(
        default="https://abok.ru",
        alias="REGISTRY_ABOK_URL",
    )
    dgis_api_key: str = Field(default="", alias="DGIS_API_KEY")
    dgis_base_url: str = Field(
        default="https://catalog.api.2gis.com",
        alias="DGIS_BASE_URL",
    )
    dadata_api_key: str = Field(default="", alias="DADATA_API_KEY")
    dadata_secret_key: str = Field(default="", alias="DADATA_SECRET_KEY")
    dadata_base_url: str = Field(default="https://suggestions.dadata.ru/suggestions-api", alias="DADATA_BASE_URL")
    search_use_live_sources: bool = Field(
        default=True,
        alias="SEARCH_USE_LIVE_SOURCES",
    )

    analytics_batch_max: int = Field(default=5, alias="ANALYTICS_BATCH_MAX")
    analytics_questions_count: int = Field(default=10, alias="ANALYTICS_QUESTIONS_COUNT")

    chat_session_ttl_sec: int = Field(default=1800, alias="CHAT_SESSION_TTL_SEC")
    chat_max_query_length: int = Field(default=500, alias="CHAT_MAX_QUERY_LENGTH")
    chat_fallback_score_threshold: float = Field(
        default=0.5, alias="CHAT_FALLBACK_SCORE_THRESHOLD"
    )
    chat_rate_limit_per_day: int = Field(default=200, alias="CHAT_RATE_LIMIT_PER_DAY")
    chat_stream_enabled: bool = Field(default=True, alias="CHAT_STREAM_ENABLED")
    rop_contact_email: str = Field(default="", alias="ROP_CONTACT_EMAIL")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def disk_cache_ttl_faq_sec(self) -> int:
        return self.disk_cache_ttl_faq_hours * 3600

    @property
    def disk_cache_ttl_technical_sec(self) -> int:
        return self.disk_cache_ttl_technical_hours * 3600


@lru_cache
def get_settings() -> Settings:
    return Settings()
