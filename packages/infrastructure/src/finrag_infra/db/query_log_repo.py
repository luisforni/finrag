import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import Integer, String, Text, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from finrag_core.domain.interfaces.query_log_repository import AbstractQueryLogRepository
from finrag_core.domain.models.query_log import QueryLog, QueryLogCreate
from finrag_infra.db.base import Base


class QueryLogORM(Base):
    __tablename__ = "query_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    document_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    sources_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))


def _to_domain(orm: QueryLogORM) -> QueryLog:
    return QueryLog(
        id=orm.id,
        user_id=orm.user_id,
        question=orm.question,
        answer=orm.answer,
        document_ids=[uuid.UUID(d) for d in json.loads(orm.document_ids_json)],
        sources_count=orm.sources_count,
        tokens_used=orm.tokens_used,
        latency_ms=orm.latency_ms,
        created_at=orm.created_at,
    )


class PostgresQueryLogRepository(AbstractQueryLogRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def create(self, data: QueryLogCreate) -> QueryLog:
        async with self._sf() as session:
            orm = QueryLogORM(
                id=uuid.uuid4(),
                user_id=data.user_id,
                question=data.question,
                answer=data.answer,
                document_ids_json=json.dumps([str(d) for d in data.document_ids]),
                sources_count=data.sources_count,
                tokens_used=data.tokens_used,
                latency_ms=data.latency_ms,
                created_at=datetime.now(timezone.utc),
            )
            session.add(orm)
            await session.commit()
            await session.refresh(orm)
            return _to_domain(orm)

    async def list_by_user(self, user_id: uuid.UUID, limit: int, offset: int) -> list[QueryLog]:
        async with self._sf() as session:
            result = await session.execute(
                select(QueryLogORM)
                .where(QueryLogORM.user_id == user_id)
                .order_by(QueryLogORM.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            return [_to_domain(row) for row in result.scalars()]
