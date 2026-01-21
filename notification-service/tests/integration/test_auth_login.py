"""
Integration tests for /auth/login endpoint
"""
import pytest
from fastapi import status


class TestLoginEndpoint:
    """Tests for POST /api/v1/auth/login"""
    
    def test_login_success(self, client, sample_user):
        """Test successful login"""
        login_data = {
            "email": sample_user.email,
            "password": "TestPassword123!"  # From sample_user_data fixture
        }
        
        response = client.post(
            "/api/v1/auth/login",
            json=login_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert data["message"] == "Login successful"
        assert "user" in data
        assert data["user"]["email"] == sample_user.email
        assert "tokens" in data
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]
        assert data["tokens"]["token_type"] == "bearer"
        assert len(data["tokens"]["access_token"]) > 0
        assert len(data["tokens"]["refresh_token"]) > 0
    
    def test_login_wrong_password(self, client, sample_user):
        """Test login with wrong password"""
        login_data = {
            "email": sample_user.email,
            "password": "WrongPassword123!"
        }
        
        response = client.post(
            "/api/v1/auth/login",
            json=login_data
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data
        assert "Invalid email or password" in data["detail"]
    
    def test_login_nonexistent_email(self, client):
        """Test login with non-existent email"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "SomePassword123!"
        }
        
        response = client.post(
            "/api/v1/auth/login",
            json=login_data
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data
        assert "Invalid email or password" in data["detail"]
    
    def test_login_invalid_email_format(self, client):
        """Test login with invalid email format"""
        login_data = {
            "email": "not-an-email",
            "password": "TestPassword123!"
        }
        
        response = client.post(
            "/api/v1/auth/login",
            json=login_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_login_missing_email(self, client):
        """Test login with missing email field"""
        login_data = {
            "password": "TestPassword123!"
        }
        
        response = client.post(
            "/api/v1/auth/login",
            json=login_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_login_missing_password(self, client, sample_user):
        """Test login with missing password field"""
        login_data = {
            "email": sample_user.email
        }
        
        response = client.post(
            "/api/v1/auth/login",
            json=login_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_login_empty_password(self, client, sample_user):
        """Test login with empty password"""
        login_data = {
            "email": sample_user.email,
            "password": ""
        }
        
        response = client.post(
            "/api/v1/auth/login",
            json=login_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_login_creates_refresh_token_in_db(self, client, test_db, sample_user):
        """Test that login creates refresh token in database"""
        from app.repositories.refresh_token_repository import RefreshTokenRepository
        
        login_data = {
            "email": sample_user.email,
            "password": "TestPassword123!"
        }
        
        response = client.post(
            "/api/v1/auth/login",
            json=login_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        refresh_token = data["tokens"]["refresh_token"]
        
        # Verify token exists in database
        refresh_token_repo = RefreshTokenRepository(test_db)
        token_record = refresh_token_repo.get_by_token(refresh_token)
        assert token_record is not None
        assert token_record.user_id == sample_user.id
        assert token_record.revoked is False
    
    def test_login_tokens_are_valid(self, client, sample_user):
        """Test that login returns valid JWT tokens"""
        from app.core.security import decode_token
        
        login_data = {
            "email": sample_user.email,
            "password": "TestPassword123!"
        }
        
        response = client.post(
            "/api/v1/auth/login",
            json=login_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify access token
        access_token = data["tokens"]["access_token"]
        access_payload = decode_token(access_token)
        assert access_payload is not None
        assert access_payload["sub"] == str(sample_user.id)
        assert access_payload["email"] == sample_user.email
        assert access_payload["type"] == "access"
        
        # Verify refresh token
        refresh_token = data["tokens"]["refresh_token"]
        refresh_payload = decode_token(refresh_token)
        assert refresh_payload is not None
        assert refresh_payload["sub"] == str(sample_user.id)
        assert refresh_payload["email"] == sample_user.email
        assert refresh_payload["type"] == "refresh"
