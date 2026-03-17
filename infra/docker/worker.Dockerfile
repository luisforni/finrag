FROM python:3.11-slim

RUN addgroup --system finrag && adduser --system --ingroup finrag finrag

WORKDIR /app

RUN pip install --no-cache-dir \
    "pydantic[email]>=2.7.0" "pydantic-settings>=2.3.0" \
    "python-jose[cryptography]>=3.3.0" "passlib[bcrypt]>=1.7.4" "structlog>=24.2.0" \
    "sqlalchemy>=2.0.30" "asyncpg>=0.29.0" \
    "boto3>=1.34.0" "chromadb>=0.5.0" \
    "pypdf>=4.2.0" "langchain-text-splitters>=0.2.0" \
    "redis[asyncio]>=5.0.0" "tenacity>=8.3.0" "arq>=0.26.0"

COPY packages/core/src/finrag_core ./finrag_core
COPY packages/infrastructure/src/finrag_infra ./finrag_infra
COPY packages/worker/src/finrag_worker ./finrag_worker

USER finrag

CMD ["python", "-m", "arq", "finrag_worker.main.WorkerSettings"]
