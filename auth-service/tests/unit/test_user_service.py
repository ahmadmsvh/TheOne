"""
Unit tests for UserService
"""
import pytest
from fastapi import HTTPException, status
from uuid import UUID
from sqlalchemy.exc import IntegrityError

from app.services.user_service import UserService
from app.schemas import UserRegisterRequest
from app.models import User


class TestUserServiceRegistration:
    """Tests for user registration"""
    
    def test_register_user_success(self, test_db, sample_user_data):
        """Test successful user registration"""
        user_service = UserService(test_db)
        user_data = UserRegisterRequest(**sample_user_data)
        
        user = user_service.register_user(user_data)
        
        assert user is not None
        assert isinstance(user, User)
        assert user.email == sample_user_data["email"]
        assert user.password_hash != sample_user_data["password"]  # Should be hashed
        assert user.id is not None
    
    # def test_register_user_duplicate_email(self, test_db, sample_user_data):
    #     """Test that registering with duplicate email raises HTTPException"""
    #     user_service = UserService(test_db)
    #     user_data = UserRegisterRequest(**sample_user_data)
        
    #     # Register first user
    #     user_service.register_user(user_data)
        
    #     # Try to register again with same email
    #     with pytest.raises(HTTPException) as exc_info:
    #         user_service.register_user(user_data)
        
    #     assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    #     assert "Email already registered" in exc_info.value.detail
    
    def test_register_user_password_is_hashed(self, test_db, sample_user_data):
        """Test that password is properly hashed during registration"""
        user_service = UserService(test_db)
        user_data = UserRegisterRequest(**sample_user_data)
        original_password = sample_user_data["password"]
        
        user = user_service.register_user(user_data)
        
        # Password should be hashed, not stored in plain text
        assert user.password_hash != original_password
        assert len(user.password_hash) > len(original_password)
        # Should be able to verify the password
        from app.core.security import verify_password
        assert verify_password(original_password, user.password_hash) is True
    
    def test_register_user_creates_user_in_db(self, test_db, sample_user_data):
        """Test that registered user is persisted in database"""
        user_service = UserService(test_db)
        user_data = UserRegisterRequest(**sample_user_data)
        
        user = user_service.register_user(user_data)
        
        # Verify user exists in database
        found_user = user_service.get_user_by_id(user.id)
        assert found_user is not None
        assert found_user.email == sample_user_data["email"]


class TestUserServiceAuthentication:
    """Tests for user authentication"""
    
    def test_authenticate_user_success(self, test_db, sample_user):
        """Test successful user authentication"""
        user_service = UserService(test_db)
        
        authenticated_user = user_service.authenticate_user(
            sample_user.email,
            "TestPassword123!"  # From sample_user_data fixture
        )
        
        assert authenticated_user is not None
        assert authenticated_user.id == sample_user.id
        assert authenticated_user.email == sample_user.email
    
    def test_authenticate_user_wrong_password(self, test_db, sample_user):
        """Test authentication with wrong password"""
        user_service = UserService(test_db)
        
        authenticated_user = user_service.authenticate_user(
            sample_user.email,
            "WrongPassword123!"
        )
        
        assert authenticated_user is None
    
    def test_authenticate_user_nonexistent_email(self, test_db):
        """Test authentication with non-existent email"""
        user_service = UserService(test_db)
        
        authenticated_user = user_service.authenticate_user(
            "nonexistent@example.com",
            "SomePassword123!"
        )
        
        assert authenticated_user is None
    
    def test_authenticate_user_empty_password(self, test_db, sample_user):
        """Test authentication with empty password"""
        user_service = UserService(test_db)
        
        authenticated_user = user_service.authenticate_user(
            sample_user.email,
            ""
        )
        
        assert authenticated_user is None


class TestUserServiceGetUser:
    """Tests for getting users"""
    
    def test_get_user_by_id_success(self, test_db, sample_user):
        """Test getting user by ID"""
        user_service = UserService(test_db)
        
        found_user = user_service.get_user_by_id(sample_user.id)
        
        assert found_user is not None
        assert found_user.id == sample_user.id
        assert found_user.email == sample_user.email
    
    def test_get_user_by_id_not_found(self, test_db):
        """Test getting user by non-existent ID"""
        from uuid import uuid4
        user_service = UserService(test_db)
        
        non_existent_id = uuid4()
        found_user = user_service.get_user_by_id(non_existent_id)
        
        assert found_user is None
    
    def test_get_user_by_email_success(self, test_db, sample_user):
        """Test getting user by email"""
        user_service = UserService(test_db)
        
        found_user = user_service.get_user_by_email(sample_user.email)
        
        assert found_user is not None
        assert found_user.id == sample_user.id
        assert found_user.email == sample_user.email
    
    def test_get_user_by_email_not_found(self, test_db):
        """Test getting user by non-existent email"""
        user_service = UserService(test_db)
        
        found_user = user_service.get_user_by_email("nonexistent@example.com")
        
        assert found_user is None


class TestUserServiceUserToResponse:
    """Tests for user to response conversion"""
    
    def test_user_to_response(self, test_db, sample_user):
        """Test converting user to response schema"""
        user_service = UserService(test_db)
        
        response = user_service.user_to_response(sample_user)
        
        assert response.id == sample_user.id
        assert response.email == sample_user.email
        assert response.created_at == sample_user.created_at
        assert response.updated_at == sample_user.updated_at
