"""统一导入所有 ORM 模型，供 Alembic env.py 识别完整 metadata。

新增模型后务必在此 import，否则 autogenerate 不会感知表变更。
"""
from app.db.base import Base
from app.models.agent_run import AgentRun
from app.models.case_artifact import CaseArtifact
from app.models.case_version import CaseVersion
from app.models.cfd_task import CfdTask
from app.models.design_case import DesignCase
from app.models.experiment_record import ExperimentRecord
from app.models.proxy_model import ProxyModel
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "DesignCase",
    "CaseVersion",
    "CaseArtifact",
    "ProxyModel",
    "CfdTask",
    "AgentRun",
    "ExperimentRecord",
]
