from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RCS MVP"
    app_env: str = "development"
    rcs_agent_id: str = ""
    rcs_api_region: str = "us"
    google_service_account_file: str = ""
    google_service_account_json: str = ""
    request_timeout_seconds: int = 30
    max_broadcast_recipients: int = 500

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def rcs_base_url(self) -> str:
        region = self.rcs_api_region.strip().lower()
        if region not in {"us", "europe", "asia"}:
            region = "us"
        return f"https://{region}-rcsbusinessmessaging.googleapis.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()
