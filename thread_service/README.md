# Thread Service

Standalone FastAPI + gRPC service responsible for persisting agent threads in PostgreSQL.

## Features

- HTTP + gRPC surface areas for creating, listing, and streaming conversation threads
- PostgreSQL persistence via SQLAlchemy + Alembic migrations
- Configurable via environment variables loaded with `pydantic-settings`

## Getting Started

```bash
cd thread_service
uv sync
cp env.example .env
uv run python run.py
```

This starts FastAPI on `THREAD_SERVICE_HTTP_*` and the gRPC server on `THREAD_SERVICE_GRPC_*`.

To regenerate protobuf stubs after editing `thread_service/proto/thread_service.proto`:

```bash
uv run python -m grpc_tools.protoc \\
  -I thread_service/proto \\
  --python_out=thread_service/proto \\
  --grpc_python_out=thread_service/proto \\
  thread_service/proto/thread_service.proto
```

## Environment Variables

Copy `env.example` to `.env` and adjust values:

- `THREAD_SERVICE_HTTP_HOST` / `THREAD_SERVICE_HTTP_PORT` — FastAPI bind address
- `THREAD_SERVICE_GRPC_HOST` / `THREAD_SERVICE_GRPC_PORT` — gRPC bind address
- `POSTGRES_*` — PostgreSQL connection details used to form the SQLAlchemy DSN

## Repository Layout

```
thread_service/
├── Dockerfile
├── alembic.ini
├── docker-compose.yml
├── env.example
├── migrations/
│   ├── env.py
│   └── versions/
├── pyproject.toml
├── run.py
├── tests/
└── thread_service/
    ├── api/
    ├── db.py
    ├── main.py
    ├── models.py
    ├── proto/
    ├── repositories.py
    ├── schemas.py
    └── settings.py
```

## Docker & Compose

Build and run the stack (service + Postgres):

```bash
cd thread_service
docker compose up --build
```

## Database Migrations

```bash
cd thread_service
uv run alembic upgrade head
```

## Testing

```bash
cd thread_service
uv run pytest
```
