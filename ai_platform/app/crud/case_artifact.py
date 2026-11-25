"""CaseArtifact 异步 CRUD。"""
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case_artifact import CaseArtifact

_EDITABLE = {c.name for c in CaseArtifact.__table__.columns} - {
    "id",
    "case_version_id",
    "created_at",
}


async def create_case_artifact(
    session: AsyncSession,
    *,
    case_version_id: int,
    artifact_type: str,
    file_key: str,
    description: str | None = None,
) -> CaseArtifact:
    """登记算例产物（二进制文件存 MinIO，这里只写对象 key）。"""
    artifact = CaseArtifact(
        case_version_id=case_version_id,
        artifact_type=artifact_type,
        file_key=file_key,
        description=description,
    )
    session.add(artifact)
    await session.commit()
    await session.refresh(artifact)
    return artifact


async def get_case_artifact(session: AsyncSession, artifact_id: int) -> CaseArtifact | None:
    """按主键查询。"""
    return await session.get(CaseArtifact, artifact_id)


async def list_case_artifacts(
    session: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 100,
    case_version_id: int | None = None,
    artifact_type: str | None = None,
) -> Sequence[CaseArtifact]:
    """分页查询产物，可选按版本/类型过滤。"""
    stmt = select(CaseArtifact).order_by(CaseArtifact.case_version_id, CaseArtifact.id)
    if case_version_id is not None:
        stmt = stmt.where(CaseArtifact.case_version_id == case_version_id)
    if artifact_type:
        stmt = stmt.where(CaseArtifact.artifact_type == artifact_type)
    stmt = stmt.offset(offset).limit(limit)
    return (await session.execute(stmt)).scalars().all()


async def update_case_artifact(
    session: AsyncSession, artifact_id: int, values: dict
) -> CaseArtifact | None:
    """按字典部分更新。不存在返回 None。"""
    artifact = await session.get(CaseArtifact, artifact_id)
    if artifact is None:
        return None
    for key, value in values.items():
        if key in _EDITABLE:
            setattr(artifact, key, value)
    await session.commit()
    await session.refresh(artifact)
    return artifact


async def delete_case_artifact(session: AsyncSession, artifact_id: int) -> bool:
    """删除产物登记；引用它的 CFD 任务由数据库将 input_artifact_id 置空。"""
    artifact = await session.get(CaseArtifact, artifact_id)
    if artifact is None:
        return False
    await session.delete(artifact)
    await session.commit()
    return True
