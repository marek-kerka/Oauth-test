from pydantic import BaseModel, EmailStr
from typing import Optional


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


class RevokeTokenRequest(BaseModel):
    refresh_token: str


class RevokeTokenResponse(BaseModel):
    status: str
    message: str
