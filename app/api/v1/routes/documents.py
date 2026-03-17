import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.api.v1.dependencies import get_current_user
from app.domain.models.document import Document, DocumentType
from app.domain.models.user import User
from app.domain.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


def get_document_service() -> DocumentService:
    """Overridden in tests and main.py via app.dependency_overrides."""
    raise NotImplementedError("DocumentService dependency not configured")


@router.post("/", response_model=Document, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: Annotated[UploadFile, File(description="PDF document")],
    document_type: Annotated[DocumentType, Form()],
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> Document:
    """Upload and index a financial document (PDF)."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted",
        )

    max_size = 50 * 1024 * 1024  # 50 MB
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds 50 MB limit",
        )

    import io

    return await service.upload_document(
        file=io.BytesIO(content),
        filename=file.filename,
        document_type=document_type,
        current_user=current_user,
    )


@router.get("/", response_model=dict)
async def list_documents(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """List documents owned by the current user."""
    docs, total = await service.list_documents(current_user, limit, offset)
    return {"items": docs, "total": total, "limit": limit, "offset": offset}


@router.get("/{document_id}", response_model=Document)
async def get_document(
    document_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> Document:
    """Retrieve a document by ID."""
    doc = await service.get_document(document_id, current_user)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> None:
    """Delete a document and its vector embeddings."""
    deleted = await service.delete_document(document_id, current_user)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
