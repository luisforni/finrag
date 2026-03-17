import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from finrag_core.core.security import hash_password
from finrag_core.domain.models.document import Document, DocumentStatus, DocumentType
from finrag_core.domain.models.query import SourceChunk
from finrag_core.domain.models.user import User, UserInDB, UserRole


@pytest.fixture
def sample_user() -> User:
    return User(
        id=uuid.uuid4(),
        email="analyst@bank.com",
        full_name="Ana Pérez",
        role=UserRole.ANALYST,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_user_in_db(sample_user: User) -> UserInDB:
    return UserInDB(**sample_user.model_dump(), hashed_password=hash_password("password123"))


@pytest.fixture
def sample_document(sample_user: User) -> Document:
    return Document(
        id=uuid.uuid4(),
        filename="contrato_2024.pdf",
        s3_key=f"documents/{sample_user.id}/uuid/contrato_2024.pdf",
        document_type=DocumentType.CONTRACT,
        status=DocumentStatus.READY,
        owner_id=sample_user.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        chunk_count=10,
    )


@pytest.fixture
def sample_source(sample_document: Document) -> SourceChunk:
    return SourceChunk(
        document_id=sample_document.id,
        document_filename=sample_document.filename,
        chunk_index=0,
        content="El ratio de cobertura de liquidez es del 145%.",
        score=0.92,
    )


@pytest.fixture
def mock_doc_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_user_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_vector_store() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_storage() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_task_queue() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_llm() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_query_log_repo() -> AsyncMock:
    return AsyncMock()
