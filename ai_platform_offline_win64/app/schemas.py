"""Pydantic API Schema：请求体 / 响应体定义（Pydantic v2）。

状态枚举用 Literal 在 API 边界校验，数据库列统一存 String，
兼容 SQLite(开发) 与 PostgreSQL(生产)。JSON 字段用于参数、向量、日志；
文件（网格/结果/权重）只传 MinIO 对象 key。
"""
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------- 状态/类型常量（API 校验用） ----------
Role = Literal["admin", "engineer", "viewer"]
CaseVersionStatus = Literal["draft", "running", "finished", "archived"]
ArtifactType = Literal["mesh", "result", "weight", "dataset", "other"]
CfdTaskStatus = Literal["pending", "running", "success", "failed", "stop"]
ProxyModelType = Literal["kriging", "gp", "mlp", "mf_adaptive"]  # mf_adaptive=多保真自适应采样
ProxyModelStatus = Literal["draft", "training", "ready", "failed"]
AgentRunStatus = Literal["pending", "running", "success", "failed"]
SampleTag = Literal["high_fid", "low_fid"]
RecordSource = Literal["sim", "test"]  # sim=仿真(低保真) test=试验(高保真)

# JSON 字段类型别名
JsonDict = dict[str, Any]
JsonVector = dict[str, Any] | list[Any]

# 简单邮箱校验（离线环境，不依赖 email-validator 包）
EmailField = Annotated[str, Field(max_length=255, pattern=r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")]


# ==================== User ====================
class UserCreate(BaseModel):
    email: EmailField
    display_name: str | None = Field(default=None, max_length=100)
    role: Role = "viewer"


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    role: Role | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str | None
    role: str
    created_at: datetime


# ==================== DesignCase（主档） ====================
class DesignCaseCreate(BaseModel):
    case_name: str = Field(max_length=200)
    description: str | None = None
    parent_case_id: int | None = None
    creator_id: int
    # 创建主档时自动生成 v1 版本，可带初始设计参数
    design_parameters: JsonDict | None = None


class DesignCaseUpdate(BaseModel):
    case_name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    parent_case_id: int | None = None


class DesignCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_name: str
    description: str | None
    parent_case_id: int | None
    creator_id: int
    created_at: datetime
    updated_at: datetime


# ==================== CaseVersion ====================
class CaseVersionCreate(BaseModel):
    case_id: int
    version_no: str = Field(default="v1", max_length=50)
    status: CaseVersionStatus = "draft"
    design_parameters: JsonDict | None = None
    description: str | None = None


class CaseVersionUpdate(BaseModel):
    version_no: str | None = Field(default=None, max_length=50)
    status: CaseVersionStatus | None = None
    design_parameters: JsonDict | None = None
    description: str | None = None


class CaseVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    version_no: str
    status: str
    design_parameters: JsonDict | None
    description: str | None
    created_at: datetime
    updated_at: datetime


# ==================== CaseArtifact ====================
class CaseArtifactCreate(BaseModel):
    case_version_id: int
    artifact_type: ArtifactType
    file_key: str = Field(max_length=500)
    description: str | None = None


class CaseArtifactUpdate(BaseModel):
    artifact_type: ArtifactType | None = None
    file_key: str | None = Field(default=None, max_length=500)
    description: str | None = None


class CaseArtifactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_version_id: int
    artifact_type: str
    file_key: str
    description: str | None
    created_at: datetime


# ==================== CfdTask ====================
class CfdTaskCreate(BaseModel):
    case_version_id: int
    task_name: str = Field(max_length=200)
    task_type: str = Field(max_length=50, description="如 flow/combustion/heat/cooling")
    input_params: JsonDict | None = None
    max_iter: int = Field(default=100, ge=1)
    converge_criteria: JsonDict | None = None
    proxy_model_id: int | None = None
    input_artifact_id: int | None = None
    mesh_file_key: str | None = Field(default=None, max_length=500)
    celery_task_id: str | None = Field(default=None, max_length=100)


class CfdTaskUpdate(BaseModel):
    task_name: str | None = Field(default=None, max_length=200)
    task_type: str | None = Field(default=None, max_length=50)
    input_params: JsonDict | None = None
    output_result: JsonDict | None = None
    max_iter: int | None = Field(default=None, ge=1)
    current_iter: int | None = Field(default=None, ge=0)
    converge_criteria: JsonDict | None = None
    status: CfdTaskStatus | None = None
    error_msg: str | None = None
    input_artifact_id: int | None = None
    mesh_file_key: str | None = Field(default=None, max_length=500)
    result_file_key: str | None = Field(default=None, max_length=500)
    proxy_model_id: int | None = None
    celery_task_id: str | None = Field(default=None, max_length=100)
    started_at: datetime | None = None
    finished_at: datetime | None = None


class CfdTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_version_id: int
    input_artifact_id: int | None
    task_name: str
    task_type: str
    input_params: JsonDict | None
    output_result: JsonDict | None
    max_iter: int
    current_iter: int
    converge_criteria: JsonDict | None
    status: str
    error_msg: str | None
    mesh_file_key: str | None
    result_file_key: str | None
    proxy_model_id: int | None
    celery_task_id: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


# ==================== ProxyModel ====================
class ProxyModelCreate(BaseModel):
    model_name: str = Field(max_length=200)
    model_version: str = Field(default="v1", max_length=50)
    model_type: ProxyModelType
    input_dim: int = Field(ge=1)
    output_dim: int = Field(ge=1)
    metric: JsonDict | None = None
    weight_key: str | None = Field(default=None, max_length=500)
    weights_json: JsonDict | None = None
    train_dataset_key: str | None = Field(default=None, max_length=500)
    description: str | None = None
    status: ProxyModelStatus = "draft"


class ProxyModelUpdate(BaseModel):
    model_name: str | None = Field(default=None, max_length=200)
    model_version: str | None = Field(default=None, max_length=50)
    model_type: ProxyModelType | None = None
    input_dim: int | None = Field(default=None, ge=1)
    output_dim: int | None = Field(default=None, ge=1)
    metric: JsonDict | None = None
    weight_key: str | None = Field(default=None, max_length=500)
    weights_json: JsonDict | None = None
    train_dataset_key: str | None = Field(default=None, max_length=500)
    description: str | None = None
    status: ProxyModelStatus | None = None


class ProxyModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_name: str
    model_version: str
    model_type: str
    input_dim: int
    output_dim: int
    metric: JsonDict | None
    weight_key: str | None
    weights_json: JsonDict | None
    train_dataset_key: str | None
    description: str | None
    status: str
    created_at: datetime


class ProxyModelPredictIn(BaseModel):
    input_x: list[float] = Field(min_length=1, description="输入向量，长度须等于模型 input_dim")


class ProxyModelPredictOut(BaseModel):
    model_id: int
    input_x: list[float]
    output_y: list[float]
    weight_source: str  # inline=内嵌权重 / file=权重文件(待接入对象存储)


# ==================== AgentRun ====================
class AgentRunCreate(BaseModel):
    case_id: int
    agent_name: str = Field(max_length=100)
    thread_id: str | None = Field(default=None, max_length=100)
    input_query: str | None = None
    status: AgentRunStatus = "pending"
    started_at: datetime | None = None


class AgentRunUpdate(BaseModel):
    agent_name: str | None = Field(default=None, max_length=100)
    thread_id: str | None = Field(default=None, max_length=100)
    input_query: str | None = None
    state_snapshot: JsonDict | None = None
    trace_log: JsonDict | None = None
    status: AgentRunStatus | None = None
    error_msg: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class AgentRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    agent_name: str
    thread_id: str | None
    input_query: str | None
    state_snapshot: JsonDict | None
    trace_log: JsonDict | None
    status: str
    error_msg: str | None
    started_at: datetime | None
    finished_at: datetime | None


# ==================== ExperimentRecord ====================
class ExperimentRecordCreate(BaseModel):
    cfd_task_id: int | None = None
    source: RecordSource = "sim"
    sample_tag: SampleTag
    weight: float | None = Field(default=None, ge=0, description="训练权重；试验样本通常给更大值")
    test_data_key: str | None = Field(default=None, max_length=500, description="来源为试验时必填：原始试验数据文件 key")
    input_x: JsonVector | None = None
    output_y_true: JsonVector | None = None
    output_y_pred: JsonVector | None = None
    residual: float | None = None
    mlflow_run_id: str | None = Field(default=None, max_length=64)


class ExperimentRecordUpdate(BaseModel):
    sample_tag: SampleTag | None = None
    weight: float | None = Field(default=None, ge=0)
    test_data_key: str | None = Field(default=None, max_length=500)
    input_x: JsonVector | None = None
    output_y_true: JsonVector | None = None
    output_y_pred: JsonVector | None = None
    residual: float | None = None
    mlflow_run_id: str | None = Field(default=None, max_length=64)


class ExperimentRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cfd_task_id: int | None
    source: str
    sample_tag: str
    weight: float | None
    test_data_key: str | None
    input_x: JsonVector | None
    output_y_true: JsonVector | None
    output_y_pred: JsonVector | None
    residual: float | None
    mlflow_run_id: str | None
    created_at: datetime
