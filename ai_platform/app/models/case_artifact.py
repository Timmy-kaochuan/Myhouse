"""算例产物表：某版本产出/登记的文件（二进制存 MinIO，库内只存对象 key）。"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now

# 产物类型常量
ARTIFACT_TYPE_MESH = "mesh"
ARTIFACT_TYPE_RESULT = "result"
ARTIFACT_TYPE_WEIGHT = "weight"
ARTIFACT_TYPE_DATASET = "dataset"
ARTIFACT_TYPE_OTHER = "other"


class CaseArtifact(Base):
    """算例产物：网格/结果/权重/数据集等文件的 MinIO 对象登记。"""

    __tablename__ = "case_artifacts"
    __table_args__ = {"comment": "算例产物登记表"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键")
    case_version_id: Mapped[int] = mapped_column(
        ForeignKey("case_versions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="所属算例版本ID -> case_versions.id",
    )
    artifact_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="产物类型: mesh/result/weight/dataset/other"
    )
    file_key: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="MinIO 对象key，约定 cases/{算例}/{版本}/outputs/..."
    )
    description: Mapped[str | None] = mapped_column(Text, default=None, comment="产物说明")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, comment="创建时间(UTC)"
    )

    # 多对一
    case_version: Mapped["CaseVersion"] = relationship(back_populates="artifacts")
