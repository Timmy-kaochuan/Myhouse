"""代理模型表：克里金 / 高斯过程 / MLP / 多保真自适应采样。"""
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONField, utc_now

# 模型类型常量（mf_adaptive = 多保真自适应采样）
MODEL_TYPE_KRIGING = "kriging"
MODEL_TYPE_GP = "gp"
MODEL_TYPE_MLP = "mlp"
MODEL_TYPE_MF_ADAPTIVE = "mf_adaptive"

# 模型状态常量
PM_STATUS_DRAFT = "draft"
PM_STATUS_TRAINING = "training"
PM_STATUS_READY = "ready"
PM_STATUS_FAILED = "failed"


class ProxyModel(Base):
    """代理模型（数据与权重文件只存 MinIO 对象 key）。"""

    __tablename__ = "proxy_models"
    __table_args__ = {"comment": "代理模型表(克里金/GP/MLP/多保真自适应采样)"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键")
    model_name: Mapped[str] = mapped_column(
        String(200), index=True, nullable=False, comment="模型名称"
    )
    model_version: Mapped[str] = mapped_column(
        String(50), default="v1", server_default="v1", nullable=False, comment="模型版本"
    )
    model_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="模型类型: kriging/gp/mlp/mf_adaptive(多保真自适应采样)"
    )
    input_dim: Mapped[int] = mapped_column(nullable=False, comment="输入变量维度")
    output_dim: Mapped[int] = mapped_column(nullable=False, comment="输出响应维度")
    metric: Mapped[dict | None] = mapped_column(
        JSONField, default=None, comment="精度指标(JSON)：RMSE/R2/MAE 等"
    )
    weight_key: Mapped[str | None] = mapped_column(
        String(500), default=None, comment="MinIO 模型权重文件对象key，二进制不入库"
    )
    train_dataset_key: Mapped[str | None] = mapped_column(
        String(500), default=None, comment="MinIO 训练数据集文件对象key，二进制不入库"
    )
    description: Mapped[str | None] = mapped_column(Text, default=None, comment="模型说明")
    status: Mapped[str] = mapped_column(
        String(20),
        default=PM_STATUS_DRAFT,
        server_default=PM_STATUS_DRAFT,
        nullable=False,
        comment="状态: draft/training/ready/failed",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, comment="创建时间(UTC)"
    )

    # proxy_model -> cfd_task 一对多：删除代理模型时 CFD 任务保留，引用置空(SET NULL)
    cfd_tasks: Mapped[list["CfdTask"]] = relationship(
        back_populates="proxy_model",
        passive_deletes=True,
    )
