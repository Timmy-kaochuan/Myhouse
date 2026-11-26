"""保真样本实验记录表：仿真/试验样本与代理模型预测对比。

数据来源分两类：
- sim：CFD 仿真结果（低保真），必须挂在某个 CFD 任务下；
- test：试验测量结果（高保真），不挂 CFD 任务，登记原始试验数据文件 key。
weight 为该样本的训练权重（可空，空则由训练器按 sample_tag 默认策略处理）。
"""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONField, utc_now

# 样本保真度常量
SAMPLE_HIGH_FID = "high_fid"
SAMPLE_LOW_FID = "low_fid"

# 数据来源常量
SOURCE_SIM = "sim"
SOURCE_TEST = "test"


class ExperimentRecord(Base):
    """一条保真样本：来源 + 输入向量 + 真实输出 + 代理模型预测输出。"""

    __tablename__ = "experiment_records"
    __table_args__ = {"comment": "保真样本实验记录表(仿真/试验样本、权重与预测残差)"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键")
    cfd_task_id: Mapped[int | None] = mapped_column(
        ForeignKey("cfd_tasks.id", ondelete="CASCADE"),
        index=True,
        default=None,
        comment="所属CFD任务ID -> cfd_tasks.id；来源为仿真时必填，试验时可空",
    )
    source: Mapped[str] = mapped_column(
        String(20),
        default=SOURCE_SIM,
        server_default=SOURCE_SIM,
        nullable=False,
        comment="数据来源: sim(仿真低保真)/test(试验高保真)",
    )
    sample_tag: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="样本保真度: high_fid/low_fid"
    )
    weight: Mapped[float | None] = mapped_column(
        Float, default=None, comment="训练权重(≥0)；空则由训练器按 sample_tag 默认策略处理，试验样本通常更大"
    )
    test_data_key: Mapped[str | None] = mapped_column(
        String(500), default=None, comment="MinIO 原始试验数据文件key；来源为试验时登记，二进制不入库"
    )
    input_x: Mapped[dict | list | None] = mapped_column(
        JSONField, default=None, comment="输入样本向量(JSON 数组)：设计变量/工况取值"
    )
    output_y_true: Mapped[dict | list | None] = mapped_column(
        JSONField, default=None, comment="真实输出向量(JSON)：仿真计算或试验测量结果"
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

    # 多对一（试验记录 cfd_task_id 为空）
    cfd_task: Mapped["CfdTask | None"] = relationship(back_populates="experiment_records")
