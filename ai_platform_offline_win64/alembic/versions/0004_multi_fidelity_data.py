"""multi-fidelity training data: source/weight/test_data_key + inline weights_json

- experiment_records 重建：cfd_task_id 改可空（试验数据不挂任务），新增
  source(sim/test) / weight(样本权重) / test_data_key(原始试验数据文件key)
- proxy_models 新增 weights_json（内嵌小权重，供 /predict 端到端推理）

存量迁移：旧记录全部视为仿真来源(source=sim)，weight/test_data_key 置空。

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-26

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 与 app/db/base.py 的 JSONField 保持一致：SQLite 用 JSON，PostgreSQL 用 JSONB
JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    # 1. experiment_records 重建：cfd_task_id 可空 + 新增 source/weight/test_data_key
    op.create_table(
        "experiment_records_new",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False, comment="主键"),
        sa.Column("cfd_task_id", sa.Integer(), nullable=True, comment="所属CFD任务ID -> cfd_tasks.id；来源为仿真时必填，试验时可空"),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="sim", comment="数据来源: sim(仿真低保真)/test(试验高保真)"),
        sa.Column("sample_tag", sa.String(length=20), nullable=False, comment="样本保真度: high_fid/low_fid"),
        sa.Column("weight", sa.Float(), nullable=True, comment="训练权重(≥0)；空则由训练器按 sample_tag 默认策略处理"),
        sa.Column("test_data_key", sa.String(length=500), nullable=True, comment="MinIO 原始试验数据文件key；来源为试验时登记"),
        sa.Column("input_x", JSON_TYPE, nullable=True, comment="输入样本向量(JSON 数组)"),
        sa.Column("output_y_true", JSON_TYPE, nullable=True, comment="真实输出向量(JSON)"),
        sa.Column("output_y_pred", JSON_TYPE, nullable=True, comment="代理模型预测输出向量(JSON)"),
        sa.Column("residual", sa.Float(), nullable=True, comment="预测残差"),
        sa.Column("mlflow_run_id", sa.String(length=64), nullable=True, comment="MLflow run_id"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间(UTC)"),
        sa.ForeignKeyConstraint(["cfd_task_id"], ["cfd_tasks.id"], ondelete="CASCADE"),
        comment="保真样本实验记录表(仿真/试验样本、权重与预测残差)",
    )
    op.execute(
        "INSERT INTO experiment_records_new (id, cfd_task_id, source, sample_tag, weight, test_data_key, "
        "input_x, output_y_true, output_y_pred, residual, mlflow_run_id, created_at) "
        "SELECT id, cfd_task_id, 'sim', sample_tag, NULL, NULL, "
        "input_x, output_y_true, output_y_pred, residual, mlflow_run_id, created_at "
        "FROM experiment_records"
    )
    op.drop_table("experiment_records")
    op.rename_table("experiment_records_new", "experiment_records")
    op.create_index("ix_experiment_records_cfd_task_id", "experiment_records", ["cfd_task_id"])
    op.create_index("ix_experiment_records_mlflow_run_id", "experiment_records", ["mlflow_run_id"])

    # 2. proxy_models 新增内嵌权重 weights_json（无外键，batch 加列安全）
    with op.batch_alter_table("proxy_models") as batch:
        batch.add_column(
            sa.Column(
                "weights_json",
                JSON_TYPE,
                nullable=True,
                comment="内嵌小权重(JSON)：如 {type: linear, coef: [...], intercept: 0}，供 /predict 直接推理",
            )
        )


def downgrade() -> None:
    """尽力回滚：删除试验来源记录（旧结构无法容纳无任务的样本）。"""
    # 1. proxy_models 去掉 weights_json
    with op.batch_alter_table("proxy_models") as batch:
        batch.drop_column("weights_json")

    # 2. experiment_records 退回旧结构（cfd_task_id NOT NULL，无 source/weight/test_data_key）
    op.execute("DELETE FROM experiment_records WHERE cfd_task_id IS NULL")
    op.create_table(
        "experiment_records_old",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("cfd_task_id", sa.Integer(), nullable=False),
        sa.Column("sample_tag", sa.String(length=20), nullable=False),
        sa.Column("input_x", JSON_TYPE),
        sa.Column("output_y_true", JSON_TYPE),
        sa.Column("output_y_pred", JSON_TYPE),
        sa.Column("residual", sa.Float()),
        sa.Column("mlflow_run_id", sa.String(length=64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["cfd_task_id"], ["cfd_tasks.id"], ondelete="CASCADE"),
    )
    op.execute(
        "INSERT INTO experiment_records_old (id, cfd_task_id, sample_tag, input_x, output_y_true, "
        "output_y_pred, residual, mlflow_run_id, created_at) "
        "SELECT id, cfd_task_id, sample_tag, input_x, output_y_true, output_y_pred, residual, "
        "mlflow_run_id, created_at FROM experiment_records"
    )
    op.drop_table("experiment_records")
    op.rename_table("experiment_records_old", "experiment_records")
    op.create_index("ix_experiment_records_cfd_task_id", "experiment_records", ["cfd_task_id"])
    op.create_index("ix_experiment_records_mlflow_run_id", "experiment_records", ["mlflow_run_id"])
