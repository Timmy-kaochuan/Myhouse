"""ExperimentRecord 异步 CRUD。"""
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.experiment_record import SOURCE_SIM, ExperimentRecord

_EDITABLE = {c.name for c in ExperimentRecord.__table__.columns} - {
    "id",
    "cfd_task_id",
    "source",
    "created_at",
}


async def create_experiment_record(
    session: AsyncSession,
    *,
    source: str = SOURCE_SIM,
    sample_tag: str,
    cfd_task_id: int | None = None,
    weight: float | None = None,
    test_data_key: str | None = None,
    input_x: dict | list | None = None,
    output_y_true: dict | list | None = None,
    output_y_pred: dict | list | None = None,
    residual: float | None = None,
    mlflow_run_id: str | None = None,
) -> ExperimentRecord:
    """创建保真样本实验记录（仿真样本挂任务，试验样本登记数据文件 key）。"""
    record = ExperimentRecord(
        cfd_task_id=cfd_task_id,
        source=source,
        sample_tag=sample_tag,
        weight=weight,
        test_data_key=test_data_key,
        input_x=input_x,
        output_y_true=output_y_true,
        output_y_pred=output_y_pred,
        residual=residual,
        mlflow_run_id=mlflow_run_id,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def get_experiment_record(
    session: AsyncSession, record_id: int
) -> ExperimentRecord | None:
    """按主键查询。"""
    return await session.get(ExperimentRecord, record_id)


async def list_experiment_records(
    session: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 100,
    cfd_task_id: int | None = None,
    source: str | None = None,
    sample_tag: str | None = None,
    mlflow_run_id: str | None = None,
) -> Sequence[ExperimentRecord]:
    """分页查询，可选按任务/来源/保真度/run_id 过滤。"""
    stmt = select(ExperimentRecord).order_by(ExperimentRecord.id)
    if cfd_task_id is not None:
        stmt = stmt.where(ExperimentRecord.cfd_task_id == cfd_task_id)
    if source:
        stmt = stmt.where(ExperimentRecord.source == source)
    if sample_tag:
        stmt = stmt.where(ExperimentRecord.sample_tag == sample_tag)
    if mlflow_run_id:
        stmt = stmt.where(ExperimentRecord.mlflow_run_id == mlflow_run_id)
    stmt = stmt.offset(offset).limit(limit)
    return (await session.execute(stmt)).scalars().all()


async def update_experiment_record(
    session: AsyncSession, record_id: int, values: dict
) -> ExperimentRecord | None:
    """按字典部分更新。不存在返回 None。"""
    record = await session.get(ExperimentRecord, record_id)
    if record is None:
        return None
    for key, value in values.items():
        if key in _EDITABLE:
            setattr(record, key, value)
    await session.commit()
    await session.refresh(record)
    return record


async def delete_experiment_record(session: AsyncSession, record_id: int) -> bool:
    """删除实验记录。不存在返回 False。"""
    record = await session.get(ExperimentRecord, record_id)
    if record is None:
        return False
    await session.delete(record)
    await session.commit()
    return True
