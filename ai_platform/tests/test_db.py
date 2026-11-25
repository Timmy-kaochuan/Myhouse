import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app import crud
from app.db.base import Base
from app.main import app
from app.models import CaseVersion, User


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


def test_health_db() -> None:
    response = TestClient(app).get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
