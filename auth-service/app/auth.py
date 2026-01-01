import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional
import uuid
from app.config import settings


def create_access_token(user_email: str) -> str:
    """Create JWT access token"""
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": user_email,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return token


def create_refresh_token() -> str:
    """Create refresh token (UUID)"""
    return str(uuid.uuid4())


def verify_access_token(token: str) -> Optional[Dict]:
    """Verify and decode JWT access token"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        # Check if it's an access token
        if payload.get("type") != "access":
            return None

        return payload

    except jwt.ExpiredSignatureError:
        raise Exception("token_expired")
    except jwt.InvalidTokenError:
        raise Exception("invalid_token")
