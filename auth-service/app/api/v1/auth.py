"""
Authentication API endpoints
"""
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas import UserRegisterRequest, UserRegisterResponse, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/register",
    response_model=UserRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "User successfully registered"},
        400: {"description": "Bad request - validation error or email already exists"},
        500: {"description": "Internal server error"}
    }
)
def register_user(
    user_data: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user
    
    - **email**: User's email address (must be unique)
    - **password**: User's password (min 8 characters, must contain uppercase, lowercase, and digit)
    
    Returns the created user information.
    """
    user_service = UserService(db)
    new_user = user_service.register_user(user_data)
    
    return UserRegisterResponse(
        message="User registered successfully",
        user=user_service.user_to_response(new_user)
    )
