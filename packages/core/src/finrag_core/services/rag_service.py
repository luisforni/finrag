import time
import uuid
from datetime import datetime, timezone

from finrag_core.core.logging import get_logger
from finrag_core.domain.interfaces.llm_client import AbstractLLMClient
from finrag_core.domain.interfaces.query_log_repository import AbstractQueryLogRepository
from finrag_core.domain.interfaces.vector_store import AbstractVectorStore
from finrag_core.domain.models.query import QueryRequest, QueryResponse, SourceChunk
from finrag_core.domain.models.query_log import QueryLogCreate

logger = get_logger(__name__)


class RAGService:
    def __init__(
        self,
        vector_store: AbstractVectorStore,
        llm_client: AbstractLLMClient,
        query_log_repo: AbstractQueryLogRepository,
    ) -> None:
        self._vector_store = vector_store
        self._llm = llm_client
        self._query_log_repo = query_log_repo

    async def query(self, request: QueryRequest, user_id: uuid.UUID) -> QueryResponse:
        start = time.monotonic()
        logger.info("rag_query_start", user_id=str(user_id), question_len=len(request.question))

        sources: list[SourceChunk] = await self._vector_store.similarity_search(
            query=request.question,
            top_k=request.top_k,
            document_ids=request.document_ids,
        )

        if not sources:
            answer = "No relevant context found in the selected documents."
            tokens_used = 0
        else:
            context = self._build_context(sources)
            answer, tokens_used = await self._llm.generate(
                question=request.question, context=context
            )

        latency_ms = int((time.monotonic() - start) * 1000)
        response_id = uuid.uuid4()

        await self._query_log_repo.create(
            QueryLogCreate(
                user_id=user_id,
                question=request.question,
                answer=answer,
                document_ids=request.document_ids or [],
                sources_count=len(sources),
                tokens_used=tokens_used,
                latency_ms=latency_ms,
            )
        )

        logger.info(
            "rag_query_complete", user_id=str(user_id), tokens=tokens_used, latency_ms=latency_ms
        )

        return QueryResponse(
            id=response_id,
            question=request.question,
            answer=answer,
            sources=sources,
            created_at=datetime.now(timezone.utc),
            tokens_used=tokens_used,
        )

    def _build_context(self, sources: list[SourceChunk]) -> str:
        parts = [
            f"[Source {i} — {s.document_filename}, chunk {s.chunk_index}]\n{s.content}"
            for i, s in enumerate(sources, 1)
        ]
        return "\n\n---\n\n".join(parts)
