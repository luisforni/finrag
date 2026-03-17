from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.models.query import SourceChunk


class AbstractVectorStore(ABC):
    """Port: defines what the domain needs from the vector store."""

    @abstractmethod
    async def add_chunks(
        self,
        document_id: UUID,
        document_filename: str,
        chunks: list[str],
    ) -> int:
        ...

    @abstractmethod
    async def similarity_search(
        self,
        query: str,
        top_k: int,
        document_ids: list[UUID] | None = None,
    ) -> list[SourceChunk]:
        ...

    @abstractmethod
    async def delete_document(self, document_id: UUID) -> bool:
        ...
