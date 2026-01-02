import pytest
import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["JWT_ALGORITHM"] = "HS256"

from app.main import app
from app.core.database import get_db
from app.models import Base, User, Role
from app.core.security import hash_password


@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    Base.metadata.create_all(bind=engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture(scope="function")
def client(test_db: Session) -> Generator[TestClient, None, None]:

    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_data():
    return {
        "email": "test@example.com",
        "password": "TestPassword123!"
    }


@pytest.fixture
def sample_user(test_db: Session, sample_user_data: dict) -> User:
    user = User(
        email=sample_user_data["email"],
        password_hash=hash_password(sample_user_data["password"])
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def sample_role(test_db: Session) -> Role:
    role = Role(
        name="admin",
        description="Administrator role"
    )
    test_db.add(role)
    test_db.commit()
    test_db.refresh(role)
    return role


@pytest.fixture
def user_with_role(test_db: Session, sample_user: User, sample_role: Role) -> User:
    sample_user.roles.append(sample_role)
    test_db.commit()
    test_db.refresh(sample_user)
    return sample_user


@pytest.fixture
def access_token(sample_user: User) -> str:
    from app.core.security import create_access_token
    
    token_data = {
        "sub": str(sample_user.id),
        "email": sample_user.email,
        "roles": [role.name for role in sample_user.roles]
    }
    return create_access_token(token_data)


@pytest.fixture
def refresh_token(test_db: Session, sample_user: User) -> str:
    from app.core.security import create_refresh_token, REFRESH_TOKEN_EXPIRE_DAYS
    from datetime import datetime, timedelta, timezone
    from app.repositories.refresh_token_repository import RefreshTokenRepository
    
    token_data = {
        "sub": str(sample_user.id),
        "email": sample_user.email,
        "roles": [role.name for role in sample_user.roles]
    }
    token = create_refresh_token(token_data)
    
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token_repo = RefreshTokenRepository(test_db)
    refresh_token_repo.create(
        token=token,
        user_id=sample_user.id,
        expires_at=expires_at
    )
    
    return token
