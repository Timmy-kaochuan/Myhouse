"""case versioning: split design_cases into master + case_versions, add case_artifacts

- design_cases 主档化：删除 case_version/design_parameters/status，新增 parent_case_id
- 新表 case_versions（版本号同算例唯一）、case_artifacts（产物登记）
- cfd_tasks 从挂算例改为挂版本（存量任务回填到所属算例的唯一版本），新增 input_artifact_id

存量迁移规则：每个旧 design_cases 行 => 一个 case_versions 行（版本号沿用原 case_version，
状态与设计参数随迁）；cfd_tasks.case_id => 该算例当前唯一版本的 id。

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-25

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 与 app/db/base.py 的 JSONField 保持一致：SQLite 用 JSON，PostgreSQL 用 JSONB
JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    # 1. 新表 case_versions
    op.create_table(
        "case_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False, comment="主键"),
        sa.Column("case_id", sa.Integer(), nullable=False, comment="所属设计算例ID -> design_cases.id"),
        sa.Column("version_no", sa.String(length=50), nullable=False, server_default="v1", comment="版本号，如 v1/v2；同一算例内唯一"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft", comment="状态: draft/running/finished/archived"),
        sa.Column("design_parameters", JSON_TYPE, nullable=True, comment="设计参数(JSON)"),
        sa.Column("description", sa.Text(), nullable=True, comment="版本说明"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间(UTC)"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, comment="更新时间(UTC)"),
        sa.ForeignKeyConstraint(["case_id"], ["design_cases.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("case_id", "version_no", name="uq_case_versions_case_version"),
        comment="算例版本表",
    )
    op.create_index("ix_case_versions_case_id", "case_versions", ["case_id"])

    # 2. 新表 case_artifacts
    op.create_table(
        "case_artifacts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False, comment="主键"),
        sa.Column("case_version_id", sa.Integer(), nullable=False, comment="所属算例版本ID -> case_versions.id"),
        sa.Column("artifact_type", sa.String(length=20), nullable=False, comment="产物类型: mesh/result/weight/dataset/other"),
        sa.Column("file_key", sa.String(length=500), nullable=False, comment="MinIO 对象key，约定 cases/{算例}/{版本}/outputs/..."),
        sa.Column("description", sa.Text(), nullable=True, comment="产物说明"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间(UTC)"),
        sa.ForeignKeyConstraint(["case_version_id"], ["case_versions.id"], ondelete="CASCADE"),
        comment="算例产物登记表",
    )
    op.create_index("ix_case_artifacts_case_version_id", "case_artifacts", ["case_version_id"])

    # 3. 存量算例的版本信息迁入 case_versions（每个旧算例行 => 一个版本行）
    op.execute(
        "INSERT INTO case_versions (case_id, version_no, status, design_parameters, description, created_at, updated_at) "
        "SELECT id, case_version, status, design_parameters, NULL, created_at, updated_at "
        "FROM design_cases"
    )

    # 4. design_cases 主档化：重建为 主档结构（去掉版本/参数/状态，新增 parent_case_id）
    op.create_table(
        "design_cases_new",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False, comment="主键"),
        sa.Column("case_name", sa.String(length=200), nullable=False, comment="算例名称"),
        sa.Column("description", sa.Text(), nullable=True, comment="算例描述"),
        sa.Column("parent_case_id", sa.Integer(), nullable=True, comment="父算例ID(衍生/复制来源) -> design_cases.id，可空"),
        sa.Column("creator_id", sa.Integer(), nullable=False, comment="创建人ID -> users.id"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间(UTC)"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, comment="更新时间(UTC)"),
        sa.ForeignKeyConstraint(["parent_case_id"], ["design_cases.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="CASCADE"),
        comment="设计算例主档表",
    )
    op.execute(
        "INSERT INTO design_cases_new (id, case_name, description, parent_case_id, creator_id, created_at, updated_at) "
        "SELECT id, case_name, description, NULL, creator_id, created_at, updated_at "
        "FROM design_cases"
    )
    op.drop_table("design_cases")
    op.rename_table("design_cases_new", "design_cases")
    op.create_index("ix_design_cases_case_name", "design_cases", ["case_name"])
    op.create_index("ix_design_cases_creator_id", "design_cases", ["creator_id"])
    op.create_index("ix_design_cases_parent_case_id", "design_cases", ["parent_case_id"])

    # 5. cfd_tasks 重建：case_id -> case_version_id（回填到所属算例的唯一版本），新增 input_artifact_id
    op.create_table(
        "cfd_tasks_new",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False, comment="主键"),
        sa.Column("case_version_id", sa.Integer(), nullable=False, comment="所属算例版本ID -> case_versions.id"),
        sa.Column("input_artifact_id", sa.Integer(), nullable=True, comment="上游产物ID(输入来源) -> case_artifacts.id，可空"),
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
        sa.ForeignKeyConstraint(["case_version_id"], ["case_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["input_artifact_id"], ["case_artifacts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["proxy_model_id"], ["proxy_models.id"], ondelete="SET NULL"),
        comment="CFD 迭代计算任务表",
    )
    op.execute(
        "INSERT INTO cfd_tasks_new (id, case_version_id, input_artifact_id, task_name, task_type, input_params, "
        "output_result, max_iter, current_iter, converge_criteria, status, error_msg, mesh_file_key, result_file_key, "
        "proxy_model_id, celery_task_id, started_at, finished_at, created_at) "
        "SELECT t.id, cv.id, NULL, t.task_name, t.task_type, t.input_params, t.output_result, t.max_iter, "
        "t.current_iter, t.converge_criteria, t.status, t.error_msg, t.mesh_file_key, t.result_file_key, "
        "t.proxy_model_id, t.celery_task_id, t.started_at, t.finished_at, t.created_at "
        "FROM cfd_tasks t "
        "JOIN case_versions cv ON cv.id = (SELECT MIN(c2.id) FROM case_versions c2 WHERE c2.case_id = t.case_id)"
    )
    op.drop_table("cfd_tasks")
    op.rename_table("cfd_tasks_new", "cfd_tasks")
    op.create_index("ix_cfd_tasks_case_version_id", "cfd_tasks", ["case_version_id"])
    op.create_index("ix_cfd_tasks_input_artifact_id", "cfd_tasks", ["input_artifact_id"])
    op.create_index("ix_cfd_tasks_proxy_model_id", "cfd_tasks", ["proxy_model_id"])
    op.create_index("ix_cfd_tasks_celery_task_id", "cfd_tasks", ["celery_task_id"])


def downgrade() -> None:
    """尽力回滚到 0002：多版本算例只保留 id 最小的版本，其余版本数据丢失。"""
    # 1. cfd_tasks 退回挂算例
    op.create_table(
        "cfd_tasks_old",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("task_name", sa.String(length=200), nullable=False),
        sa.Column("task_type", sa.String(length=50), nullable=False),
        sa.Column("input_params", JSON_TYPE),
        sa.Column("output_result", JSON_TYPE),
        sa.Column("max_iter", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("current_iter", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("converge_criteria", JSON_TYPE),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("error_msg", sa.Text()),
        sa.Column("mesh_file_key", sa.String(length=500)),
        sa.Column("result_file_key", sa.String(length=500)),
        sa.Column("proxy_model_id", sa.Integer()),
        sa.Column("celery_task_id", sa.String(length=100)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["design_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proxy_model_id"], ["proxy_models.id"], ondelete="SET NULL"),
    )
    op.execute(
        "INSERT INTO cfd_tasks_old (id, case_id, task_name, task_type, input_params, output_result, max_iter, "
        "current_iter, converge_criteria, status, error_msg, mesh_file_key, result_file_key, proxy_model_id, "
        "celery_task_id, started_at, finished_at, created_at) "
        "SELECT t.id, cv.case_id, t.task_name, t.task_type, t.input_params, t.output_result, t.max_iter, "
        "t.current_iter, t.converge_criteria, t.status, t.error_msg, t.mesh_file_key, t.result_file_key, "
        "t.proxy_model_id, t.celery_task_id, t.started_at, t.finished_at, t.created_at "
        "FROM cfd_tasks t JOIN case_versions cv ON cv.id = t.case_version_id"
    )
    op.drop_table("cfd_tasks")
    op.rename_table("cfd_tasks_old", "cfd_tasks")
    op.create_index("ix_cfd_tasks_case_id", "cfd_tasks", ["case_id"])
    op.create_index("ix_cfd_tasks_proxy_model_id", "cfd_tasks", ["proxy_model_id"])
    op.create_index("ix_cfd_tasks_celery_task_id", "cfd_tasks", ["celery_task_id"])

    # 2. design_cases 退回单表结构（版本号/状态/参数取每算例最早版本）
    op.create_table(
        "design_cases_old",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("case_name", sa.String(length=200), nullable=False),
        sa.Column("case_version", sa.String(length=50), nullable=False, server_default="v1"),
        sa.Column("description", sa.Text()),
        sa.Column("design_parameters", JSON_TYPE),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("creator_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.execute(
        "INSERT INTO design_cases_old (id, case_name, case_version, description, design_parameters, status, "
        "creator_id, created_at, updated_at) "
        "SELECT d.id, d.case_name, cv.version_no, d.description, cv.design_parameters, cv.status, "
        "d.creator_id, d.created_at, d.updated_at "
        "FROM design_cases d "
        "JOIN case_versions cv ON cv.id = (SELECT MIN(c2.id) FROM case_versions c2 WHERE c2.case_id = d.id)"
    )
    op.drop_table("design_cases")
    op.rename_table("design_cases_old", "design_cases")
    op.create_index("ix_design_cases_case_name", "design_cases", ["case_name"])
    op.create_index("ix_design_cases_creator_id", "design_cases", ["creator_id"])

    # 3. 删除新表
    op.drop_table("case_artifacts")
    op.drop_table("case_versions")
