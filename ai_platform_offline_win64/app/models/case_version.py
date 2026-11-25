"""算例版本表：同一算例的不同迭代轮次（参数快照 + 产物容器）。"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONField, utc_now

# 版本状态常量
VERSION_STATUS_DRAFT = "draft"
VERSION_STATUS_RUNNING = "running"
VERSION_STATUS_FINISHED = "finished"
VERSION_STATUS_ARCHIVED = "archived"


class CaseVersion(Base):
    """设计算例版本：具体设计参数与状态挂在版本上，产物与 CFD 任务归属版本。"""

    __tablename__ = "case_versions"
    __table_args__ = (
        UniqueConstraint("case_id", "version_no", name="uq_case_versions_case_version"),
        {"comment": "算例版本表"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键")
    case_id: Mapped[int] = mapped_column(
        ForeignKey("design_cases.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="所属设计算例ID -> design_cases.id",
    )
    version_no: Mapped[str] = mapped_column(
        String(50), default="v1", server_default="v1", nullable=False, comment="版本号，如 v1/v2；同一算例内唯一"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=VERSION_STATUS_DRAFT,
        server_default=VERSION_STATUS_DRAFT,
        nullable=False,
        comment="状态: draft/running/finished/archived",
    )
    design_parameters: Mapped[dict | None] = mapped_column(
        JSONField,
        default=None,
        comment="设计参数(JSON)：如压比、流量、涡轮进口温度等设计变量向量",
    )
    description: Mapped[str | None] = mapped_column(Text, default=None, comment="版本说明")
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
    design_case: Mapped["DesignCase"] = relationship(back_populates="versions")

    # case_version -> case_artifact / cfd_task 一对多：删除版本级联删除子记录
    artifacts: Mapped[list["CaseArtifact"]] = relationship(
        back_populates="case_version",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    cfd_tasks: Mapped[list["CfdTask"]] = relationship(
        back_populates="case_version",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
