import io
import uuid
from typing import Protocol

from finrag_core.core.logging import get_logger
from finrag_core.domain.interfaces.document_repository import AbstractDocumentRepository
from finrag_core.domain.interfaces.object_storage import AbstractObjectStorage
from finrag_core.domain.models.document import (
    Document,
    DocumentCreate,
    DocumentStatus,
    DocumentType,
    DocumentUpdate,
)
from finrag_core.domain.models.user import User, UserRole

logger = get_logger(__name__)


class TaskQueueProtocol(Protocol):
    async def enqueue_document_processing(self, document_id: uuid.UUID, s3_key: str) -> None: ...
class DocumentService:
    def __init__(
        self,
        repository: AbstractDocumentRepository,
        storage: AbstractObjectStorage,
        task_queue: TaskQueueProtocol,
    ) -> None:
        self._repo = repository
        self._storage = storage
        self._task_queue = task_queue

    async def upload_document(
        self,
        file_data: bytes,
        filename: str,
        document_type: DocumentType,
        current_user: User,
    ) -> Document:
        s3_key = f"documents/{current_user.id}/{uuid.uuid4()}/{filename}"
        logger.info("uploading_document", user_id=str(current_user.id), filename=filename)

        await self._storage.upload(s3_key, file_data, "application/pdf")

        doc_create = DocumentCreate(
            filename=filename,
            document_type=document_type,
            owner_id=current_user.id,
        )
        document = await self._repo.create(doc_create, s3_key)

        await self._task_queue.enqueue_document_processing(document.id, s3_key)
        logger.info("document_processing_enqueued", document_id=str(document.id))

        return document

    async def get_document(self, document_id: uuid.UUID, current_user: User) -> Document | None:
        doc = await self._repo.get_by_id(document_id)
        if doc is None:
            return None
        if doc.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
            return None
        return doc

    async def list_documents(
        self, current_user: User, limit: int = 20, offset: int = 0
    ) -> tuple[list[Document], int]:
        if current_user.role == UserRole.ADMIN:
            docs = await self._repo.list_all(limit, offset)
            total = await self._repo.count_all()
        else:
            docs = await self._repo.list_by_owner(current_user.id, limit, offset)
            total = await self._repo.count_by_owner(current_user.id)
        return docs, total

    async def delete_document(self, document_id: uuid.UUID, current_user: User) -> bool:
        doc = await self.get_document(document_id, current_user)
        if doc is None:
            return False
        await self._storage.delete(doc.s3_key)
        deleted = await self._repo.delete(document_id)
        if deleted:
            logger.info(
                "document_deleted", document_id=str(document_id), user_id=str(current_user.id)
            )
        return deleted
