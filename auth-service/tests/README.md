# Auth Service Tests

This directory contains comprehensive unit and integration tests for the auth service.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and test configuration
├── unit/                    # Unit tests
│   ├── __init__.py
│   ├── test_security.py     # Password hashing and JWT token tests
│   ├── test_user_service.py # UserService business logic tests
│   └── test_dependencies.py # Authentication dependency tests
└── integration/             # Integration tests
    ├── __init__.py
    ├── test_auth_register.py # Registration endpoint tests
    ├── test_auth_login.py    # Login endpoint tests
    ├── test_auth_refresh.py  # Token refresh endpoint tests
    └── test_auth_logout.py  # Logout endpoint tests
```

## Running Tests

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run specific test file
pytest tests/unit/test_security.py

# Run specific test
pytest tests/unit/test_security.py::TestPasswordHashing::test_hash_password_returns_string
```

### Run with Coverage

```bash
pytest --cov=app --cov-report=html
```

This will generate an HTML coverage report in `htmlcov/index.html`.

### Run with Verbose Output

```bash
pytest -v
```

### Run with Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration
```

## Test Coverage

The test suite covers:

### Unit Tests

1. **Security Functions** (`test_security.py`)
   - Password hashing and verification
   - JWT token creation (access and refresh)
   - JWT token decoding and validation
   - Token expiration handling

2. **UserService** (`test_user_service.py`)
   - User registration
   - User authentication
   - User retrieval by ID and email
   - User to response conversion

3. **Dependencies** (`test_dependencies.py`)
   - `require_auth` dependency
   - `require_role` dependency
   - `require_any_role` dependency

### Integration Tests

1. **Registration Endpoint** (`test_auth_register.py`)
   - Successful registration
   - Duplicate email handling
   - Password validation
   - Input validation

2. **Login Endpoint** (`test_auth_login.py`)
   - Successful login
   - Invalid credentials handling
   - Token generation and storage
   - Token validation

3. **Refresh Endpoint** (`test_auth_refresh.py`)
   - Successful token refresh
   - Invalid token handling
   - Expired token handling
   - Revoked token handling

4. **Logout Endpoint** (`test_auth_logout.py`)
   - Successful logout
   - Token revocation
   - Invalid token handling (should still succeed)

## Test Fixtures

The `conftest.py` file provides several useful fixtures:

- `test_db`: In-memory SQLite database session for each test
- `client`: FastAPI test client with database override
- `sample_user_data`: Sample user registration data
- `sample_user`: Pre-created user in test database
- `sample_role`: Pre-created role in test database
- `user_with_role`: User with assigned role
- `access_token`: Valid access token for testing
- `refresh_token`: Valid refresh token stored in database

## Writing New Tests

When writing new tests:

1. Place unit tests in `tests/unit/`
2. Place integration tests in `tests/integration/`
3. Use descriptive test class and method names
4. Use fixtures from `conftest.py` when possible
5. Follow the existing test structure and naming conventions

## Notes

- Tests use an in-memory SQLite database for isolation
- Each test gets a fresh database session
- JWT secret key is set to a test value in `conftest.py`
- Tests are designed to be independent and can run in any order
