import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app import crud
from app.db.base import Base
from app.main import app
from app.models import CaseVersion, User
from app.services.predictor import PredictorUnavailable, predict


def test_user_roundtrip() -> None:
    async def run() -> None:
        engine = create_async_engine(
            "sqlite+aiosqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            session.add(User(email="test@example.com", display_name="Test"))
            await session.commit()

            user = (await session.execute(select(User))).scalar_one()
            assert user.email == "test@example.com"
            assert user.created_at is not None

        await engine.dispose()

    asyncio.run(run())


def test_case_version_and_artifact_flow() -> None:
    """主档+版本+产物+CFD 任务挂版本+上游引用+环检测 全链路。"""

    async def run() -> None:
        engine = create_async_engine(
            "sqlite+aiosqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            user = User(email="test@example.com", display_name="Test")
            session.add(user)
            await session.commit()

            # 创建主档自动生成 v1
            case = await crud.create_design_case(
                session,
                case_name="透平叶片优化",
                creator_id=user.id,
                design_parameters={"pressure_ratio": 12.5},
            )
            versions = (
                await session.execute(select(CaseVersion).where(CaseVersion.case_id == case.id))
            ).scalars().all()
            assert len(versions) == 1
            v1 = versions[0]
            assert v1.version_no == "v1"
            assert v1.design_parameters == {"pressure_ratio": 12.5}

            # 新增 v2；版本号查询
            v2 = await crud.create_case_version(session, case_id=case.id, version_no="v2")
            assert (await crud.get_version_by_no(session, case.id, "v2")).id == v2.id

            # 产物登记 + CFD 任务挂 v2 并引用 v1 的产物
            mesh = await crud.create_case_artifact(
                session, case_version_id=v1.id, artifact_type="mesh", file_key="cases/1/v1/outputs/mesh.msh"
            )
            task = await crud.create_cfd_task(
                session, case_version_id=v2.id, task_name="流场计算", task_type="flow",
                input_artifact_id=mesh.id,
            )
            assert task.case_version_id == v2.id
            assert task.input_artifact_id == mesh.id

            # 血缘：v2 的上游 = [v1]，v1 的下游 = [v2]
            assert await crud.get_upstream_version_ids(session, v2.id) == [v1.id]
            assert await crud.get_downstream_version_ids(session, v1.id) == [v2.id]

            # 环检测：引用自身版本产物 / 引用下游产物 => 成环；正常上游引用 => 不成环
            result_v2 = await crud.create_case_artifact(
                session, case_version_id=v2.id, artifact_type="result", file_key="cases/1/v2/outputs/r.csv"
            )
            assert await crud.artifact_creates_cycle(session, version_id=v2.id, input_artifact_id=result_v2.id)
            assert await crud.artifact_creates_cycle(session, version_id=v1.id, input_artifact_id=result_v2.id)
            assert not await crud.artifact_creates_cycle(session, version_id=v2.id, input_artifact_id=mesh.id)

        await engine.dispose()

    asyncio.run(run())


def test_multi_fidelity_records_and_predict() -> None:
    """试验/仿真双来源样本入库规则 + 内嵌权重线性预测。"""

    async def run() -> None:
        engine = create_async_engine(
            "sqlite+aiosqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            user = User(email="test@example.com", display_name="Test")
            session.add(user)
            await session.commit()
            case = await crud.create_design_case(session, case_name="算例", creator_id=user.id)
            version = await crud.get_version_by_no(session, case.id, "v1")
            task = await crud.create_cfd_task(session, case_version_id=version.id, task_name="t", task_type="flow")

            # 仿真样本：挂任务
            sim = await crud.create_experiment_record(
                session, source="sim", sample_tag="low_fid", cfd_task_id=task.id,
                input_x=[1.0, 2.0], output_y_true=[3.0],
            )
            assert sim.source == "sim" and sim.cfd_task_id == task.id

            # 试验样本：不挂任务，登记数据文件 key + 更大权重
            test = await crud.create_experiment_record(
                session, source="test", sample_tag="high_fid", weight=1.0,
                test_data_key="tests/rig01/run002.csv", input_x=[1.0, 2.0], output_y_true=[3.1],
            )
            assert test.cfd_task_id is None and test.source == "test" and test.weight == 1.0

            # 内嵌线性权重预测
            model = await crud.create_proxy_model(
                session, model_name="线性代理", model_type="mlp", input_dim=2, output_dim=1,
                status="ready", weights_json={"type": "linear", "coef": [1.2, 0.8], "intercept": 0.5},
            )
            y, src = predict(model, [1.0, 2.0])
            assert y == [3.3] and src == "inline"

            # 维度不匹配 / 无权重 → 明确报错
            try:
                predict(model, [1.0])
                raise AssertionError("should raise")
            except PredictorUnavailable as exc:
                assert "维度不匹配" in str(exc)
            no_weight = await crud.create_proxy_model(
                session, model_name="无权重", model_type="kriging", input_dim=1, output_dim=1,
                status="ready", weight_key="minio://kriging.pkl",
            )
            try:
                predict(no_weight, [1.0])
                raise AssertionError("should raise")
            except PredictorUnavailable as exc:
                assert "MinIO" in str(exc)

        await engine.dispose()

    asyncio.run(run())


def test_health_db() -> None:
    response = TestClient(app).get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
