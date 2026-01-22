
import pytest
import jwt
from datetime import datetime, timedelta
from freezegun import freeze_time
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    JWT_SECRET_KEY,
    JWT_ALGORITHM
)


class TestPasswordHashing:
        
    def test_hash_password_returns_string(self):
        password = "TestPassword123!"
        hashed = hash_password(password)
        assert isinstance(hashed, str)
        assert len(hashed) > 0
    
    def test_hash_password_produces_different_hashes(self):
        password = "TestPassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2
    
    def test_verify_password_correct_password(self):
        password = "TestPassword123!"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect_password(self):
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = hash_password(password)
        assert verify_password(wrong_password, hashed) is False
    
    def test_verify_password_empty_password(self):
        password = "TestPassword123!"
        hashed = hash_password(password)
        assert verify_password("", hashed) is False
    
    def test_hash_password_handles_special_characters(self):
        password = "Test@Password#123$%^&*()"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True


class TestJWTTokens:
    
    def test_create_access_token_returns_string(self):
        token_data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(token_data)
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_refresh_token_returns_string(self):
        token_data = {"sub": "user123", "email": "test@example.com"}
        token = create_refresh_token(token_data)
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_decode_token_valid_access_token(self):
        token_data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(token_data)
        payload = decode_token(token)
        
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"
        assert "exp" in payload
    
    def test_decode_token_valid_refresh_token(self):
        token_data = {"sub": "user123", "email": "test@example.com"}
        token = create_refresh_token(token_data)
        payload = decode_token(token)
        
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "refresh"
        assert "exp" in payload
    
    def test_decode_token_invalid_token(self):
        invalid_token = "invalid.token.here"
        payload = decode_token(invalid_token)
        assert payload is None
    
    def test_decode_token_expired_token(self):
        with freeze_time("2024-01-01"):
            token_data = {"sub": "user123", "email": "test@example.com"}
            token = create_access_token(token_data)
        
        with freeze_time("2024-01-02"):
            payload = decode_token(token)
            assert payload is None
    
    def test_access_token_expiration_time(self):
        with freeze_time("2024-01-01 12:00:00") as frozen_time:
            token_data = {"sub": "user123", "email": "test@example.com"}
            token = create_access_token(token_data)
            
            payload = decode_token(token)
            assert payload is not None
            
            frozen_time.tick(timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES - 1))
            payload = decode_token(token)
            assert payload is not None
            
            frozen_time.tick(timedelta(minutes=2))
            payload = decode_token(token)
            assert payload is None
    
    def test_refresh_token_expiration_time(self):
        with freeze_time("2024-01-01 12:00:00") as frozen_time:
            token_data = {"sub": "user123", "email": "test@example.com"}
            token = create_refresh_token(token_data)
            
            payload = decode_token(token)
            assert payload is not None
            
            frozen_time.tick(timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS - 1))
            payload = decode_token(token)
            assert payload is not None
            
            frozen_time.tick(timedelta(days=2))
            payload = decode_token(token)
            assert payload is None
    
    def test_token_preserves_custom_claims(self):
        token_data = {
            "sub": "user123",
            "email": "test@example.com",
            "custom_claim": "custom_value"
        }
        token = create_access_token(token_data)
        payload = decode_token(token)
        
        assert payload["custom_claim"] == "custom_value"
    
    def test_access_token_has_correct_type(self):
        token_data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(token_data)
        payload = decode_token(token)
        assert payload["type"] == "access"
    
    def test_refresh_token_has_correct_type(self):
        token_data = {"sub": "user123", "email": "test@example.com"}
        token = create_refresh_token(token_data)
        payload = decode_token(token)
        assert payload["type"] == "refresh"
    
    def test_token_with_wrong_secret_fails(self):
        token_data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(token_data)

        try:
            payload = jwt.decode(token, "wrong-secret", algorithms=[JWT_ALGORITHM])
            pytest.fail("Should have raised InvalidTokenError")
        except jwt.InvalidTokenError:
            pass
