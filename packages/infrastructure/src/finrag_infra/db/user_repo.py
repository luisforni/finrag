import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, String, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from finrag_core.core.security import hash_password
from finrag_core.domain.interfaces.user_repository import AbstractUserRepository
from finrag_core.domain.models.user import UserCreate, UserInDB, UserRole
from finrag_infra.db.base import Base


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=UserRole.ANALYST)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))


def _to_domain(orm: UserORM) -> UserInDB:
    return UserInDB(
        id=orm.id,
        email=orm.email,
        full_name=orm.full_name,
        role=UserRole(orm.role),
        is_active=orm.is_active,
        created_at=orm.created_at,
        hashed_password=orm.hashed_password,
    )


class PostgresUserRepository(AbstractUserRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def create(self, data: UserCreate) -> UserInDB:
        async with self._sf() as session:
            orm = UserORM(
                id=uuid.uuid4(),
                email=data.email,
                full_name=data.full_name,
                hashed_password=hash_password(data.password),
                role=data.role.value,
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
            session.add(orm)
            await session.commit()
            await session.refresh(orm)
            return _to_domain(orm)

    async def get_by_id(self, user_id: uuid.UUID) -> UserInDB | None:
        async with self._sf() as session:
            result = await session.execute(select(UserORM).where(UserORM.id == user_id))
            orm = result.scalar_one_or_none()
            return _to_domain(orm) if orm else None

    async def get_by_email(self, email: str) -> UserInDB | None:
        async with self._sf() as session:
            result = await session.execute(select(UserORM).where(UserORM.email == email))
            orm = result.scalar_one_or_none()
            return _to_domain(orm) if orm else None

    async def exists_by_email(self, email: str) -> bool:
        return await self.get_by_email(email) is not None
