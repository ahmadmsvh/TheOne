"""
FastAPI dependencies
"""
from typing import Generator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.user_service import UserService


def get_user_service(db: Session = None) -> Generator[UserService, None, None]:
    """
    Dependency to get user service instance
    
    Usage:
        @app.post("/register")
        def register(user_service: UserService = Depends(get_user_service)):
            ...
    """
    if db is None:
        # Get db from dependency if not provided
        db_gen = get_db()
        db = next(db_gen)
        try:
            yield UserService(db)
        finally:
            next(db_gen, None)
    else:
        yield UserService(db)
