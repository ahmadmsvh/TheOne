"""
Authentication utilities for validating JWT tokens from auth-service
"""
import os
import jwt
from functools import wraps
from typing import Optional, Dict, Any, List
from flask import request, jsonify
import sys
from pathlib import Path

# Add shared to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from shared.logging_config import get_logger

logger = get_logger(__name__, "product-service")

# JWT Configuration (should match auth-service)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error decoding token: {e}")
        return None


def get_current_user() -> Optional[Dict[str, Any]]:
    """Extract and validate user from Authorization header"""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    
    try:
        # Extract Bearer token
        scheme, token = auth_header.split(" ", 1)
        if scheme.lower() != "bearer":
            return None
    except ValueError:
        return None
    
    # Decode token
    payload = decode_token(token)
    if not payload:
        return None
    
    # Verify it's an access token
    if payload.get("type") != "access":
        logger.warning("Token provided is not an access token")
        return None
    
    return payload


def require_auth(f):
    """Decorator to require authentication (works with async functions)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_data = get_current_user()
        if not user_data:
            return jsonify({"error": "Invalid or expired token"}), 401
        
        # Add user data to kwargs for use in route
        kwargs["current_user"] = user_data
        # Return the function call (may be coroutine if async)
        # The async_route decorator will handle execution
        return f(*args, **kwargs)
    
    return decorated_function


def require_role(role_name: str):
    """Decorator factory to require specific role"""
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if not current_user:
                return jsonify({"error": "Authentication required"}), 401
            
            user_roles: List[str] = current_user.get("roles", [])
            if role_name not in user_roles:
                logger.warning(
                    f"User {current_user.get('sub')} attempted to access {role_name}-only resource. "
                    f"User roles: {user_roles}"
                )
                return jsonify({
                    "error": f"Access denied. Required role: {role_name}"
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def require_any_role(*role_names: str):
    """Decorator factory to require any of the specified roles"""
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if not current_user:
                return jsonify({"error": "Authentication required"}), 401
            
            user_roles: List[str] = current_user.get("roles", [])
            if not any(role_name in user_roles for role_name in role_names):
                logger.warning(
                    f"User {current_user.get('sub')} attempted to access resource requiring one of "
                    f"{role_names}. User roles: {user_roles}"
                )
                return jsonify({
                    "error": f"Access denied. Required one of the following roles: {', '.join(role_names)}"
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

