FROM python:3.11-slim AS builder

WORKDIR /app

COPY pyproject.toml ./

RUN pip install --no-cache-dir \
    "fastapi>=0.111.0" \
    "uvicorn[standard]>=0.29.0" \
    "pydantic[email]>=2.7.0" \
    "pydantic-settings>=2.3.0" \
    "sqlalchemy>=2.0.30" \
    "asyncpg>=0.29.0" \
    "alembic>=1.13.1" \
    "python-jose[cryptography]>=3.3.0" \
    "passlib[bcrypt]>=1.7.4" \
    "python-multipart>=0.0.9" \
    "boto3>=1.34.0" \
    "chromadb>=0.5.0" \
    "openai>=1.30.0" \
    "pypdf>=4.2.0" \
    "langchain-text-splitters>=0.2.0" \
    "slowapi>=0.1.9" \
    "structlog>=24.2.0" \
    "httpx>=0.27.0"

FROM python:3.11-slim

RUN addgroup --system finrag && adduser --system --ingroup finrag finrag

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY app/ ./app/

USER finrag

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
