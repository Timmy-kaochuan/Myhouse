"""DesignCase（主档）异步 CRUD：创建主档时自动生成 v1 版本。"""
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case_version import VERSION_STATUS_DRAFT, CaseVersion
from app.models.design_case import DesignCase

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
    description: str | None = None,
    parent_case_id: int | None = None,
    design_parameters: dict | None = None,
    version_no: str = "v1",
) -> DesignCase:
    """创建设计算例主档 + 默认 v1 版本（单事务提交）。"""
    case = DesignCase(
        case_name=case_name,
        creator_id=creator_id,
        description=description,
        parent_case_id=parent_case_id,
    )
    session.add(case)
    await session.flush()  # 拿到主档 id 再建版本
    version = CaseVersion(
        case_id=case.id,
        version_no=version_no,
        status=VERSION_STATUS_DRAFT,
        design_parameters=design_parameters,
    )
    session.add(version)
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
) -> Sequence[DesignCase]:
    """分页查询主档，可选按创建人过滤。"""
    stmt = select(DesignCase).order_by(DesignCase.id)
    if creator_id is not None:
        stmt = stmt.where(DesignCase.creator_id == creator_id)
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
    """删除主档，级联删除其版本、产物、CFD 任务与智能体运行记录。不存在返回 False。"""
    case = await session.get(DesignCase, case_id)
    if case is None:
        return False
    await session.delete(case)
    await session.commit()
    return True
