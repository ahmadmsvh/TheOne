"""
User repository for database operations
"""
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import User
import sys
from pathlib import Path

# Add shared to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))
from shared.logging_config import get_logger

logger = get_logger(__name__, "auth-service")


class UserRepository:
    """Repository for user database operations"""
    
    def __init__(self, db: Session):
        """
        Initialize user repository
        
        Args:
            db: Database session
        """
        self.db = db
    
    def get_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Get user by ID
        
        Args:
            user_id: User UUID
            
        Returns:
            User object or None if not found
        """
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email
        
        Args:
            email: User email address
            
        Returns:
            User object or None if not found
        """
        return self.db.query(User).filter(User.email == email).first()
    
    def email_exists(self, email: str) -> bool:
        """
        Check if email already exists
        
        Args:
            email: Email address to check
            
        Returns:
            True if email exists, False otherwise
        """
        return self.db.query(User).filter(User.email == email).first() is not None
    
    def create(self, email: str, password_hash: str) -> User:
        """
        Create a new user
        
        Args:
            email: User email address
            password_hash: Hashed password
            
        Returns:
            Created User object
            
        Raises:
            IntegrityError: If email already exists
        """
        try:
            new_user = User(
                email=email,
                password_hash=password_hash
            )
            self.db.add(new_user)
            self.db.commit()
            self.db.refresh(new_user)
            logger.info(f"User created: {new_user.email} (ID: {new_user.id})")
            return new_user
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to create user: {e}")
            raise
    
    def update(self, user: User) -> User:
        """
        Update user
        
        Args:
            user: User object to update
            
        Returns:
            Updated User object
        """
        self.db.commit()
        self.db.refresh(user)
        logger.info(f"User updated: {user.email} (ID: {user.id})")
        return user
    
    def delete(self, user_id: UUID) -> bool:
        """
        Delete user by ID
        
        Args:
            user_id: User UUID
            
        Returns:
            True if deleted, False if not found
        """
        user = self.get_by_id(user_id)
        if user:
            self.db.delete(user)
            self.db.commit()
            logger.info(f"User deleted: {user_id}")
            return True
        return False
