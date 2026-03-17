from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_current_user
from app.domain.models.query import QueryRequest, QueryResponse
from app.domain.models.user import User
from app.domain.services.rag_service import RAGService

router = APIRouter(prefix="/queries", tags=["queries"])


def get_rag_service() -> RAGService:
    raise NotImplementedError("RAGService dependency not configured")


@router.post("/", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[RAGService, Depends(get_rag_service)],
) -> QueryResponse:
    """Ask a question against indexed financial documents using RAG."""
    return await service.query(request, current_user.id)
