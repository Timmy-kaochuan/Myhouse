"""设计算例表：一次重型燃机设计优化任务的顶层容器。"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONField, utc_now

# 算例状态常量
CASE_STATUS_DRAFT = "draft"
CASE_STATUS_RUNNING = "running"
CASE_STATUS_FINISHED = "finished"
CASE_STATUS_ARCHIVED = "archived"


class DesignCase(Base):
    """设计算例。"""

    __tablename__ = "design_cases"
    __table_args__ = {"comment": "设计算例表"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键")
    case_name: Mapped[str] = mapped_column(
        String(200), index=True, nullable=False, comment="算例名称"
    )
    case_version: Mapped[str] = mapped_column(
        String(50), default="v1", server_default="v1", nullable=False, comment="算例版本"
    )
    description: Mapped[str | None] = mapped_column(Text, default=None, comment="算例描述")
    design_parameters: Mapped[dict | None] = mapped_column(
        JSONField,
        default=None,
        comment="设计参数(JSON)：如压比、流量、涡轮进口温度等设计变量向量",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=CASE_STATUS_DRAFT,
        server_default=CASE_STATUS_DRAFT,
        nullable=False,
        comment="状态: draft/running/finished/archived",
    )
    creator_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="创建人ID -> users.id",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, comment="创建时间(UTC)"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
        comment="更新时间(UTC)，ORM 自动维护",
    )

    # 多对一
    creator: Mapped["User"] = relationship(back_populates="design_cases")

    # design_case -> cfd_task / agent_run 一对多：删除算例级联删除子记录
    cfd_tasks: Mapped[list["CfdTask"]] = relationship(
        back_populates="design_case",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    agent_runs: Mapped[list["AgentRun"]] = relationship(
        back_populates="design_case",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
