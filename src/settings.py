from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_url: str
    api_token: str
    auth_api_url: str
    jwt_secret: str
    server_port: int
    frontend_url: str

    model_config = {"env_file": ".env", "extra": "allow"}


settings = Settings()  # type: ignore[call-arg]
