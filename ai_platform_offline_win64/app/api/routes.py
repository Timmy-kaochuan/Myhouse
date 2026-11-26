"""API 路由：健康检查 + 六类资源的 REST 接口。

- 统一使用 Depends(get_session) 注入异步会话；
- 网格/结果/权重等大文件只传 MinIO 对象 key，接口不收发二进制；
- 外键存在性在 API 层预检，返回 404 而非触发数据库 500。
"""
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.db.session import get_session
from app.schemas import (
    AgentRunCreate,
    AgentRunOut,
    AgentRunStatus,
    AgentRunUpdate,
    CaseArtifactCreate,
    CaseArtifactOut,
    CaseArtifactUpdate,
    CaseVersionCreate,
    CaseVersionOut,
    CaseVersionStatus,
    CaseVersionUpdate,
    CfdTaskCreate,
    CfdTaskOut,
    CfdTaskStatus,
    CfdTaskUpdate,
    DesignCaseCreate,
    DesignCaseOut,
    DesignCaseUpdate,
    ExperimentRecordCreate,
    ExperimentRecordOut,
    ExperimentRecordUpdate,
    ProxyModelCreate,
    ProxyModelOut,
    ProxyModelPredictIn,
    ProxyModelPredictOut,
    ProxyModelStatus,
    ProxyModelType,
    ProxyModelUpdate,
    RecordSource,
    Role,
    SampleTag,
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.services import predictor
from app.services.predictor import PredictorUnavailable

router = APIRouter()

# 异步数据库会话依赖
DbSession = Annotated[AsyncSession, Depends(get_session)]


# ==================== 健康检查 ====================
@router.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """服务存活检查。"""
    return {"status": "ok"}


@router.get("/health/db", tags=["health"])
async def health_db(session: DbSession) -> dict[str, str]:
    """数据库连通性检查。"""
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}


# ==================== User ====================
@router.post("/users", response_model=UserOut, status_code=http_status.HTTP_201_CREATED, tags=["users"])
async def create_user(payload: UserCreate, session: DbSession) -> UserOut:
    """创建用户（邮箱唯一，重复返回 409）。"""
    if await crud.get_user_by_email(session, payload.email):
        raise HTTPException(http_status.HTTP_409_CONFLICT, "email already exists")
    return await crud.create_user(session, **payload.model_dump())


@router.get("/users", response_model=list[UserOut], tags=["users"])
async def list_users(
    session: DbSession,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    role: Role | None = None,
) -> Sequence[UserOut]:
    """分页查询用户。"""
    return await crud.list_users(session, offset=offset, limit=limit, role=role)


@router.get("/users/{user_id}", response_model=UserOut, tags=["users"])
async def get_user(user_id: int, session: DbSession) -> UserOut:
    """查询单个用户。"""
    user = await crud.get_user(session, user_id)
    if user is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "user not found")
    return user


@router.patch("/users/{user_id}", response_model=UserOut, tags=["users"])
async def update_user(user_id: int, payload: UserUpdate, session: DbSession) -> UserOut:
    """部分更新用户。"""
    user = await crud.update_user(session, user_id, payload.model_dump(exclude_unset=True))
    if user is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "user not found")
    return user


@router.delete("/users/{user_id}", status_code=http_status.HTTP_204_NO_CONTENT, tags=["users"])
async def delete_user(user_id: int, session: DbSession) -> None:
    """删除用户（级联删除其算例）。"""
    if not await crud.delete_user(session, user_id):
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "user not found")


# ==================== DesignCase（主档） ====================
@router.post("/design-cases", response_model=DesignCaseOut, status_code=http_status.HTTP_201_CREATED, tags=["design-cases"])
async def create_design_case(payload: DesignCaseCreate, session: DbSession) -> DesignCaseOut:
    """创建设计算例主档（自动生成默认 v1 版本，可带初始设计参数）。"""
    if await crud.get_user(session, payload.creator_id) is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "creator(user) not found")
    if payload.parent_case_id is not None and await crud.get_design_case(session, payload.parent_case_id) is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "parent design case not found")
    return await crud.create_design_case(session, **payload.model_dump())


@router.get("/design-cases", response_model=list[DesignCaseOut], tags=["design-cases"])
async def list_design_cases(
    session: DbSession,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    creator_id: int | None = None,
) -> Sequence[DesignCaseOut]:
    """分页查询算例主档，可按创建人过滤。"""
    return await crud.list_design_cases(session, offset=offset, limit=limit, creator_id=creator_id)


@router.get("/design-cases/{case_id}", response_model=DesignCaseOut, tags=["design-cases"])
async def get_design_case(case_id: int, session: DbSession) -> DesignCaseOut:
    """查询单个算例主档。"""
    case = await crud.get_design_case(session, case_id)
    if case is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "design case not found")
    return case


@router.patch("/design-cases/{case_id}", response_model=DesignCaseOut, tags=["design-cases"])
async def update_design_case(case_id: int, payload: DesignCaseUpdate, session: DbSession) -> DesignCaseOut:
    """部分更新算例主档（updated_at 自动刷新）。"""
    if payload.parent_case_id is not None:
        if payload.parent_case_id == case_id:
            raise HTTPException(http_status.HTTP_409_CONFLICT, "parent case cannot be itself")
        if await crud.get_design_case(session, payload.parent_case_id) is None:
            raise HTTPException(http_status.HTTP_404_NOT_FOUND, "parent design case not found")
    case = await crud.update_design_case(session, case_id, payload.model_dump(exclude_unset=True))
    if case is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "design case not found")
    return case


@router.delete("/design-cases/{case_id}", status_code=http_status.HTTP_204_NO_CONTENT, tags=["design-cases"])
async def delete_design_case(case_id: int, session: DbSession) -> None:
    """删除算例主档（级联删除其版本、产物、CFD 任务与智能体运行记录）。"""
    if not await crud.delete_design_case(session, case_id):
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "design case not found")


# ==================== CaseVersion ====================
@router.post("/case-versions", response_model=CaseVersionOut, status_code=http_status.HTTP_201_CREATED, tags=["case-versions"])
async def create_case_version(payload: CaseVersionCreate, session: DbSession) -> CaseVersionOut:
    """在算例下创建新版本（同算例内版本号唯一）。"""
    if await crud.get_design_case(session, payload.case_id) is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "design case not found")
    if await crud.get_version_by_no(session, payload.case_id, payload.version_no):
        raise HTTPException(http_status.HTTP_409_CONFLICT, "version_no already exists in this case")
    return await crud.create_case_version(session, **payload.model_dump())


@router.get("/case-versions", response_model=list[CaseVersionOut], tags=["case-versions"])
async def list_case_versions(
    session: DbSession,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    case_id: int | None = None,
    status: CaseVersionStatus | None = None,
) -> Sequence[CaseVersionOut]:
    """分页查询算例版本，可按算例/状态过滤。"""
    return await crud.list_case_versions(
        session, offset=offset, limit=limit, case_id=case_id, status=status
    )


@router.get("/case-versions/{version_id}", response_model=CaseVersionOut, tags=["case-versions"])
async def get_case_version(version_id: int, session: DbSession) -> CaseVersionOut:
    """查询单个算例版本。"""
    version = await crud.get_case_version(session, version_id)
    if version is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "case version not found")
    return version


@router.patch("/case-versions/{version_id}", response_model=CaseVersionOut, tags=["case-versions"])
async def update_case_version(version_id: int, payload: CaseVersionUpdate, session: DbSession) -> CaseVersionOut:
    """部分更新版本（状态、设计参数、版本号等）。"""
    version = await crud.get_case_version(session, version_id)
    if version is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "case version not found")
    values = payload.model_dump(exclude_unset=True)
    new_no = values.get("version_no")
    if new_no is not None and new_no != version.version_no:
        if await crud.get_version_by_no(session, version.case_id, new_no):
            raise HTTPException(http_status.HTTP_409_CONFLICT, "version_no already exists in this case")
    return await crud.update_case_version(session, version_id, values)


@router.delete("/case-versions/{version_id}", status_code=http_status.HTTP_204_NO_CONTENT, tags=["case-versions"])
async def delete_case_version(version_id: int, session: DbSession) -> None:
    """删除版本（级联删除其产物与 CFD 任务）。"""
    if not await crud.delete_case_version(session, version_id):
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "case version not found")


@router.get("/case-versions/{version_id}/upstream", response_model=list[CaseVersionOut], tags=["case-versions"])
async def get_case_version_upstream(version_id: int, session: DbSession) -> Sequence[CaseVersionOut]:
    """查询某版本的全部上游版本（沿"消费->生产"依赖边，含传递依赖）。"""
    version = await crud.get_case_version(session, version_id)
    if version is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "case version not found")
    ids = await crud.get_upstream_version_ids(session, version_id)
    versions = [await crud.get_case_version(session, vid) for vid in ids]
    return [v for v in versions if v is not None]


@router.get("/case-versions/{version_id}/downstream", response_model=list[CaseVersionOut], tags=["case-versions"])
async def get_case_version_downstream(version_id: int, session: DbSession) -> Sequence[CaseVersionOut]:
    """查询某版本的全部下游版本（沿"生产->消费"反向依赖边，含传递依赖）。"""
    version = await crud.get_case_version(session, version_id)
    if version is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "case version not found")
    ids = await crud.get_downstream_version_ids(session, version_id)
    versions = [await crud.get_case_version(session, vid) for vid in ids]
    return [v for v in versions if v is not None]


# ==================== CaseArtifact ====================
@router.post("/case-artifacts", response_model=CaseArtifactOut, status_code=http_status.HTTP_201_CREATED, tags=["case-artifacts"])
async def create_case_artifact(payload: CaseArtifactCreate, session: DbSession) -> CaseArtifactOut:
    """登记算例产物（文件本体在 MinIO，接口只收对象 key）。"""
    if await crud.get_case_version(session, payload.case_version_id) is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "case version not found")
    return await crud.create_case_artifact(session, **payload.model_dump())


@router.get("/case-artifacts", response_model=list[CaseArtifactOut], tags=["case-artifacts"])
async def list_case_artifacts(
    session: DbSession,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    case_version_id: int | None = None,
    artifact_type: str | None = None,
) -> Sequence[CaseArtifactOut]:
    """分页查询产物，可按版本/类型过滤。"""
    return await crud.list_case_artifacts(
        session, offset=offset, limit=limit, case_version_id=case_version_id, artifact_type=artifact_type
    )


@router.get("/case-artifacts/{artifact_id}", response_model=CaseArtifactOut, tags=["case-artifacts"])
async def get_case_artifact(artifact_id: int, session: DbSession) -> CaseArtifactOut:
    """查询单个产物登记。"""
    artifact = await crud.get_case_artifact(session, artifact_id)
    if artifact is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "case artifact not found")
    return artifact


@router.patch("/case-artifacts/{artifact_id}", response_model=CaseArtifactOut, tags=["case-artifacts"])
async def update_case_artifact(artifact_id: int, payload: CaseArtifactUpdate, session: DbSession) -> CaseArtifactOut:
    """部分更新产物登记（类型、对象 key、说明等）。"""
    artifact = await crud.update_case_artifact(session, artifact_id, payload.model_dump(exclude_unset=True))
    if artifact is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "case artifact not found")
    return artifact


@router.delete("/case-artifacts/{artifact_id}", status_code=http_status.HTTP_204_NO_CONTENT, tags=["case-artifacts"])
async def delete_case_artifact(artifact_id: int, session: DbSession) -> None:
    """删除产物登记（引用它的 CFD 任务的 input_artifact_id 由数据库置空）。"""
    if not await crud.delete_case_artifact(session, artifact_id):
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "case artifact not found")


# ==================== CfdTask ====================
@router.post("/cfd-tasks", response_model=CfdTaskOut, status_code=http_status.HTTP_201_CREATED, tags=["cfd-tasks"])
async def create_cfd_task(payload: CfdTaskCreate, session: DbSession) -> CfdTaskOut:
    """创建 CFD 迭代任务（归属算例版本，可选引用上游产物）。"""
    if await crud.get_case_version(session, payload.case_version_id) is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "case version not found")
    if payload.proxy_model_id is not None and await crud.get_proxy_model(session, payload.proxy_model_id) is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "proxy model not found")
    if payload.input_artifact_id is not None:
        if await crud.get_case_artifact(session, payload.input_artifact_id) is None:
            raise HTTPException(http_status.HTTP_404_NOT_FOUND, "case artifact not found")
        if await crud.artifact_creates_cycle(
            session, version_id=payload.case_version_id, input_artifact_id=payload.input_artifact_id
        ):
            raise HTTPException(http_status.HTTP_409_CONFLICT, "input artifact would create a dependency cycle")
    return await crud.create_cfd_task(session, **payload.model_dump())


@router.get("/cfd-tasks", response_model=list[CfdTaskOut], tags=["cfd-tasks"])
async def list_cfd_tasks(
    session: DbSession,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    case_version_id: int | None = None,
    proxy_model_id: int | None = None,
    status: CfdTaskStatus | None = None,
) -> Sequence[CfdTaskOut]:
    """分页查询 CFD 任务，可按算例版本/代理模型/状态过滤。"""
    return await crud.list_cfd_tasks(
        session, offset=offset, limit=limit, case_version_id=case_version_id, proxy_model_id=proxy_model_id, status=status
    )


@router.get("/cfd-tasks/{task_id}", response_model=CfdTaskOut, tags=["cfd-tasks"])
async def get_cfd_task(task_id: int, session: DbSession) -> CfdTaskOut:
    """查询单个 CFD 任务。"""
    task = await crud.get_cfd_task(session, task_id)
    if task is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "cfd task not found")
    return task


@router.patch("/cfd-tasks/{task_id}", response_model=CfdTaskOut, tags=["cfd-tasks"])
async def update_cfd_task(task_id: int, payload: CfdTaskUpdate, session: DbSession) -> CfdTaskOut:
    """更新任务：迭代进度、结果、状态流转、上游产物、MinIO key 等。"""
    values = payload.model_dump(exclude_unset=True)
    if values.get("input_artifact_id") is not None:
        if await crud.get_case_artifact(session, values["input_artifact_id"]) is None:
            raise HTTPException(http_status.HTTP_404_NOT_FOUND, "case artifact not found")
        if await crud.artifact_creates_cycle(
            session,
            version_id=(await crud.get_cfd_task(session, task_id)).case_version_id,
            input_artifact_id=values["input_artifact_id"],
            exclude_task_id=task_id,
        ):
            raise HTTPException(http_status.HTTP_409_CONFLICT, "input artifact would create a dependency cycle")
    task = await crud.update_cfd_task(session, task_id, values)
    if task is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "cfd task not found")
    return task


@router.delete("/cfd-tasks/{task_id}", status_code=http_status.HTTP_204_NO_CONTENT, tags=["cfd-tasks"])
async def delete_cfd_task(task_id: int, session: DbSession) -> None:
    """删除任务（级联删除实验记录）。"""
    if not await crud.delete_cfd_task(session, task_id):
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "cfd task not found")


# ==================== ProxyModel ====================
@router.post("/proxy-models", response_model=ProxyModelOut, status_code=http_status.HTTP_201_CREATED, tags=["proxy-models"])
async def create_proxy_model(payload: ProxyModelCreate, session: DbSession) -> ProxyModelOut:
    """创建代理模型记录（权重/数据集只存 MinIO key）。"""
    return await crud.create_proxy_model(session, **payload.model_dump())


@router.get("/proxy-models", response_model=list[ProxyModelOut], tags=["proxy-models"])
async def list_proxy_models(
    session: DbSession,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    model_type: ProxyModelType | None = None,
    status: ProxyModelStatus | None = None,
) -> Sequence[ProxyModelOut]:
    """分页查询代理模型，可按类型/状态过滤。"""
    return await crud.list_proxy_models(
        session, offset=offset, limit=limit, model_type=model_type, status=status
    )


@router.get("/proxy-models/{model_id}", response_model=ProxyModelOut, tags=["proxy-models"])
async def get_proxy_model(model_id: int, session: DbSession) -> ProxyModelOut:
    """查询单个代理模型。"""
    model = await crud.get_proxy_model(session, model_id)
    if model is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "proxy model not found")
    return model


@router.patch("/proxy-models/{model_id}", response_model=ProxyModelOut, tags=["proxy-models"])
async def update_proxy_model(model_id: int, payload: ProxyModelUpdate, session: DbSession) -> ProxyModelOut:
    """部分更新代理模型（指标、权重key、状态等）。"""
    model = await crud.update_proxy_model(session, model_id, payload.model_dump(exclude_unset=True))
    if model is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "proxy model not found")
    return model


@router.delete("/proxy-models/{model_id}", status_code=http_status.HTTP_204_NO_CONTENT, tags=["proxy-models"])
async def delete_proxy_model(model_id: int, session: DbSession) -> None:
    """删除代理模型（关联 CFD 任务的引用由数据库置空）。"""
    if not await crud.delete_proxy_model(session, model_id):
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "proxy model not found")


@router.post("/proxy-models/{model_id}/predict", response_model=ProxyModelPredictOut, tags=["proxy-models"])
async def predict_proxy_model(model_id: int, payload: ProxyModelPredictIn, session: DbSession) -> ProxyModelPredictOut:
    """代理模型推理（供工具链/智能体调用）：优先内嵌权重，权重文件后端接入后自动可用。"""
    model = await crud.get_proxy_model(session, model_id)
    if model is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "proxy model not found")
    if model.status != "ready":
        raise HTTPException(http_status.HTTP_409_CONFLICT, f"model is not ready (status={model.status})")
    if len(payload.input_x) != model.input_dim:
        raise HTTPException(
            http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"input_x length {len(payload.input_x)} != model input_dim {model.input_dim}",
        )
    try:
        output_y, weight_source = predictor.predict(model, payload.input_x)
    except PredictorUnavailable as exc:
        raise HTTPException(http_status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
    return ProxyModelPredictOut(model_id=model.id, input_x=payload.input_x, output_y=output_y, weight_source=weight_source)


# ==================== AgentRun ====================
@router.post("/agent-runs", response_model=AgentRunOut, status_code=http_status.HTTP_201_CREATED, tags=["agent-runs"])
async def create_agent_run(payload: AgentRunCreate, session: DbSession) -> AgentRunOut:
    """创建 LangGraph 智能体运行记录。"""
    if await crud.get_design_case(session, payload.case_id) is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "design case not found")
    return await crud.create_agent_run(session, **payload.model_dump())


@router.get("/agent-runs", response_model=list[AgentRunOut], tags=["agent-runs"])
async def list_agent_runs(
    session: DbSession,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    case_id: int | None = None,
    thread_id: str | None = None,
    status: AgentRunStatus | None = None,
) -> Sequence[AgentRunOut]:
    """分页查询智能体运行记录，可按算例/thread_id/状态过滤。"""
    return await crud.list_agent_runs(
        session, offset=offset, limit=limit, case_id=case_id, thread_id=thread_id, status=status
    )


@router.get("/agent-runs/{run_id}", response_model=AgentRunOut, tags=["agent-runs"])
async def get_agent_run(run_id: int, session: DbSession) -> AgentRunOut:
    """查询单条运行记录（含状态快照与 trace）。"""
    run = await crud.get_agent_run(session, run_id)
    if run is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "agent run not found")
    return run


@router.patch("/agent-runs/{run_id}", response_model=AgentRunOut, tags=["agent-runs"])
async def update_agent_run(run_id: int, payload: AgentRunUpdate, session: DbSession) -> AgentRunOut:
    """更新运行记录：状态快照、trace 日志、起止时间等。"""
    run = await crud.update_agent_run(session, run_id, payload.model_dump(exclude_unset=True))
    if run is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "agent run not found")
    return run


@router.delete("/agent-runs/{run_id}", status_code=http_status.HTTP_204_NO_CONTENT, tags=["agent-runs"])
async def delete_agent_run(run_id: int, session: DbSession) -> None:
    """删除运行记录。"""
    if not await crud.delete_agent_run(session, run_id):
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "agent run not found")


# ==================== ExperimentRecord ====================
@router.post("/experiment-records", response_model=ExperimentRecordOut, status_code=http_status.HTTP_201_CREATED, tags=["experiment-records"])
async def create_experiment_record(payload: ExperimentRecordCreate, session: DbSession) -> ExperimentRecordOut:
    """创建保真样本记录：仿真样本(sim)须挂 CFD 任务；试验样本(test)须登记原始数据文件 key。"""
    if payload.source == "sim":
        if payload.cfd_task_id is None:
            raise HTTPException(http_status.HTTP_422_UNPROCESSABLE_ENTITY, "source=sim requires cfd_task_id")
        if await crud.get_cfd_task(session, payload.cfd_task_id) is None:
            raise HTTPException(http_status.HTTP_404_NOT_FOUND, "cfd task not found")
    else:  # test：高保真试验数据，不依赖 CFD 任务
        if not payload.test_data_key:
            raise HTTPException(http_status.HTTP_422_UNPROCESSABLE_ENTITY, "source=test requires test_data_key")
    return await crud.create_experiment_record(session, **payload.model_dump())


@router.get("/experiment-records", response_model=list[ExperimentRecordOut], tags=["experiment-records"])
async def list_experiment_records(
    session: DbSession,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    cfd_task_id: int | None = None,
    source: RecordSource | None = None,
    sample_tag: SampleTag | None = None,
    mlflow_run_id: str | None = None,
) -> Sequence[ExperimentRecordOut]:
    """分页查询实验记录，可按任务/来源/保真度/run_id 过滤。"""
    return await crud.list_experiment_records(
        session,
        offset=offset,
        limit=limit,
        cfd_task_id=cfd_task_id,
        source=source,
        sample_tag=sample_tag,
        mlflow_run_id=mlflow_run_id,
    )


@router.get("/experiment-records/{record_id}", response_model=ExperimentRecordOut, tags=["experiment-records"])
async def get_experiment_record(record_id: int, session: DbSession) -> ExperimentRecordOut:
    """查询单条实验记录。"""
    record = await crud.get_experiment_record(session, record_id)
    if record is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "experiment record not found")
    return record


@router.patch("/experiment-records/{record_id}", response_model=ExperimentRecordOut, tags=["experiment-records"])
async def update_experiment_record(record_id: int, payload: ExperimentRecordUpdate, session: DbSession) -> ExperimentRecordOut:
    """部分更新实验记录（预测值、残差、run_id 等）。"""
    record = await crud.update_experiment_record(session, record_id, payload.model_dump(exclude_unset=True))
    if record is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "experiment record not found")
    return record


@router.delete("/experiment-records/{record_id}", status_code=http_status.HTTP_204_NO_CONTENT, tags=["experiment-records"])
async def delete_experiment_record(record_id: int, session: DbSession) -> None:
    """删除实验记录。"""
    if not await crud.delete_experiment_record(session, record_id):
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "experiment record not found")
