"""User 异步 CRUD。约定：函数内部 commit，调用方无需管理事务。"""
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import ROLE_VIEWER, User

# 允许通过 update 修改的列
_EDITABLE = {c.name for c in User.__table__.columns} - {"id", "created_at"}


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    display_name: str | None = None,
    role: str = ROLE_VIEWER,
) -> User:
    """创建用户。"""
    user = User(email=email, display_name=display_name, role=role)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_user(session: AsyncSession, user_id: int) -> User | None:
    """按主键查询。"""
    return await session.get(User, user_id)


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """按唯一邮箱查询。"""
    stmt = select(User).where(User.email == email)
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_users(
    session: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 100,
    role: str | None = None,
) -> Sequence[User]:
    """分页查询，可选按角色过滤。"""
    stmt = select(User).order_by(User.id)
    if role:
        stmt = stmt.where(User.role == role)
    stmt = stmt.offset(offset).limit(limit)
    return (await session.execute(stmt)).scalars().all()


async def update_user(session: AsyncSession, user_id: int, values: dict) -> User | None:
    """按字典部分更新，忽略非列字段。不存在返回 None。"""
    user = await session.get(User, user_id)
    if user is None:
        return None
    for key, value in values.items():
        if key in _EDITABLE:
            setattr(user, key, value)
    await session.commit()
    await session.refresh(user)
    return user


async def delete_user(session: AsyncSession, user_id: int) -> bool:
    """删除用户，级联删除其算例。不存在返回 False。"""
    user = await session.get(User, user_id)
    if user is None:
        return False
    await session.delete(user)
    await session.commit()
    return True
