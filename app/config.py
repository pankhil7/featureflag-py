from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    port: int = 8080
    api_key: str = "sk_dev"          # valid Bearer token
    rate_limit_capacity: int = 100   # token bucket max tokens
    rate_limit_refill_rate: float = 10.0  # tokens per second

    class Config:
        env_file = ".env"


settings = Settings()
