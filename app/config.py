from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    backend_host: str = "127.0.0.1"
    backend_port: int = 8765
    request_timeout_seconds: int = 120
    max_search_results_per_query: int = 20
    max_candidates_before_ranking: int = 250
    search_region: str = "us-en"
    search_backend: str = "auto"


settings = Settings()
