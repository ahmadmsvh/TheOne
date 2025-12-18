# Auth Service

Authentication and authorization service for TheOne platform.

## Project Structure

```
auth-service/
├── app/
│   ├── api/                  # API endpoints
│   │   └── v1/              # API version 1
│   │       ├── auth.py      # Authentication endpoints
│   │       └── health.py    # Health check endpoints
│   ├── core/                # Core utilities
│   │   ├── database.py      # Database connection manager
│   │   └── security.py      # Password hashing utilities
│   ├── models/              # SQLAlchemy models
│   │   └── __init__.py      # User, Role, RefreshToken models
│   ├── repositories/        # Data access layer
│   │   └── user_repository.py
│   ├── schemas/             # Pydantic schemas
│   │   └── __init__.py      # Request/Response models
│   ├── services/            # Business logic layer
│   │   └── user_service.py
│   ├── dependencies.py      # FastAPI dependencies
│   └── main.py              # FastAPI application
├── alembic/                 # Database migrations
├── tests/                   # Test files
├── main.py                  # Application entry point
├── requirements.txt         # Python dependencies
└── Dockerfile               # Docker configuration
```

## Architecture

The service follows a layered architecture:

- **API Layer** (`app/api/`): FastAPI routers handling HTTP requests
- **Service Layer** (`app/services/`): Business logic and orchestration
- **Repository Layer** (`app/repositories/`): Data access operations
- **Model Layer** (`app/models/`): SQLAlchemy ORM models
- **Schema Layer** (`app/schemas/`): Pydantic validation models
- **Core Layer** (`app/core/`): Shared utilities (database, security)

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register a new user

### Health
- `GET /api/v1/health` - Health check endpoint

## Running the Service

### Development
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### Production
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### Docker
```bash
docker build -t auth-service .
docker run -p 8001:8001 auth-service
```

## Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Environment Variables

See `.env.example` for required environment variables.
