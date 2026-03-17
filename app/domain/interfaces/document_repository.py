from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.models.document import Document, DocumentCreate, DocumentUpdate


class AbstractDocumentRepository(ABC):
    """Port: defines what the domain needs from persistence."""

    @abstractmethod
    async def create(self, data: DocumentCreate, s3_key: str) -> Document:
        ...

    @abstractmethod
    async def get_by_id(self, document_id: UUID) -> Document | None:
        ...

    @abstractmethod
    async def list_by_owner(self, owner_id: UUID, limit: int, offset: int) -> list[Document]:
        ...

    @abstractmethod
    async def update(self, document_id: UUID, data: DocumentUpdate) -> Document | None:
        ...

    @abstractmethod
    async def delete(self, document_id: UUID) -> bool:
        ...

    @abstractmethod
    async def count_by_owner(self, owner_id: UUID) -> int:
        ...
