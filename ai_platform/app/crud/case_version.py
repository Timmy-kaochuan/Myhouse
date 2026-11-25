"""CaseVersion 异步 CRUD + 血缘（上游/下游）遍历。

依赖边约定：一条 CFD 任务挂在"消费版本"上、引用"生产版本"产出的产物，
即形成边 消费版本 -> 生产版本。
"""
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case_artifact import CaseArtifact
from app.models.case_version import VERSION_STATUS_DRAFT, CaseVersion
from app.models.cfd_task import CfdTask

_EDITABLE = {c.name for c in CaseVersion.__table__.columns} - {
    "id",
    "case_id",
    "created_at",
    "updated_at",
}


async def create_case_version(
    session: AsyncSession,
    *,
    case_id: int,
    version_no: str = "v1",
    status: str = VERSION_STATUS_DRAFT,
    design_parameters: dict | None = None,
    description: str | None = None,
) -> CaseVersion:
    """创建算例版本（同算例内 version_no 唯一性由路由层预检 + 数据库约束兜底）。"""
    version = CaseVersion(
        case_id=case_id,
        version_no=version_no,
        status=status,
        design_parameters=design_parameters,
        description=description,
    )
    session.add(version)
    await session.commit()
    await session.refresh(version)
    return version


async def get_case_version(session: AsyncSession, version_id: int) -> CaseVersion | None:
    """按主键查询。"""
    return await session.get(CaseVersion, version_id)


async def get_version_by_no(
    session: AsyncSession, case_id: int, version_no: str
) -> CaseVersion | None:
    """查询同算例下指定版本号（唯一性预检用）。"""
    stmt = select(CaseVersion).where(
        CaseVersion.case_id == case_id, CaseVersion.version_no == version_no
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_case_versions(
    session: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 100,
    case_id: int | None = None,
    status: str | None = None,
) -> Sequence[CaseVersion]:
    """分页查询版本，可选按算例/状态过滤。"""
    stmt = select(CaseVersion).order_by(CaseVersion.case_id, CaseVersion.id)
    if case_id is not None:
        stmt = stmt.where(CaseVersion.case_id == case_id)
    if status:
        stmt = stmt.where(CaseVersion.status == status)
    stmt = stmt.offset(offset).limit(limit)
    return (await session.execute(stmt)).scalars().all()


async def update_case_version(
    session: AsyncSession, version_id: int, values: dict
) -> CaseVersion | None:
    """按字典部分更新（updated_at 自动刷新）。不存在返回 None。"""
    version = await session.get(CaseVersion, version_id)
    if version is None:
        return None
    for key, value in values.items():
        if key in _EDITABLE:
            setattr(version, key, value)
    await session.commit()
    await session.refresh(version)
    return version


async def delete_case_version(session: AsyncSession, version_id: int) -> bool:
    """删除版本，级联删除其产物与 CFD 任务。不存在返回 False。"""
    version = await session.get(CaseVersion, version_id)
    if version is None:
        return False
    await session.delete(version)
    await session.commit()
    return True


# ==================== 血缘遍历 ====================
_EDGE_QUERY = (
    select(CfdTask.case_version_id, CaseArtifact.case_version_id).join(
        CaseArtifact, CfdTask.input_artifact_id == CaseArtifact.id
    )
)


async def get_upstream_version_ids(
    session: AsyncSession,
    version_id: int,
    *,
    exclude_task_id: int | None = None,
) -> list[int]:
    """收集全部上游版本（沿 消费->生产 边 BFS，去重、按发现顺序返回）。

    exclude_task_id：计算时忽略指定任务自身的旧依赖边（更新场景用）。
    """
    visited = {version_id}
    result: list[int] = []
    frontier = [version_id]
    while frontier:
        stmt = _EDGE_QUERY.where(CfdTask.case_version_id.in_(frontier))
        if exclude_task_id is not None:
            stmt = stmt.where(CfdTask.id != exclude_task_id)
        rows = (await session.execute(stmt)).all()
        next_frontier = []
        for _consumer, producer in rows:
            if producer not in visited:
                visited.add(producer)
                result.append(producer)
                next_frontier.append(producer)
        frontier = next_frontier
    return result


async def get_downstream_version_ids(session: AsyncSession, version_id: int) -> list[int]:
    """收集全部下游版本（沿 生产->消费 反向边 BFS，去重、按发现顺序返回）。"""
    visited = {version_id}
    result: list[int] = []
    frontier = [version_id]
    while frontier:
        stmt = _EDGE_QUERY.where(CaseArtifact.case_version_id.in_(frontier))
        rows = (await session.execute(stmt)).all()
        next_frontier = []
        for consumer, _producer in rows:
            if consumer not in visited:
                visited.add(consumer)
                result.append(consumer)
                next_frontier.append(consumer)
        frontier = next_frontier
    return result
