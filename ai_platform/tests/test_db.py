import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.main import app
from app.models import User


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


def test_health_db() -> None:
    response = TestClient(app).get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
