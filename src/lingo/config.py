from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LINGO_", env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://lingo:lingo@localhost:5432/lingo"

    # Auth
    dev_mode: bool = False
    secret_key: str = "change-me-in-production"

    # Slack
    slack_bot_token: str = ""
    slack_app_token: str = ""
    slack_signing_secret: str = ""
    slack_client_id: str = ""
    slack_client_secret: str = ""

    # MCP
    mcp_bearer_token: str = ""

    # Voting thresholds
    community_threshold: int = 3
    official_threshold: int = 10

    # Staleness
    stale_threshold_days: int = 180

    # App
    app_url: str = "http://localhost:8000"

    # Feature flags — set via env vars, e.g. LINGO_FEATURE_VOTING=false
    # Defaults to a simple experience suitable for small teams.
    feature_discovery: bool = False  # Slack auto-discovery job
    feature_relationships: bool = False  # Term relationship linking
    feature_voting: bool = True  # Voting & status pipeline
    feature_staleness: bool = False  # Staleness checks & notifications

    @model_validator(mode="after")
    def check_secret_key(self):
        if not self.dev_mode and self.secret_key == "change-me-in-production":
            raise ValueError(
                "LINGO_SECRET_KEY must be set to a random value in production. "
                "Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'"
            )
        return self


settings = Settings()
