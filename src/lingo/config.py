from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LINGO_", env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://lingo:lingo@localhost:5432/lingo"

    # Auth
    dev_mode: bool = False
    secret_key: str = "change-me-in-production"
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_discovery_url: str = ""

    # Slack
    slack_bot_token: str = ""
    slack_app_token: str = ""
    slack_signing_secret: str = ""

    # MCP
    mcp_bearer_token: str = ""

    # Voting thresholds
    community_threshold: int = 3
    official_threshold: int = 10

    # Staleness
    stale_threshold_days: int = 180

    # App
    app_url: str = "http://localhost:8000"


settings = Settings()
