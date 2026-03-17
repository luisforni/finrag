import uuid
from typing import Any

from arq import ArqRedis

from finrag_core.core.config import get_settings
from finrag_core.core.logging import get_logger
from finrag_core.domain.models.document import DocumentStatus, DocumentUpdate
from finrag_infra.pdf.extractor import PDFTextExtractor
from finrag_infra.storage.s3_client import S3ObjectStorage

logger = get_logger(__name__)
settings = get_settings()


async def process_document(ctx: dict[str, Any], document_id: str, s3_key: str) -> None:
    """ARQ task: download PDF from S3, extract text, index in Chroma, update DB status."""
    doc_uuid = uuid.UUID(document_id)
    doc_repo = ctx["doc_repo"]
    vector_store = ctx["vector_store"]
    storage = ctx["storage"]
    extractor = ctx["extractor"]

    logger.info("worker_processing_start", document_id=document_id)

    try:
        await doc_repo.update(doc_uuid, DocumentUpdate(status=DocumentStatus.PROCESSING))

        file_data = await storage.download(s3_key)
        chunks = await extractor.extract_and_chunk(file_data)

        doc = await doc_repo.get_by_id(doc_uuid)
        filename = doc.filename if doc else s3_key.split("/")[-1]

        chunk_count = await vector_store.add_chunks(doc_uuid, filename, chunks)

        await doc_repo.update(
            doc_uuid,
            DocumentUpdate(status=DocumentStatus.READY, chunk_count=chunk_count),
        )
        logger.info("worker_processing_complete", document_id=document_id, chunks=chunk_count)

    except Exception as exc:
        logger.error("worker_processing_failed", document_id=document_id, error=str(exc))
        await doc_repo.update(
            doc_uuid,
            DocumentUpdate(status=DocumentStatus.FAILED, error_message=str(exc)),
        )
        raise
