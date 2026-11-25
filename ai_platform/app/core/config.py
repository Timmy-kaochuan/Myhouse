import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "AI Platform")
    version: str = "0.1.0"
    # 本地开发默认 SQLite；生产用 POSTGRES 地址，例如：
    # postgresql+asyncpg://user:password@localhost:5432/ai_platform
    database_url: str = os.getenv(
        "DATABASE_URL", "sqlite+aiosqlite:///./ai_platform.db"
    )
    sql_echo: bool = os.getenv("SQL_ECHO", "false").lower() == "true"


settings = Settings()
