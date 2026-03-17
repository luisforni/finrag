from contextlib import asynccontextmanager
from typing import AsyncGenerator

import chromadb
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from finrag_api.middleware.correlation_id import CorrelationIdMiddleware
from finrag_api.v1.routes import auth, documents, queries
from finrag_core.core.config import get_settings
from finrag_core.core.logging import configure_logging, get_logger
from finrag_core.services.document_service import DocumentService, TaskQueueProtocol
from finrag_core.services.rag_service import RAGService
from finrag_core.services.user_service import UserService
from finrag_infra.cache.redis_client import close_redis, get_redis
from finrag_infra.db.document_repo import PostgresDocumentRepository
from finrag_infra.db.query_log_repo import PostgresQueryLogRepository
from finrag_infra.db.user_repo import PostgresUserRepository
from finrag_infra.llm.openai_client import OpenAILLMClient
from finrag_infra.storage.s3_client import S3ObjectStorage
from finrag_infra.vector.chroma_store import ChromaVectorStore

settings = get_settings()
configure_logging("DEBUG" if settings.debug else "INFO")
logger = get_logger(__name__)


class ARQTaskQueue(TaskQueueProtocol):
    """Adapts ARQ pool to the TaskQueueProtocol port."""

    def __init__(self, pool) -> None:
        self._pool = pool

    async def enqueue_document_processing(self, document_id, s3_key: str) -> None:
        await self._pool.enqueue_job("process_document", str(document_id), s3_key)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("finrag_api_startup", environment=settings.environment)

    engine = create_async_engine(
        str(settings.database_url),
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
        echo=settings.debug,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    await get_redis()
    arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))

    chroma_client = await chromadb.AsyncHttpClient(
        host=settings.chroma_host, port=settings.chroma_port
    )

    doc_repo = PostgresDocumentRepository(session_factory)
    user_repo = PostgresUserRepository(session_factory)
    query_log_repo = PostgresQueryLogRepository(session_factory)
    vector_store = ChromaVectorStore(chroma_client, settings.chroma_collection_name)
    storage = S3ObjectStorage()
    llm_client = OpenAILLMClient()
    task_queue = ARQTaskQueue(arq_pool)

    doc_service = DocumentService(doc_repo, storage, task_queue)
    rag_service = RAGService(vector_store, llm_client, query_log_repo)
    user_service = UserService(user_repo)

    app.dependency_overrides[documents.get_document_service] = lambda: doc_service
    app.dependency_overrides[queries.get_rag_service] = lambda: rag_service
    app.dependency_overrides[auth.get_user_service] = lambda: user_service

    yield

    await arq_pool.aclose()
    await close_redis()
    await engine.dispose()
    logger.info("finrag_api_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="FinRAG — Financial Document Analysis API",
        description="RAG-powered API for querying financial documents in natural language.",
        version="0.2.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    limiter = Limiter(key_func=get_remote_address, storage_uri=settings.redis_url)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(auth.router, prefix=settings.api_v1_prefix)
    app.include_router(documents.router, prefix=settings.api_v1_prefix)
    app.include_router(queries.router, prefix=settings.api_v1_prefix)

    @app.get("/health", tags=["ops"])
    async def health() -> dict:
        return {"status": "ok", "service": settings.app_name, "version": "0.2.0"}

    return app


app = create_app()
