# FinRAG — Financial Document Analysis API

RAG-powered API that lets bank analysts upload financial PDFs (contracts, risk reports, statements) and query them in natural language via GPT-4o-mini.

## Architecture

Monorepo with 4 Python packages following hexagonal architecture (ports & adapters):

```
packages/
├── core/          # finrag-core  — domain models, abstract interfaces, services
├── infrastructure/# finrag-infra — SQLAlchemy, ChromaDB, S3, Redis, OpenAI adapters
├── api/           # finrag-api   — FastAPI HTTP layer, JWT auth, rate limiting
└── worker/        # finrag-worker — ARQ async worker for PDF processing
```

Document uploads return `202 Accepted` immediately. An ARQ worker picks up the job from Redis, downloads the PDF from S3, chunks it, embeds it in ChromaDB, and updates the document status in Postgres — fully decoupled from the HTTP request.

```
Client → POST /documents (202) → S3 upload + ARQ enqueue
                                       ↓
                                  ARQ Worker
                                  S3 download → PDF extract → ChromaDB index → DB status=ready

Client → POST /queries → ChromaDB retrieval → GPT-4o-mini → answer + sources
```

## Stack

| Layer | Technology |
|---|---|
| API | FastAPI 0.111, uvicorn |
| Auth | JWT HS256, bcrypt passwords |
| Database | PostgreSQL 16 + SQLAlchemy async (asyncpg) |
| Migrations | Alembic |
| Vector store | ChromaDB |
| LLM | OpenAI GPT-4o-mini (tenacity retry) |
| Object storage | AWS S3 |
| Task queue | ARQ (Redis-backed) |
| Rate limiting | slowapi with Redis backend |
| Logging | structlog JSON + X-Request-ID correlation |
| IaC | Terraform — VPC, ECS Fargate, RDS, ALB TLS 1.3, ECR, Secrets Manager |
| CI/CD | Jenkinsfile + GitHub Actions |

## OWASP Top 10 mitigations

| Risk | Mitigation |
|---|---|
| A01 Broken Access Control | Role-based access (`admin` / `analyst`); analysts see only their own documents |
| A02 Cryptographic Failures | AWS Secrets Manager for credentials; TLS 1.3 on ALB; bcrypt password hashing |
| A03 Injection | Pydantic v2 strict validation on all inputs; SQLAlchemy parameterised queries |
| A05 Security Misconfiguration | CORS restricted in production; `ALLOW_RESET` disabled in ChromaDB |
| A07 Auth Failures | JWT expiry + revocation-ready; rate limiting on auth endpoints |
| A09 Logging Failures | structlog JSON with request ID, user ID, and latency on every request |

## Quick start

### Prerequisites

- Docker and Docker Compose
- An OpenAI API key

### Run with Docker Compose

```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY

cd infra/docker
OPENAI_API_KEY=sk-... docker compose up --build
```

The API will be available at `http://localhost:8085`.
Interactive docs: `http://localhost:8085/docs`

### Development setup

```bash
# Requires uv (https://docs.astral.sh/uv/)
uv sync

# Run API
uv run uvicorn finrag_api.main:app --reload --port 8085

# Run worker (separate terminal)
uv run arq finrag_worker.main.WorkerSettings

# Run migrations
DATABASE_URL=postgresql+asyncpg://finrag:finrag@localhost:5432/finrag \
  uv run alembic upgrade head
```

## API endpoints

### Auth

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Register a new analyst account |
| `POST` | `/api/v1/auth/login` | Obtain a JWT access token |

### Documents

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/documents/` | Upload a PDF (max 50 MB) — returns `202` |
| `GET` | `/api/v1/documents/` | List documents (paginated) |
| `GET` | `/api/v1/documents/{id}` | Get document status and metadata |
| `DELETE` | `/api/v1/documents/{id}` | Delete a document |

### Queries

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/queries/` | Ask a question against indexed documents |

### Ops

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |

## Example usage

```bash
# Register
curl -X POST http://localhost:8085/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "analyst@bank.com", "full_name": "Ana Analyst", "password": "secret123"}'

# Login
TOKEN=$(curl -s -X POST http://localhost:8085/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=analyst@bank.com&password=secret123" | jq -r .access_token)

# Upload a PDF
curl -X POST http://localhost:8085/api/v1/documents/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@report.pdf" \
  -F "document_type=risk_report"

# Query
curl -X POST http://localhost:8085/api/v1/queries/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the main credit risk factors mentioned?"}'
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL asyncpg connection string |
| `SECRET_KEY` | Yes | JWT signing key (min 32 chars) |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `S3_BUCKET_NAME` | Yes | S3 bucket for PDF storage |
| `REDIS_URL` | Yes | Redis connection string |
| `CHROMA_HOST` | Yes | ChromaDB host |
| `CHROMA_PORT` | No | ChromaDB port (default: 8000) |
| `AWS_REGION` | No | AWS region (default: us-east-1) |
| `RATE_LIMIT_PER_MINUTE` | No | Requests per minute per IP (default: 60) |
| `ENVIRONMENT` | No | `development` or `production` |
| `DEBUG` | No | Enable debug logging and SQL echo |

## Project structure

```
finrag/
├── packages/
│   ├── core/src/finrag_core/
│   │   ├── core/           # Config, logging, security (JWT/bcrypt)
│   │   ├── domain/
│   │   │   ├── interfaces/ # Abstract ports (6 interfaces)
│   │   │   └── models/     # Pydantic domain models
│   │   └── services/       # DocumentService, RAGService, UserService, AuditService
│   ├── infrastructure/src/finrag_infra/
│   │   ├── db/             # SQLAlchemy ORM + Postgres repositories
│   │   ├── vector/         # ChromaDB adapter
│   │   ├── llm/            # OpenAI adapter with retry
│   │   ├── storage/        # S3 adapter
│   │   ├── cache/          # Redis client
│   │   └── aws/            # Secrets Manager client
│   ├── api/src/finrag_api/
│   │   ├── middleware/     # CorrelationId, CORS, rate limiting
│   │   └── v1/routes/      # auth, documents, queries
│   └── worker/src/finrag_worker/
│       └── tasks/          # ARQ document processing task
├── alembic/                # DB migrations
├── infra/
│   ├── docker/             # Dockerfiles + docker-compose.yml
│   └── terraform/          # AWS infrastructure
└── tests/
    ├── unit/               # Mocked service tests
    └── integration/        # testcontainers-python against real Postgres
```

## Tests

```bash
# Unit tests
uv run pytest tests/unit/

# Integration tests (requires Docker for testcontainers)
uv run pytest tests/integration/

# Full suite with coverage (≥85% required)
uv run pytest
```

## Infrastructure (Terraform)

```bash
cd infra/terraform
terraform init
terraform plan -var="db_password=<secret>" -var="openai_api_key=<key>"
terraform apply
```

Provisions: VPC with private subnets, ECS Fargate (api + worker), RDS PostgreSQL, ElastiCache Redis, S3, ALB with TLS 1.3, ECR repositories, and Secrets Manager entries.
