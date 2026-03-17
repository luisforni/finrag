from contextlib import asynccontextmanager
from typing import AsyncGenerator

import chromadb
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.routes import auth, documents, queries
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.domain.services.document_service import DocumentService
from app.domain.services.rag_service import RAGService
from app.infrastructure.aws.s3_client import S3ObjectStorage
from app.infrastructure.openai_client import OpenAILLMClient
from app.infrastructure.pdf_extractor import PDFTextExtractor
from app.infrastructure.repositories.chroma_vector_store import ChromaVectorStore
from app.infrastructure.repositories.postgres_document_repo import (
    Base,
    PostgresDocumentRepository,
)

settings = get_settings()
configure_logging("DEBUG" if settings.debug else "INFO")
logger = get_logger(__name__)

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("finrag_startup", environment=settings.environment)

    # Database
    engine = create_async_engine(str(settings.database_url), echo=settings.debug)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Infrastructure adapters
    doc_repo = PostgresDocumentRepository(session_factory)
    chroma_client = await chromadb.AsyncHttpClient(
        host=settings.chroma_host, port=settings.chroma_port
    )
    vector_store = ChromaVectorStore(chroma_client, settings.chroma_collection_name)
    storage = S3ObjectStorage()
    extractor = PDFTextExtractor()
    llm_client = OpenAILLMClient()

    # Domain services
    doc_service = DocumentService(doc_repo, storage, vector_store, extractor)
    rag_service = RAGService(vector_store, llm_client)

    # Wire dependencies (SOLID: DIP)
    app.dependency_overrides[documents.get_document_service] = lambda: doc_service
    app.dependency_overrides[queries.get_rag_service] = lambda: rag_service

    yield

    await engine.dispose()
    logger.info("finrag_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="FinRAG — Financial Document Analysis API",
        description="RAG-powered API for querying financial documents in natural language.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Middlewares
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Routers
    app.include_router(auth.router, prefix=settings.api_v1_prefix)
    app.include_router(documents.router, prefix=settings.api_v1_prefix)
    app.include_router(queries.router, prefix=settings.api_v1_prefix)

    @app.get("/health", tags=["ops"])
    async def health() -> dict:
        return {"status": "ok", "service": settings.app_name}

    return app


app = create_app()
