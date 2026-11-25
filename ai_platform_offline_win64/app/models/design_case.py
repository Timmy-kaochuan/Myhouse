"""设计算例主档表：一次设计优化任务的顶层容器。

主档只管"身份"（名称/描述/归属），具体设计参数与运行状态
下沉到 case_versions 版本表；CFD 任务与产物归属版本。
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class DesignCase(Base):
    """设计算例主档（版本化后的顶层容器）。"""

    __tablename__ = "design_cases"
    __table_args__ = {"comment": "设计算例主档表"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键")
    case_name: Mapped[str] = mapped_column(
        String(200), index=True, nullable=False, comment="算例名称"
    )
    description: Mapped[str | None] = mapped_column(Text, default=None, comment="算例描述")
    parent_case_id: Mapped[int | None] = mapped_column(
        ForeignKey("design_cases.id", ondelete="SET NULL"),
        index=True,
        default=None,
        comment="父算例ID(衍生/复制来源) -> design_cases.id，可空",
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

    # design_case -> case_version / agent_run 一对多：删除主档级联删除子记录
    versions: Mapped[list["CaseVersion"]] = relationship(
        back_populates="design_case",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    agent_runs: Mapped[list["AgentRun"]] = relationship(
        back_populates="design_case",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
