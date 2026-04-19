from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "CampusHelpATW API"
    app_env: str = "dev"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "mysql+aiomysql://root:root@127.0.0.1:3306/campus_help_atw"

    jwt_secret_key: str = "change-this-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    dev_verify_code: str = "123456"

    default_help_reward: int = 3
    default_honor_reward: int = 2
    default_confirm_honor_reward: int = 1
    task_publish_help_cost: int = 1

    task_publish_rate_limit_count: int = 5
    task_publish_rate_limit_window_seconds: int = 60
    post_publish_rate_limit_count: int = 8
    post_publish_rate_limit_window_seconds: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
