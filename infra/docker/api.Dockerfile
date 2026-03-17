FROM python:3.11-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir \
    "pydantic[email]>=2.7.0" "pydantic-settings>=2.3.0" \
    "python-jose[cryptography]>=3.3.0" "passlib[bcrypt]>=1.7.4" "structlog>=24.2.0" \
    "sqlalchemy>=2.0.30" "asyncpg>=0.29.0" "alembic>=1.13.1" \
    "boto3>=1.34.0" "chromadb>=0.5.0" "openai>=1.30.0" \
    "pypdf>=4.2.0" "langchain-text-splitters>=0.2.0" \
    "redis[asyncio]>=5.0.0" "tenacity>=8.3.0" \
    "fastapi>=0.111.0" "uvicorn[standard]>=0.29.0" \
    "python-multipart>=0.0.9" "slowapi>=0.1.9" "httpx>=0.27.0" "arq>=0.26.0"

FROM python:3.11-slim

RUN addgroup --system finrag && adduser --system --ingroup finrag finrag

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY packages/core/src/finrag_core ./finrag_core
COPY packages/infrastructure/src/finrag_infra ./finrag_infra
COPY packages/api/src/finrag_api ./finrag_api
COPY alembic/ ./alembic/
COPY alembic.ini ./

USER finrag

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["sh", "-c", "alembic upgrade head && uvicorn finrag_api.main:app --host 0.0.0.0 --port 8000 --workers 2"]
