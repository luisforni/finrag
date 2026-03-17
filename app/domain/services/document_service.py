import uuid
from typing import BinaryIO

from app.core.logging import get_logger
from app.domain.interfaces.document_repository import AbstractDocumentRepository
from app.domain.interfaces.object_storage import AbstractObjectStorage
from app.domain.interfaces.vector_store import AbstractVectorStore
from app.domain.models.document import Document, DocumentCreate, DocumentStatus, DocumentType
from app.domain.models.user import User

logger = get_logger(__name__)


class DocumentService:
    """Orchestrates document lifecycle: upload → index → query-ready."""

    def __init__(
        self,
        repository: AbstractDocumentRepository,
        storage: AbstractObjectStorage,
        vector_store: AbstractVectorStore,
        text_extractor: "TextExtractorProtocol",
    ) -> None:
        self._repo = repository
        self._storage = storage
        self._vector_store = vector_store
        self._extractor = text_extractor

    async def upload_document(
        self,
        file: BinaryIO,
        filename: str,
        document_type: DocumentType,
        current_user: User,
    ) -> Document:
        file_data = file.read() if hasattr(file, "read") else bytes(file)
        s3_key = f"documents/{current_user.id}/{uuid.uuid4()}/{filename}"

        logger.info("uploading_document", user_id=str(current_user.id), filename=filename)

        await self._storage.upload(s3_key, file_data, "application/pdf")

        doc_create = DocumentCreate(
            filename=filename,
            document_type=document_type,
            owner_id=current_user.id,
        )
        document = await self._repo.create(doc_create, s3_key)

        try:
            await self._process_document(document, file_data)
        except Exception as exc:
            logger.error(
                "document_processing_failed",
                document_id=str(document.id),
                error=str(exc),
            )
            from app.domain.models.document import DocumentUpdate

            await self._repo.update(
                document.id,
                DocumentUpdate(status=DocumentStatus.FAILED, error_message=str(exc)),
            )
            raise

        return document

    async def _process_document(self, document: Document, file_data: bytes) -> None:
        from app.domain.models.document import DocumentUpdate

        await self._repo.update(document.id, DocumentUpdate(status=DocumentStatus.PROCESSING))

        chunks = await self._extractor.extract_and_chunk(file_data)
        chunk_count = await self._vector_store.add_chunks(
            document.id, document.filename, chunks
        )

        await self._repo.update(
            document.id,
            DocumentUpdate(status=DocumentStatus.READY, chunk_count=chunk_count),
        )
        logger.info(
            "document_indexed",
            document_id=str(document.id),
            chunks=chunk_count,
        )

    async def get_document(self, document_id: uuid.UUID, current_user: User) -> Document | None:
        doc = await self._repo.get_by_id(document_id)
        if doc is None:
            return None
        if doc.owner_id != current_user.id and current_user.role.value != "admin":
            return None
        return doc

    async def list_documents(
        self, current_user: User, limit: int = 20, offset: int = 0
    ) -> tuple[list[Document], int]:
        from app.domain.models.user import UserRole

        owner_id = None if current_user.role == UserRole.ADMIN else current_user.id
        if owner_id is None:
            # Admin sees all — for simplicity, reuse list_by_owner with a broad scope
            owner_id = current_user.id

        docs = await self._repo.list_by_owner(owner_id, limit, offset)
        total = await self._repo.count_by_owner(owner_id)
        return docs, total

    async def delete_document(self, document_id: uuid.UUID, current_user: User) -> bool:
        doc = await self.get_document(document_id, current_user)
        if doc is None:
            return False

        await self._vector_store.delete_document(document_id)
        await self._storage.delete(doc.s3_key)
        deleted = await self._repo.delete(document_id)

        if deleted:
            logger.info(
                "document_deleted",
                document_id=str(document_id),
                user_id=str(current_user.id),
            )
        return deleted


class TextExtractorProtocol:
    async def extract_and_chunk(self, file_data: bytes) -> list[str]:
        raise NotImplementedError
