"""add platform tables: design_cases, proxy_models, cfd_tasks, agent_runs, experiment_records

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-25

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 与 app/db/base.py 的 JSONField 保持一致：SQLite 用 JSON，PostgreSQL 用 JSONB
JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    # users 表补充角色字段（历史行默认 viewer）
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(length=20),
            nullable=False,
            server_default="viewer",
            comment="角色: admin/engineer/viewer",
        ),
    )

    op.create_table(
        "design_cases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False, comment="主键"),
        sa.Column("case_name", sa.String(length=200), nullable=False, comment="算例名称"),
        sa.Column("case_version", sa.String(length=50), nullable=False, server_default="v1", comment="算例版本"),
        sa.Column("description", sa.Text(), nullable=True, comment="算例描述"),
        sa.Column("design_parameters", JSON_TYPE, nullable=True, comment="设计参数(JSON)"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft", comment="状态: draft/running/finished/archived"),
        sa.Column("creator_id", sa.Integer(), nullable=False, comment="创建人ID -> users.id"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间(UTC)"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, comment="更新时间(UTC)"),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="CASCADE"),
        comment="设计算例表",
    )
    op.create_index("ix_design_cases_case_name", "design_cases", ["case_name"])
    op.create_index("ix_design_cases_creator_id", "design_cases", ["creator_id"])

    op.create_table(
        "proxy_models",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False, comment="主键"),
        sa.Column("model_name", sa.String(length=200), nullable=False, comment="模型名称"),
        sa.Column("model_version", sa.String(length=50), nullable=False, server_default="v1", comment="模型版本"),
        sa.Column("model_type", sa.String(length=50), nullable=False, comment="模型类型: kriging/gp/mlp/mf_adaptive"),
        sa.Column("input_dim", sa.Integer(), nullable=False, comment="输入变量维度"),
        sa.Column("output_dim", sa.Integer(), nullable=False, comment="输出响应维度"),
        sa.Column("metric", JSON_TYPE, nullable=True, comment="精度指标(JSON)"),
        sa.Column("weight_key", sa.String(length=500), nullable=True, comment="MinIO 模型权重对象key"),
        sa.Column("train_dataset_key", sa.String(length=500), nullable=True, comment="MinIO 训练数据集对象key"),
        sa.Column("description", sa.Text(), nullable=True, comment="模型说明"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft", comment="状态: draft/training/ready/failed"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间(UTC)"),
        comment="代理模型表(克里金/GP/MLP/多保真自适应采样)",
    )
    op.create_index("ix_proxy_models_model_name", "proxy_models", ["model_name"])

    op.create_table(
        "cfd_tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False, comment="主键"),
        sa.Column("case_id", sa.Integer(), nullable=False, comment="所属设计算例ID -> design_cases.id"),
        sa.Column("task_name", sa.String(length=200), nullable=False, comment="任务名称"),
        sa.Column("task_type", sa.String(length=50), nullable=False, comment="任务类型"),
        sa.Column("input_params", JSON_TYPE, nullable=True, comment="CFD 输入参数(JSON)"),
        sa.Column("output_result", JSON_TYPE, nullable=True, comment="CFD 输出结果(JSON)"),
        sa.Column("max_iter", sa.Integer(), nullable=False, server_default=sa.text("100"), comment="最大迭代步数"),
        sa.Column("current_iter", sa.Integer(), nullable=False, server_default=sa.text("0"), comment="当前迭代步数"),
        sa.Column("converge_criteria", JSON_TYPE, nullable=True, comment="收敛判据(JSON)"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending", comment="状态: pending/running/success/failed/stop"),
        sa.Column("error_msg", sa.Text(), nullable=True, comment="失败原因"),
        sa.Column("mesh_file_key", sa.String(length=500), nullable=True, comment="MinIO 网格文件对象key"),
        sa.Column("result_file_key", sa.String(length=500), nullable=True, comment="MinIO 结果文件对象key"),
        sa.Column("proxy_model_id", sa.Integer(), nullable=True, comment="关联代理模型ID -> proxy_models.id"),
        sa.Column("celery_task_id", sa.String(length=100), nullable=True, comment="Celery 异步任务ID"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True, comment="开始时间(UTC)"),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True, comment="结束时间(UTC)"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间(UTC)"),
        sa.ForeignKeyConstraint(["case_id"], ["design_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proxy_model_id"], ["proxy_models.id"], ondelete="SET NULL"),
        comment="CFD 迭代计算任务表",
    )
    op.create_index("ix_cfd_tasks_case_id", "cfd_tasks", ["case_id"])
    op.create_index("ix_cfd_tasks_proxy_model_id", "cfd_tasks", ["proxy_model_id"])
    op.create_index("ix_cfd_tasks_celery_task_id", "cfd_tasks", ["celery_task_id"])

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False, comment="主键"),
        sa.Column("case_id", sa.Integer(), nullable=False, comment="所属设计算例ID -> design_cases.id"),
        sa.Column("agent_name", sa.String(length=100), nullable=False, comment="智能体名称"),
        sa.Column("thread_id", sa.String(length=100), nullable=True, comment="LangGraph thread_id"),
        sa.Column("input_query", sa.Text(), nullable=True, comment="用户输入的自然语言任务"),
        sa.Column("state_snapshot", JSON_TYPE, nullable=True, comment="LangGraph 状态快照(JSON)"),
        sa.Column("trace_log", JSON_TYPE, nullable=True, comment="执行 trace 日志(JSON)"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending", comment="状态: pending/running/success/failed"),
        sa.Column("error_msg", sa.Text(), nullable=True, comment="失败原因"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True, comment="开始时间(UTC)"),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True, comment="结束时间(UTC)"),
        sa.ForeignKeyConstraint(["case_id"], ["design_cases.id"], ondelete="CASCADE"),
        comment="LangGraph 智能体运行记录表",
    )
    op.create_index("ix_agent_runs_case_id", "agent_runs", ["case_id"])
    op.create_index("ix_agent_runs_thread_id", "agent_runs", ["thread_id"])

    op.create_table(
        "experiment_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False, comment="主键"),
        sa.Column("cfd_task_id", sa.Integer(), nullable=False, comment="所属CFD任务ID -> cfd_tasks.id"),
        sa.Column("sample_tag", sa.String(length=20), nullable=False, comment="样本保真度: high_fid/low_fid"),
        sa.Column("input_x", JSON_TYPE, nullable=True, comment="输入样本向量(JSON 数组)"),
        sa.Column("output_y_true", JSON_TYPE, nullable=True, comment="真实输出向量(JSON)"),
        sa.Column("output_y_pred", JSON_TYPE, nullable=True, comment="代理模型预测输出向量(JSON)"),
        sa.Column("residual", sa.Float(), nullable=True, comment="预测残差"),
        sa.Column("mlflow_run_id", sa.String(length=64), nullable=True, comment="MLflow run_id"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间(UTC)"),
        sa.ForeignKeyConstraint(["cfd_task_id"], ["cfd_tasks.id"], ondelete="CASCADE"),
        comment="保真样本实验记录表",
    )
    op.create_index("ix_experiment_records_cfd_task_id", "experiment_records", ["cfd_task_id"])
    op.create_index("ix_experiment_records_mlflow_run_id", "experiment_records", ["mlflow_run_id"])


def downgrade() -> None:
    op.drop_index("ix_experiment_records_mlflow_run_id", table_name="experiment_records")
    op.drop_index("ix_experiment_records_cfd_task_id", table_name="experiment_records")
    op.drop_table("experiment_records")
    op.drop_index("ix_agent_runs_thread_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_case_id", table_name="agent_runs")
    op.drop_table("agent_runs")
    op.drop_index("ix_cfd_tasks_celery_task_id", table_name="cfd_tasks")
    op.drop_index("ix_cfd_tasks_proxy_model_id", table_name="cfd_tasks")
    op.drop_index("ix_cfd_tasks_case_id", table_name="cfd_tasks")
    op.drop_table("cfd_tasks")
    op.drop_index("ix_proxy_models_model_name", table_name="proxy_models")
    op.drop_table("proxy_models")
    op.drop_index("ix_design_cases_creator_id", table_name="design_cases")
    op.drop_index("ix_design_cases_case_name", table_name="design_cases")
    op.drop_table("design_cases")
    op.drop_column("users", "role")
