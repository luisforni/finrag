import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from finrag_core.domain.models.document import (
    DocumentCreate,
    DocumentStatus,
    DocumentType,
    DocumentUpdate,
)
from finrag_infra.db.base import Base
from finrag_infra.db.document_repo import DocumentORM, PostgresDocumentRepository  # noqa: F401
from finrag_infra.db.query_log_repo import QueryLogORM  # noqa: F401
from finrag_infra.db.user_repo import UserORM  # noqa: F401


@pytest.fixture(scope="module")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture(scope="module")
async def session_factory(postgres_container):
    url = postgres_container.get_connection_url().replace(
        "postgresql+psycopg2", "postgresql+asyncpg"
    )
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.fixture
def repo(session_factory):
    return PostgresDocumentRepository(session_factory)


class TestPostgresDocumentRepository:
    async def test_create_and_get(self, repo):
        owner = uuid.uuid4()
        doc = await repo.create(
            DocumentCreate(
                filename="test.pdf", document_type=DocumentType.CONTRACT, owner_id=owner
            ),
            s3_key=f"docs/{owner}/test.pdf",
        )
        assert doc.status == DocumentStatus.PENDING
        fetched = await repo.get_by_id(doc.id)
        assert fetched is not None
        assert fetched.id == doc.id

    async def test_update_status(self, repo):
        owner = uuid.uuid4()
        doc = await repo.create(
            DocumentCreate(
                filename="r.pdf", document_type=DocumentType.RISK_REPORT, owner_id=owner
            ),
            s3_key=f"docs/{owner}/r.pdf",
        )
        updated = await repo.update(
            doc.id, DocumentUpdate(status=DocumentStatus.READY, chunk_count=5)
        )
        assert updated.status == DocumentStatus.READY
        assert updated.chunk_count == 5

    async def test_list_and_count_by_owner(self, repo):
        owner = uuid.uuid4()
        for i in range(3):
            await repo.create(
                DocumentCreate(
                    filename=f"d{i}.pdf", document_type=DocumentType.STATEMENT, owner_id=owner
                ),
                s3_key=f"docs/{owner}/d{i}.pdf",
            )
        assert len(await repo.list_by_owner(owner, limit=10, offset=0)) == 3
        assert await repo.count_by_owner(owner) == 3

    async def test_delete(self, repo):
        owner = uuid.uuid4()
        doc = await repo.create(
            DocumentCreate(filename="del.pdf", document_type=DocumentType.OTHER, owner_id=owner),
            s3_key=f"docs/{owner}/del.pdf",
        )
        assert await repo.delete(doc.id) is True
        assert await repo.get_by_id(doc.id) is None

    async def test_get_missing_returns_none(self, repo):
        assert await repo.get_by_id(uuid.uuid4()) is None
