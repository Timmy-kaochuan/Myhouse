"""AgentRun 异步 CRUD。"""
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_run import RUN_STATUS_PENDING, AgentRun

_EDITABLE = {c.name for c in AgentRun.__table__.columns} - {"id", "case_id"}


async def create_agent_run(
    session: AsyncSession,
    *,
    case_id: int,
    agent_name: str,
    thread_id: str | None = None,
    input_query: str | None = None,
    status: str = RUN_STATUS_PENDING,
    started_at=None,
) -> AgentRun:
    """创建智能体运行记录。"""
    run = AgentRun(
        case_id=case_id,
        agent_name=agent_name,
        thread_id=thread_id,
        input_query=input_query,
        status=status,
        started_at=started_at,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def get_agent_run(session: AsyncSession, run_id: int) -> AgentRun | None:
    """按主键查询。"""
    return await session.get(AgentRun, run_id)


async def list_agent_runs(
    session: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 100,
    case_id: int | None = None,
    thread_id: str | None = None,
    status: str | None = None,
) -> Sequence[AgentRun]:
    """分页查询，可选按算例/thread_id/状态过滤。"""
    stmt = select(AgentRun).order_by(AgentRun.id)
    if case_id is not None:
        stmt = stmt.where(AgentRun.case_id == case_id)
    if thread_id:
        stmt = stmt.where(AgentRun.thread_id == thread_id)
    if status:
        stmt = stmt.where(AgentRun.status == status)
    stmt = stmt.offset(offset).limit(limit)
    return (await session.execute(stmt)).scalars().all()


async def update_agent_run(session: AsyncSession, run_id: int, values: dict) -> AgentRun | None:
    """按字典部分更新（状态快照、trace、结束时间等）。不存在返回 None。"""
    run = await session.get(AgentRun, run_id)
    if run is None:
        return None
    for key, value in values.items():
        if key in _EDITABLE:
            setattr(run, key, value)
    await session.commit()
    await session.refresh(run)
    return run


async def delete_agent_run(session: AsyncSession, run_id: int) -> bool:
    """删除运行记录。不存在返回 False。"""
    run = await session.get(AgentRun, run_id)
    if run is None:
        return False
    await session.delete(run)
    await session.commit()
    return True
