from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    api_url: str
    api_token: str
    auth_api_url: str
    jwt_secret: str
    server_port: int
    frontend_url: str
    stats_api_url: str | None = None
    stats_api_token: str | None = None
    hashrate_poll_interval_seconds: float = Field(default=30, gt=0)

    model_config = {"env_file": ".env", "extra": "allow"}


settings = Settings()  # type: ignore[call-arg]
