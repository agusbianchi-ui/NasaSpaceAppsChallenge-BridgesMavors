import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:4173,http://127.0.0.1:4173"
)


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseModel):
    """Application configuration loaded from environment variables."""

    app_name: str = "MARS OPS API"
    app_version: str = "1.0.0"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=list)
    nasa_request_timeout_seconds: float = Field(default=20.0, gt=0)

    @classmethod
    def from_env(cls) -> "Settings":
        cors_origins = _parse_csv(
            os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
        )
        return cls(
            app_name=os.getenv("APP_NAME", "MARS OPS API"),
            app_version=os.getenv("APP_VERSION", "1.0.0"),
            api_v1_prefix=os.getenv("API_V1_PREFIX", "/api/v1"),
            cors_origins=cors_origins,
            nasa_request_timeout_seconds=float(
                os.getenv("NASA_REQUEST_TIMEOUT_SECONDS", "20")
            ),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
