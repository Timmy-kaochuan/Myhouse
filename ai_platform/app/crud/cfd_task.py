"""CfdTask 异步 CRUD。"""
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cfd_task import TASK_STATUS_PENDING, CfdTask

_EDITABLE = {c.name for c in CfdTask.__table__.columns} - {"id", "case_id", "created_at"}


async def create_cfd_task(
    session: AsyncSession,
    *,
    case_id: int,
    task_name: str,
    task_type: str,
    input_params: dict | None = None,
    max_iter: int = 100,
    converge_criteria: dict | None = None,
    proxy_model_id: int | None = None,
    mesh_file_key: str | None = None,
    result_file_key: str | None = None,
    celery_task_id: str | None = None,
    status: str = TASK_STATUS_PENDING,
) -> CfdTask:
    """创建 CFD 迭代任务。"""
    task = CfdTask(
        case_id=case_id,
        task_name=task_name,
        task_type=task_type,
        input_params=input_params,
        max_iter=max_iter,
        converge_criteria=converge_criteria,
        proxy_model_id=proxy_model_id,
        mesh_file_key=mesh_file_key,
        result_file_key=result_file_key,
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
    case_id: int | None = None,
    proxy_model_id: int | None = None,
    status: str | None = None,
) -> Sequence[CfdTask]:
    """分页查询，可选按算例/代理模型/状态过滤。"""
    stmt = select(CfdTask).order_by(CfdTask.id)
    if case_id is not None:
        stmt = stmt.where(CfdTask.case_id == case_id)
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
