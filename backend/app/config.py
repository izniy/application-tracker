from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    database_url: str = "sqlite:///./orbit.db"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/email/oauth/callback"

    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    adzuna_country: str = "sg"

    daily_email_scan_hour: int = 8
    daily_job_scan_hour: int = 7

    frontend_origin: str = "http://localhost:5173"


settings = Settings()
