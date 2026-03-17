import chromadb
from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from finrag_core.core.config import get_settings
from finrag_core.core.logging import configure_logging, get_logger
from finrag_infra.db.document_repo import PostgresDocumentRepository
from finrag_infra.pdf.extractor import PDFTextExtractor
from finrag_infra.storage.s3_client import S3ObjectStorage
from finrag_infra.vector.chroma_store import ChromaVectorStore
from finrag_worker.tasks.document_tasks import process_document

settings = get_settings()
configure_logging("DEBUG" if settings.debug else "INFO")
logger = get_logger(__name__)


async def startup(ctx: dict) -> None:
    logger.info("worker_startup")
    engine = create_async_engine(
        str(settings.database_url),
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    chroma_client = await chromadb.AsyncHttpClient(
        host=settings.chroma_host, port=settings.chroma_port
    )

    ctx["doc_repo"] = PostgresDocumentRepository(session_factory)
    ctx["vector_store"] = ChromaVectorStore(chroma_client, settings.chroma_collection_name)
    ctx["storage"] = S3ObjectStorage()
    ctx["extractor"] = PDFTextExtractor()
    ctx["engine"] = engine


async def shutdown(ctx: dict) -> None:
    await ctx["engine"].dispose()
    logger.info("worker_shutdown")


class WorkerSettings:
    functions = [process_document]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    job_timeout = 300  # 5 minutes max per document
