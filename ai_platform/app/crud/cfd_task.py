"""CfdTask 异步 CRUD + 上游产物依赖环检测。"""
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.case_version import get_upstream_version_ids
from app.models.case_artifact import CaseArtifact
from app.models.cfd_task import TASK_STATUS_PENDING, CfdTask

_EDITABLE = {c.name for c in CfdTask.__table__.columns} - {
    "id",
    "case_version_id",
    "created_at",
}


async def artifact_creates_cycle(
    session: AsyncSession,
    *,
    version_id: int,
    input_artifact_id: int,
    exclude_task_id: int | None = None,
) -> bool:
    """判断"version_id 消费 input_artifact_id"是否会形成依赖环。

    环定义：沿 消费版本->生产版本 边，从产物所属版本出发能回到 version_id
    （含产物直接属于 version_id 自身的自环）。exclude_task_id 用于更新场景
    排除该任务自身的旧依赖边。
    """
    artifact = await session.get(CaseArtifact, input_artifact_id)
    if artifact is None:
        return False
    if artifact.case_version_id == version_id:
        return True
    upstream = await get_upstream_version_ids(
        session, artifact.case_version_id, exclude_task_id=exclude_task_id
    )
    return version_id in upstream


async def create_cfd_task(
    session: AsyncSession,
    *,
    case_version_id: int,
    task_name: str,
    task_type: str,
    input_params: dict | None = None,
    max_iter: int = 100,
    converge_criteria: dict | None = None,
    proxy_model_id: int | None = None,
    input_artifact_id: int | None = None,
    mesh_file_key: str | None = None,
    celery_task_id: str | None = None,
    status: str = TASK_STATUS_PENDING,
) -> CfdTask:
    """创建 CFD 迭代任务（归属算例版本）。"""
    task = CfdTask(
        case_version_id=case_version_id,
        task_name=task_name,
        task_type=task_type,
        input_params=input_params,
        max_iter=max_iter,
        converge_criteria=converge_criteria,
        proxy_model_id=proxy_model_id,
        input_artifact_id=input_artifact_id,
        mesh_file_key=mesh_file_key,
        celery_task_id=celery_task_id,
        status=status,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def get_cfd_task(session: AsyncSession, task_id: int) -> CfdTask | None:
    """按主键查询。"""
    return await session.get(CfdTask, task_id)


async def list_cfd_tasks(
    session: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 100,
    case_version_id: int | None = None,
    proxy_model_id: int | None = None,
    status: str | None = None,
) -> Sequence[CfdTask]:
    """分页查询，可选按算例版本/代理模型/状态过滤。"""
    stmt = select(CfdTask).order_by(CfdTask.id)
    if case_version_id is not None:
        stmt = stmt.where(CfdTask.case_version_id == case_version_id)
    if proxy_model_id is not None:
        stmt = stmt.where(CfdTask.proxy_model_id == proxy_model_id)
    if status:
        stmt = stmt.where(CfdTask.status == status)
    stmt = stmt.offset(offset).limit(limit)
    return (await session.execute(stmt)).scalars().all()


async def update_cfd_task(session: AsyncSession, task_id: int, values: dict) -> CfdTask | None:
    """按字典部分更新（迭代进度、结果、状态流转等）。不存在返回 None。"""
    task = await session.get(CfdTask, task_id)
    if task is None:
        return None
    for key, value in values.items():
        if key in _EDITABLE:
            setattr(task, key, value)
    await session.commit()
    await session.refresh(task)
    return task


async def delete_cfd_task(session: AsyncSession, task_id: int) -> bool:
    """删除任务，级联删除其实验记录。不存在返回 False。"""
    task = await session.get(CfdTask, task_id)
    if task is None:
        return False
    await session.delete(task)
    await session.commit()
    return True
