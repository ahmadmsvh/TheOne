import pytest
from fastapi import status


class TestRegisterEndpoint:
    
    def test_register_success(self, client, sample_user_data):
        response = client.post(
            "/api/v1/auth/register",
            json=sample_user_data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "message" in data
        assert "user" in data
        assert data["user"]["email"] == sample_user_data["email"]
        assert "id" in data["user"]
        assert "created_at" in data["user"]
        assert "updated_at" in data["user"]
        assert "password" not in data["user"]
        assert "password_hash" not in data["user"]
    
    # def test_register_duplicate_email(self, client, sample_user_data):
    #     """Test registration with duplicate email"""
    #     # Register first user
    #     response1 = client.post(
    #         "/api/v1/auth/register",
    #         json=sample_user_data
    #     )
    #     assert response1.status_code == status.HTTP_201_CREATED
        
    #     # Try to register again with same email
    #     response2 = client.post(
    #         "/api/v1/auth/register",
    #         json=sample_user_data
    #     )
        
    #     assert response2.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_register_invalid_email(self, client):
        invalid_data = {
            "email": "not-an-email",
            "password": "TestPassword123!"
        }
        
        response = client.post(
            "/api/v1/auth/register",
            json=invalid_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_register_weak_password(self, client):
        weak_password_data = {
            "email": "test@example.com",
            "password": "weak"  # Too short, no uppercase, no digit
        }
        
        response = client.post(
            "/api/v1/auth/register",
            json=weak_password_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    # def test_register_password_no_uppercase(self, client):
    #     """Test registration with password missing uppercase"""
    #     invalid_data = {
    #         "email": "test@example.com",
    #         "password": "testpassword123!"  # No uppercase
    #     }
        
    #     response = client.post(
    #         "/api/v1/auth/register",
    #         json=invalid_data
    #     )
        
    #     assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    # def test_register_password_no_lowercase(self, client):
    #     """Test registration with password missing lowercase"""
    #     invalid_data = {
    #         "email": "test@example.com",
    #         "password": "TESTPASSWORD123!"  # No lowercase
    #     }
        
    #     response = client.post(
    #         "/api/v1/auth/register",
    #         json=invalid_data
    #     )
        
    #     assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    # def test_register_password_no_digit(self, client):
    #     """Test registration with password missing digit"""
    #     invalid_data = {
    #         "email": "test@example.com",
    #         "password": "TestPassword!"  # No digit
    #     }
        
    #     response = client.post(
    #         "/api/v1/auth/register",
    #         json=invalid_data
    #     )
        
    #     assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_register_password_too_short(self, client):
        invalid_data = {
            "email": "test@example.com",
            "password": "Test1!"  # Less than 8 characters
        }
        
        response = client.post(
            "/api/v1/auth/register",
            json=invalid_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_register_missing_email(self, client):
        invalid_data = {
            "password": "TestPassword123!"
        }
        
        response = client.post(
            "/api/v1/auth/register",
            json=invalid_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_register_missing_password(self, client):
        invalid_data = {
            "email": "test@example.com"
        }
        
        response = client.post(
            "/api/v1/auth/register",
            json=invalid_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_register_empty_body(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_register_validates_password_strength(self, client):
        valid_passwords = [
            "TestPassword123!",
            "MySecurePass1@",
            "AnotherValid1#",
        ]
        
        for password in valid_passwords:
            data = {
                "email": f"test{password[:5]}@example.com",
                "password": password
            }
            response = client.post(
                "/api/v1/auth/register",
                json=data
            )
            assert response.status_code == status.HTTP_201_CREATED, f"Password {password} should be valid"
