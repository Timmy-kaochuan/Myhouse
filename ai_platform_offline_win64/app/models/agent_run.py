"""LangGraph 智能体运行记录表。"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONField

# 运行状态常量
RUN_STATUS_PENDING = "pending"
RUN_STATUS_RUNNING = "running"
RUN_STATUS_SUCCESS = "success"
RUN_STATUS_FAILED = "failed"


class AgentRun(Base):
    """一次智能体调用 / 编排运行的完整记录，用于回放与审计。"""

    __tablename__ = "agent_runs"
    __table_args__ = {"comment": "LangGraph 智能体运行记录表"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键")
    case_id: Mapped[int] = mapped_column(
        ForeignKey("design_cases.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="所属设计算例ID -> design_cases.id",
    )
    agent_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="智能体名称，如 mdo-scheduler/cfd-agent/proxy-agent"
    )
    thread_id: Mapped[str | None] = mapped_column(
        String(100),
        index=True,
        default=None,
        comment="LangGraph thread_id，用于断点续跑与状态恢复",
    )
    input_query: Mapped[str | None] = mapped_column(
        Text, default=None, comment="用户输入的自然语言任务"
    )
    state_snapshot: Mapped[dict | None] = mapped_column(
        JSONField, default=None, comment="LangGraph 状态快照(JSON)"
    )
    trace_log: Mapped[dict | None] = mapped_column(
        JSONField, default=None, comment="执行 trace 日志(JSON)：节点调用、工具调用链路"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=RUN_STATUS_PENDING,
        server_default=RUN_STATUS_PENDING,
        nullable=False,
        comment="状态: pending/running/success/failed",
    )
    error_msg: Mapped[str | None] = mapped_column(Text, default=None, comment="失败原因")
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, comment="开始时间(UTC)"
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, comment="结束时间(UTC)"
    )

    # 多对一
    design_case: Mapped["DesignCase"] = relationship(back_populates="agent_runs")
