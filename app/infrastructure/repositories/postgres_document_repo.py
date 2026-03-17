import uuid
from datetime import datetime, timezone

from sqlalchemy import Integer, String, delete, func, select, update
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain.interfaces.document_repository import AbstractDocumentRepository
from app.domain.models.document import (
    Document,
    DocumentCreate,
    DocumentStatus,
    DocumentType,
    DocumentUpdate,
)


class Base(DeclarativeBase):
    pass


class DocumentORM(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=DocumentStatus.PENDING)
    owner_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)


def _orm_to_domain(orm: DocumentORM) -> Document:
    return Document(
        id=orm.id,
        filename=orm.filename,
        s3_key=orm.s3_key,
        document_type=DocumentType(orm.document_type),
        status=DocumentStatus(orm.status),
        owner_id=orm.owner_id,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        chunk_count=orm.chunk_count,
        error_message=orm.error_message,
    )


class PostgresDocumentRepository(AbstractDocumentRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(self, data: DocumentCreate, s3_key: str) -> Document:
        async with self._session_factory() as session:
            orm = DocumentORM(
                id=uuid.uuid4(),
                filename=data.filename,
                s3_key=s3_key,
                document_type=data.document_type.value,
                status=DocumentStatus.PENDING.value,
                owner_id=data.owner_id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(orm)
            await session.commit()
            await session.refresh(orm)
            return _orm_to_domain(orm)

    async def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(DocumentORM).where(DocumentORM.id == document_id)
            )
            orm = result.scalar_one_or_none()
            return _orm_to_domain(orm) if orm else None

    async def list_by_owner(
        self, owner_id: uuid.UUID, limit: int, offset: int
    ) -> list[Document]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(DocumentORM)
                .where(DocumentORM.owner_id == owner_id)
                .order_by(DocumentORM.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            return [_orm_to_domain(row) for row in result.scalars()]

    async def update(self, document_id: uuid.UUID, data: DocumentUpdate) -> Document | None:
        async with self._session_factory() as session:
            values = {k: v for k, v in data.model_dump(exclude_none=True).items()}
            values["updated_at"] = datetime.now(timezone.utc)
            await session.execute(
                update(DocumentORM).where(DocumentORM.id == document_id).values(**values)
            )
            await session.commit()
            return await self.get_by_id(document_id)

    async def delete(self, document_id: uuid.UUID) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(
                delete(DocumentORM).where(DocumentORM.id == document_id)
            )
            await session.commit()
            return result.rowcount > 0

    async def count_by_owner(self, owner_id: uuid.UUID) -> int:
        async with self._session_factory() as session:
            result = await session.execute(
                select(func.count()).select_from(DocumentORM).where(
                    DocumentORM.owner_id == owner_id
                )
            )
            return result.scalar_one()
