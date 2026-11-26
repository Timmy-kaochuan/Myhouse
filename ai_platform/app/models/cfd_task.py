"""CFD 迭代计算任务表：归属算例版本，可引用上游产物作为输入。"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONField, utc_now

# 任务状态常量
TASK_STATUS_PENDING = "pending"
TASK_STATUS_RUNNING = "running"
TASK_STATUS_SUCCESS = "success"
TASK_STATUS_FAILED = "failed"
TASK_STATUS_STOP = "stop"


class CfdTask(Base):
    """CFD 迭代任务（网格/结果文件只存 MinIO 对象 key）。"""

    __tablename__ = "cfd_tasks"
    __table_args__ = {"comment": "CFD 迭代计算任务表"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键")
    case_version_id: Mapped[int] = mapped_column(
        ForeignKey("case_versions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="所属算例版本ID -> case_versions.id",
    )
    input_artifact_id: Mapped[int | None] = mapped_column(
        ForeignKey("case_artifacts.id", ondelete="SET NULL"),
        index=True,
        default=None,
        comment="上游产物ID(输入来源) -> case_artifacts.id，可空",
    )
    task_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="任务名称")
    task_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="任务类型，如 flow/combustion/heat/cooling"
    )
    input_params: Mapped[dict | None] = mapped_column(
        JSONField, default=None, comment="CFD 输入参数(JSON)：边界条件、物性、工况等"
    )
    output_result: Mapped[dict | None] = mapped_column(
        JSONField, default=None, comment="CFD 输出结果(JSON)：效率、流量、温升等响应量"
    )
    max_iter: Mapped[int] = mapped_column(
        default=100, server_default="100", nullable=False, comment="最大迭代步数"
    )
    current_iter: Mapped[int] = mapped_column(
        default=0, server_default="0", nullable=False, comment="当前迭代步数"
    )
    converge_criteria: Mapped[dict | None] = mapped_column(
        JSONField, default=None, comment="收敛判据(JSON)：残差阈值、波动限等"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=TASK_STATUS_PENDING,
        server_default=TASK_STATUS_PENDING,
        nullable=False,
        comment="状态: pending/running/success/failed/stop",
    )
    error_msg: Mapped[str | None] = mapped_column(Text, default=None, comment="失败原因")
    mesh_file_key: Mapped[str | None] = mapped_column(
        String(500), default=None, comment="MinIO 网格文件对象key，二进制不入库"
    )
    result_file_key: Mapped[str | None] = mapped_column(
        String(500), default=None, comment="MinIO 结果文件对象key，二进制不入库"
    )
    proxy_model_id: Mapped[int | None] = mapped_column(
        ForeignKey("proxy_models.id", ondelete="SET NULL"),
        index=True,
        default=None,
        comment="关联代理模型ID(初场/自适应采样来源) -> proxy_models.id，可空",
    )
    celery_task_id: Mapped[str | None] = mapped_column(
        String(100), index=True, default=None, comment="Celery 异步任务ID"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, comment="开始时间(UTC)"
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, comment="结束时间(UTC)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, comment="创建时间(UTC)"
    )

    # 多对一
    case_version: Mapped["CaseVersion"] = relationship(back_populates="cfd_tasks")
    input_artifact: Mapped["CaseArtifact | None"] = relationship()
    proxy_model: Mapped["ProxyModel | None"] = relationship(back_populates="cfd_tasks")

    # cfd_task -> experiment_record 一对多：删除任务级联删除实验记录
    experiment_records: Mapped[list["ExperimentRecord"]] = relationship(
        back_populates="cfd_task",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
