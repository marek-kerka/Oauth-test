from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.auth import verify_jwt_token, extract_user_email
from app.models import ChatRequest, ChatResponse
from app.llm_mock import MockLLM

app = FastAPI(
    title="LLM API Service",
    description="Mock LLM Service with JWT Authentication",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # V produkci: omezit
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock LLM instance
llm = MockLLM()


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """
    JWT authentication middleware.
    Validates token for /llm/* endpoints.
    """
    # Skip auth for non-protected endpoints
    if not request.url.path.startswith("/llm"):
        return await call_next(request)

    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Missing or invalid Authorization header"
            }
        )

    token = auth_header.replace("Bearer ", "")

    try:
        # Verify JWT token
        payload = verify_jwt_token(token)
        # Attach user info to request state
        request.state.user_email = extract_user_email(payload)
        request.state.jwt_payload = payload

    except Exception as e:
        error_type = str(e)

        if error_type == "token_expired":
            return JSONResponse(
                status_code=401,
                content={
                    "error": "token_expired",
                    "message": "Access token has expired. Please refresh."
                }
            )
        else:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "invalid_token",
                    "message": "Invalid access token"
                }
            )

    return await call_next(request)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "LLM API Service",
        "version": "1.0.0",
        "description": "Mock LLM with JWT authentication",
        "endpoints": {
            "chat": "POST /llm/chat",
            "health": "GET /health"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "llm-api"}


@app.post("/llm/chat", response_model=ChatResponse)
async def chat(request: Request, chat_request: ChatRequest):
    """
    Chat endpoint - requires valid JWT token.
    Returns mock LLM response.
    """
    # Get user email from request state (set by middleware)
    user_email = request.state.user_email

    # Generate conversation ID if not provided
    conversation_id = chat_request.conversation_id or llm.generate_conversation_id()

    # Generate mock LLM response
    response_text = llm.generate_response(
        message=chat_request.message,
        user_email=user_email
    )

    return ChatResponse(
        response=response_text,
        conversation_id=conversation_id,
        user_email=user_email
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
