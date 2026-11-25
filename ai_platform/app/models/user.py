"""用户表：平台账号，角色 admin/engineer/viewer。"""
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now

# 角色常量
ROLE_ADMIN = "admin"
ROLE_ENGINEER = "engineer"
ROLE_VIEWER = "viewer"


class User(Base):
    """平台用户。"""

    __tablename__ = "users"
    __table_args__ = {"comment": "平台用户表"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键")
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False, comment="邮箱，全局唯一"
    )
    display_name: Mapped[str | None] = mapped_column(
        String(100), default=None, comment="显示名称"
    )
    role: Mapped[str] = mapped_column(
        String(20),
        default=ROLE_VIEWER,
        server_default=ROLE_VIEWER,
        nullable=False,
        comment="角色: admin/engineer/viewer",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, comment="创建时间(UTC)"
    )

    # user -> design_case 一对多：删除用户级联删除其算例
    design_cases: Mapped[list["DesignCase"]] = relationship(
        back_populates="creator",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
