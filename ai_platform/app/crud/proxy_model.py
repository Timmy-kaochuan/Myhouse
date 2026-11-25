"""ProxyModel 异步 CRUD。"""
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proxy_model import PM_STATUS_DRAFT, ProxyModel

_EDITABLE = {c.name for c in ProxyModel.__table__.columns} - {"id", "created_at"}


async def create_proxy_model(
    session: AsyncSession,
    *,
    model_name: str,
    model_type: str,
    input_dim: int,
    output_dim: int,
    model_version: str = "v1",
    metric: dict | None = None,
    weight_key: str | None = None,
    train_dataset_key: str | None = None,
    description: str | None = None,
    status: str = PM_STATUS_DRAFT,
) -> ProxyModel:
    """创建代理模型记录（权重/数据集只存 MinIO key）。"""
    model = ProxyModel(
        model_name=model_name,
        model_type=model_type,
        input_dim=input_dim,
        output_dim=output_dim,
        model_version=model_version,
        metric=metric,
        weight_key=weight_key,
        train_dataset_key=train_dataset_key,
        description=description,
        status=status,
    )
    session.add(model)
    await session.commit()
    await session.refresh(model)
    return model


async def get_proxy_model(session: AsyncSession, model_id: int) -> ProxyModel | None:
    """按主键查询。"""
    return await session.get(ProxyModel, model_id)


async def list_proxy_models(
    session: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 100,
    model_type: str | None = None,
    status: str | None = None,
) -> Sequence[ProxyModel]:
    """分页查询，可选按类型/状态过滤。"""
    stmt = select(ProxyModel).order_by(ProxyModel.id)
    if model_type:
        stmt = stmt.where(ProxyModel.model_type == model_type)
    if status:
        stmt = stmt.where(ProxyModel.status == status)
    stmt = stmt.offset(offset).limit(limit)
    return (await session.execute(stmt)).scalars().all()


async def update_proxy_model(
    session: AsyncSession, model_id: int, values: dict
) -> ProxyModel | None:
    """按字典部分更新。不存在返回 None。"""
    model = await session.get(ProxyModel, model_id)
    if model is None:
        return None
    for key, value in values.items():
        if key in _EDITABLE:
            setattr(model, key, value)
    await session.commit()
    await session.refresh(model)
    return model


async def delete_proxy_model(session: AsyncSession, model_id: int) -> bool:
    """删除代理模型，关联 CFD 任务的 proxy_model_id 由数据库置空。不存在返回 False。"""
    model = await session.get(ProxyModel, model_id)
    if model is None:
        return False
    await session.delete(model)
    await session.commit()
    return True
