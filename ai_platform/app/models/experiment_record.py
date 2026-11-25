"""保真样本实验记录表：CFD 高/低保真样本与代理模型预测对比。"""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONField, utc_now

# 样本保真度常量
SAMPLE_HIGH_FID = "high_fid"
SAMPLE_LOW_FID = "low_fid"


class ExperimentRecord(Base):
    """一条保真样本：输入向量 + 真实输出 + 代理模型预测输出。"""

    __tablename__ = "experiment_records"
    __table_args__ = {"comment": "保真样本实验记录表(高/低保真样本与预测残差)"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键")
    cfd_task_id: Mapped[int] = mapped_column(
        ForeignKey("cfd_tasks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="所属CFD任务ID -> cfd_tasks.id",
    )
    sample_tag: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="样本保真度: high_fid/low_fid"
    )
    input_x: Mapped[dict | list | None] = mapped_column(
        JSONField, default=None, comment="输入样本向量(JSON 数组)：设计变量取值"
    )
    output_y_true: Mapped[dict | list | None] = mapped_column(
        JSONField, default=None, comment="真实输出向量(JSON)：CFD 计算结果"
    )
    output_y_pred: Mapped[dict | list | None] = mapped_column(
        JSONField, default=None, comment="代理模型预测输出向量(JSON)"
    )
    residual: Mapped[float | None] = mapped_column(
        Float, default=None, comment="预测残差 |y_true - y_pred|"
    )
    mlflow_run_id: Mapped[str | None] = mapped_column(
        String(64), index=True, default=None, comment="MLflow 实验 run_id"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, comment="创建时间(UTC)"
    )

    # 多对一
    cfd_task: Mapped["CfdTask"] = relationship(back_populates="experiment_records")
