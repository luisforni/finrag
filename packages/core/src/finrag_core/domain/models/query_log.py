from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class QueryLog(BaseModel):
    id: UUID
    user_id: UUID
    question: str
    answer: str
    document_ids: list[UUID]
    sources_count: int
    tokens_used: int
    latency_ms: int
    created_at: datetime


class QueryLogCreate(BaseModel):
    user_id: UUID
    question: str
    answer: str
    document_ids: list[UUID]
    sources_count: int
    tokens_used: int
    latency_ms: int
