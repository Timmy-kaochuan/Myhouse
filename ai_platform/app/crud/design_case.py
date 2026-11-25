"""DesignCase 异步 CRUD。"""
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.design_case import CASE_STATUS_DRAFT, DesignCase

_EDITABLE = {c.name for c in DesignCase.__table__.columns} - {
    "id",
    "creator_id",
    "created_at",
    "updated_at",
}


async def create_design_case(
    session: AsyncSession,
    *,
    case_name: str,
    creator_id: int,
    case_version: str = "v1",
    description: str | None = None,
    design_parameters: dict | None = None,
    status: str = CASE_STATUS_DRAFT,
) -> DesignCase:
    """创建设计算例。"""
    case = DesignCase(
        case_name=case_name,
        creator_id=creator_id,
        case_version=case_version,
        description=description,
        design_parameters=design_parameters,
        status=status,
    )
    session.add(case)
    await session.commit()
    await session.refresh(case)
    return case


async def get_design_case(session: AsyncSession, case_id: int) -> DesignCase | None:
    """按主键查询。"""
    return await session.get(DesignCase, case_id)


async def list_design_cases(
    session: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 100,
    creator_id: int | None = None,
    status: str | None = None,
) -> Sequence[DesignCase]:
    """分页查询，可选按创建人/状态过滤。"""
    stmt = select(DesignCase).order_by(DesignCase.id)
    if creator_id is not None:
        stmt = stmt.where(DesignCase.creator_id == creator_id)
    if status:
        stmt = stmt.where(DesignCase.status == status)
    stmt = stmt.offset(offset).limit(limit)
    return (await session.execute(stmt)).scalars().all()


async def update_design_case(
    session: AsyncSession, case_id: int, values: dict
) -> DesignCase | None:
    """按字典部分更新（updated_at 自动刷新）。不存在返回 None。"""
    case = await session.get(DesignCase, case_id)
    if case is None:
        return None
    for key, value in values.items():
        if key in _EDITABLE:
            setattr(case, key, value)
    await session.commit()
    await session.refresh(case)
    return case


async def delete_design_case(session: AsyncSession, case_id: int) -> bool:
    """删除算例，级联删除其 CFD 任务与智能体运行记录。不存在返回 False。"""
    case = await session.get(DesignCase, case_id)
    if case is None:
        return False
    await session.delete(case)
    await session.commit()
    return True
