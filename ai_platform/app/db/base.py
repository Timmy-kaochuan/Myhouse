"""ORM 基类与通用类型定义（SQLite 开发 / PostgreSQL 生产 双兼容）。"""
from datetime import datetime, timezone

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase

# JSON 字段类型：开发环境 SQLite 用 JSON，生产 PostgreSQL 自动切换为 JSONB（可索引、查询更快）
JSONField = JSON().with_variant(JSONB(), "postgresql")


def utc_now() -> datetime:
    """统一 UTC 时间戳。Python 侧生成，保证 SQLite / PostgreSQL 行为一致。"""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""
