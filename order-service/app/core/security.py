import jwt
from typing import Optional, Dict, Any
from shared.logging_config import get_logger
from shared.config import get_settings

settings = get_settings()
logger = get_logger(__name__, "order-service")

JWT_SECRET_KEY = settings.app.jwt_secret_key
JWT_ALGORITHM = settings.app.jwt_algorithm


def decode_token(token: str) -> Optional[Dict[str, Any]]:
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

