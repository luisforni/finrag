from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=5, max_length=2000)
    document_ids: list[UUID] | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class SourceChunk(BaseModel):
    document_id: UUID
    document_filename: str
    chunk_index: int
    content: str
    score: float


class QueryResponse(BaseModel):
    id: UUID
    question: str
    answer: str
    sources: list[SourceChunk]
    created_at: datetime
    tokens_used: int
