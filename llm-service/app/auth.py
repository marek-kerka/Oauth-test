import jwt
from typing import Dict, Optional
from app.config import settings


def verify_jwt_token(token: str) -> Dict:
    """
    Verify JWT access token.
    Raises exceptions for expired or invalid tokens.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        # Check if it's an access token
        if payload.get("type") != "access":
            raise Exception("invalid_token")

        return payload

    except jwt.ExpiredSignatureError:
        raise Exception("token_expired")
    except jwt.InvalidTokenError:
        raise Exception("invalid_token")


def extract_user_email(payload: Dict) -> str:
    """Extract user email from JWT payload"""
    return payload.get("sub", "unknown@example.com")
