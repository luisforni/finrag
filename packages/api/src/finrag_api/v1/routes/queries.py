from typing import Annotated

from fastapi import APIRouter, Depends

from finrag_api.dependencies import get_current_user
from finrag_core.domain.models.query import QueryRequest, QueryResponse
from finrag_core.domain.models.user import User
from finrag_core.services.rag_service import RAGService

router = APIRouter(prefix="/queries", tags=["queries"])


def get_rag_service() -> RAGService:
    raise NotImplementedError("RAGService not configured")


@router.post("/", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[RAGService, Depends(get_rag_service)],
) -> QueryResponse:
    """Ask a question against indexed financial documents using RAG."""
    return await service.query(request, current_user.id)
