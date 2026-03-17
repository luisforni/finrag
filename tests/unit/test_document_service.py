import uuid
from datetime import datetime, timezone

import pytest

from finrag_core.domain.models.document import DocumentType
from finrag_core.domain.models.user import User, UserRole
from finrag_core.services.document_service import DocumentService


@pytest.fixture
def service(mock_doc_repo, mock_storage, mock_task_queue):
    return DocumentService(
        repository=mock_doc_repo,
        storage=mock_storage,
        task_queue=mock_task_queue,
    )


class TestUploadDocument:
    async def test_enqueues_task_and_returns_immediately(
        self,
        service,
        sample_user,
        sample_document,
        mock_doc_repo,
        mock_storage,
        mock_task_queue,
    ):
        mock_storage.upload.return_value = "s3_key"
        mock_doc_repo.create.return_value = sample_document
        mock_task_queue.enqueue_document_processing.return_value = None

        result = await service.upload_document(
            file_data=b"fake pdf",
            filename="test.pdf",
            document_type=DocumentType.CONTRACT,
            current_user=sample_user,
        )

        assert result == sample_document
        mock_storage.upload.assert_called_once()
        mock_doc_repo.create.assert_called_once()
        mock_task_queue.enqueue_document_processing.assert_called_once()

    async def test_no_inline_processing(
        self,
        service,
        sample_user,
        sample_document,
        mock_doc_repo,
        mock_storage,
        mock_task_queue,
    ):
        mock_storage.upload.return_value = "s3_key"
        mock_doc_repo.create.return_value = sample_document
        mock_task_queue.enqueue_document_processing.return_value = None

        await service.upload_document(
            file_data=b"any bytes",
            filename="report.pdf",
            document_type=DocumentType.RISK_REPORT,
            current_user=sample_user,
        )


class TestGetDocument:
    async def test_owner_can_access(self, service, sample_user, sample_document, mock_doc_repo):
        mock_doc_repo.get_by_id.return_value = sample_document
        assert await service.get_document(sample_document.id, sample_user) == sample_document

    async def test_other_user_cannot_access(self, service, sample_document, mock_doc_repo):
        other = User(
            id=uuid.uuid4(),
            email="other@bank.com",
            full_name="Other",
            role=UserRole.ANALYST,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        mock_doc_repo.get_by_id.return_value = sample_document
        assert await service.get_document(sample_document.id, other) is None

    async def test_admin_can_access_any(self, service, sample_document, mock_doc_repo):
        admin = User(
            id=uuid.uuid4(),
            email="admin@bank.com",
            full_name="Admin",
            role=UserRole.ADMIN,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        mock_doc_repo.get_by_id.return_value = sample_document
        assert await service.get_document(sample_document.id, admin) == sample_document

    async def test_returns_none_for_missing(self, service, sample_user, mock_doc_repo):
        mock_doc_repo.get_by_id.return_value = None
        assert await service.get_document(uuid.uuid4(), sample_user) is None


class TestDeleteDocument:
    async def test_successful_delete(
        self,
        service,
        sample_user,
        sample_document,
        mock_doc_repo,
        mock_storage,
    ):
        mock_doc_repo.get_by_id.return_value = sample_document
        mock_doc_repo.delete.return_value = True
        mock_storage.delete.return_value = True

        assert await service.delete_document(sample_document.id, sample_user) is True
        mock_storage.delete.assert_called_once_with(sample_document.s3_key)
