import uuid
from datetime import datetime, timezone

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domain.interfaces.vector_store import AbstractVectorStore
from app.domain.models.query import QueryRequest, QueryResponse, SourceChunk

logger = get_logger(__name__)
settings = get_settings()


class RAGService:
    """Retrieval-Augmented Generation: retrieve context, then generate answer."""

    def __init__(
        self,
        vector_store: AbstractVectorStore,
        llm_client: "LLMClientProtocol",
    ) -> None:
        self._vector_store = vector_store
        self._llm = llm_client

    async def query(self, request: QueryRequest, user_id: uuid.UUID) -> QueryResponse:
        logger.info(
            "rag_query_start",
            user_id=str(user_id),
            question_length=len(request.question),
            document_ids=[str(d) for d in (request.document_ids or [])],
        )

        sources: list[SourceChunk] = await self._vector_store.similarity_search(
            query=request.question,
            top_k=request.top_k,
            document_ids=request.document_ids,
        )

        if not sources:
            return QueryResponse(
                id=uuid.uuid4(),
                question=request.question,
                answer="No relevant context found in the selected documents.",
                sources=[],
                created_at=datetime.now(timezone.utc),
                tokens_used=0,
            )

        context = self._build_context(sources)
        answer, tokens_used = await self._llm.generate(
            question=request.question,
            context=context,
        )

        logger.info(
            "rag_query_complete",
            user_id=str(user_id),
            tokens_used=tokens_used,
            sources_count=len(sources),
        )

        return QueryResponse(
            id=uuid.uuid4(),
            question=request.question,
            answer=answer,
            sources=sources,
            created_at=datetime.now(timezone.utc),
            tokens_used=tokens_used,
        )

    def _build_context(self, sources: list[SourceChunk]) -> str:
        parts = []
        for i, src in enumerate(sources, 1):
            parts.append(
                f"[Source {i} — {src.document_filename}, chunk {src.chunk_index}]\n{src.content}"
            )
        return "\n\n---\n\n".join(parts)


class LLMClientProtocol:
    async def generate(self, question: str, context: str) -> tuple[str, int]:
        raise NotImplementedError
