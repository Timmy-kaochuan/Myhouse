import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "AI Platform")
    version: str = "0.1.0"


settings = Settings()
