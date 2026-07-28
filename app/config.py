from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    port: int = 8080
    seed_api_key: str = ""          # pre-seeded key value (e.g. sk_dev)
    seed_api_key_name: str = "default"
    seed_api_key_capacity: int = 100
    seed_api_key_refill_rate: float = 10.0

    class Config:
        env_file = ".env"


settings = Settings()
