from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.redis_client import redis_client
from app.auth import create_access_token, create_refresh_token, verify_access_token
from app.models import (
    TokenResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RevokeTokenRequest,
    RevokeTokenResponse
)
import html

app = FastAPI(
    title="Auth Service",
    description="OAuth Token Service with Browser-based Authentication",
    version="1.0.0"
)

# CORS - v produkci omezit na konkrétní originy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # V produkci: ["https://your-domain.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Connect to Redis on startup"""
    await redis_client.connect()


@app.on_event("shutdown")
async def shutdown_event():
    """Disconnect from Redis on shutdown"""
    await redis_client.disconnect()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Auth Service",
        "version": "1.0.0",
        "endpoints": {
            "browser_login": "GET /auth/login",
            "token": "POST /auth/token",
            "refresh": "POST /auth/refresh",
            "revoke": "POST /auth/revoke"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


@app.get("/auth/login", response_class=HTMLResponse)
async def browser_login(
    request: Request,
    x_user_email: str = Header(None, alias="X-User-Email")
):
    """
    Browser-based login endpoint.
    Expects X-User-Email header from proxy (after Google OAuth verification).
    Returns HTML page that redirects to electron app via custom URL scheme.
    """
    # Validate proxy IP (optional, for production)
    client_ip = request.client.host
    # if client_ip not in settings.allowed_ips_list:
    #     raise HTTPException(status_code=403, detail="Forbidden - invalid proxy IP")

    if not x_user_email:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized - missing X-User-Email header"
        )

    # Generate tokens
    access_token = create_access_token(x_user_email)
    refresh_token = create_refresh_token()

    # Store refresh token in Redis
    await redis_client.store_refresh_token(
        token=refresh_token,
        user_email=x_user_email,
        device_info="electron_app_v1.0"
    )

    # Build callback URL for Electron app
    callback_url = (
        f"myapp://auth/callback"
        f"?access_token={access_token}"
        f"&refresh_token={refresh_token}"
        f"&expires_in={settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60}"
    )

    # Escape email for safe HTML display
    safe_email = html.escape(x_user_email)

    # Return HTML with auto-redirect
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="cs">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Autorizace úspěšná</title>
        <meta http-equiv="refresh" content="1;url={callback_url}">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                text-align: center;
                padding: 50px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                margin: 0;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .container {{
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            }}
            h1 {{
                color: #4CAF50;
                font-size: 3em;
                margin: 0 0 20px 0;
            }}
            p {{
                font-size: 1.2em;
                margin: 10px 0;
            }}
            .email {{
                color: #FFD700;
                font-weight: bold;
            }}
            .loader {{
                border: 5px solid #f3f3f3;
                border-top: 5px solid #4CAF50;
                border-radius: 50%;
                width: 50px;
                height: 50px;
                animation: spin 1s linear infinite;
                margin: 20px auto;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>✓</h1>
            <h2>Autorizace úspěšná</h2>
            <p>Uživatel: <span class="email">{safe_email}</span></p>
            <div class="loader"></div>
            <p>Přesměrování do aplikace...</p>
            <p><small>Toto okno můžete zavřít.</small></p>
        </div>
        <script>
            // Auto redirect
            setTimeout(function() {{
                window.location.href = '{callback_url}';
            }}, 1000);

            // Auto close after redirect
            setTimeout(function() {{
                window.close();
            }}, 2000);
        </script>
    </body>
    </html>
    """)


@app.post("/auth/token", response_model=TokenResponse)
async def get_token(
    x_user_email: str = Header(None, alias="X-User-Email")
):
    """
    Get access and refresh tokens (API endpoint version).
    For programmatic access, not browser-based.
    """
    if not x_user_email:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized - missing X-User-Email header"
        )

    # Generate tokens
    access_token = create_access_token(x_user_email)
    refresh_token = create_refresh_token()

    # Store refresh token in Redis
    await redis_client.store_refresh_token(
        token=refresh_token,
        user_email=x_user_email,
        device_info="api_client"
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@app.post("/auth/refresh", response_model=RefreshTokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token.
    """
    # Validate refresh token in Redis
    token_data = await redis_client.get_refresh_token(request.refresh_token)

    if not token_data:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token"
        )

    user_email = token_data["user_email"]

    # Generate new access token
    access_token = create_access_token(user_email)

    return RefreshTokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@app.post("/auth/revoke", response_model=RevokeTokenResponse)
async def revoke_token(request: RevokeTokenRequest):
    """
    Revoke refresh token (logout).
    """
    # Revoke token in Redis
    success = await redis_client.revoke_refresh_token(request.refresh_token)

    if not success:
        return RevokeTokenResponse(
            status="not_found",
            message="Refresh token not found or already revoked"
        )

    return RevokeTokenResponse(
        status="revoked",
        message="Refresh token successfully revoked"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
