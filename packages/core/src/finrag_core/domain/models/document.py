from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class DocumentType(str, Enum):
    CONTRACT = "contract"
    RISK_REPORT = "risk_report"
    STATEMENT = "statement"
    OTHER = "other"


class Document(BaseModel):
    id: UUID
    filename: str
    s3_key: str
    document_type: DocumentType
    status: DocumentStatus
    owner_id: UUID
    created_at: datetime
    updated_at: datetime
    chunk_count: int = 0
    error_message: str | None = None


class DocumentCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    document_type: DocumentType
    owner_id: UUID


class DocumentUpdate(BaseModel):
    status: DocumentStatus | None = None
    chunk_count: int | None = None
    error_message: str | None = None
