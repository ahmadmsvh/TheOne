"""
Health check API endpoints
"""
from fastapi import APIRouter

from app.core.database import get_db_manager

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    """Health check endpoint"""
    db_manager = get_db_manager()
    db_healthy = db_manager.health_check()
    
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "connected" if db_healthy else "disconnected"
    }
