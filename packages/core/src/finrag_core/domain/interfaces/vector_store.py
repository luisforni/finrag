from abc import ABC, abstractmethod
from uuid import UUID

from finrag_core.domain.models.query import SourceChunk


class AbstractVectorStore(ABC):
    @abstractmethod
    async def add_chunks(
        self, document_id: UUID, document_filename: str, chunks: list[str]
    ) -> int: ...

    @abstractmethod
    async def similarity_search(
        self, query: str, top_k: int, document_ids: list[UUID] | None = None
    ) -> list[SourceChunk]: ...

    @abstractmethod
    async def delete_document(self, document_id: UUID) -> bool: ...
