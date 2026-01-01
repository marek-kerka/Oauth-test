# Architektura OAuth Token Systému

## Přehled

Systém se skládá ze 3 hlavních komponent:

1. **Auth Service** - Vydává tokeny (za Google OAuth proxy)
2. **LLM API Service** - Obsluhuje LLM requesty s validací tokenů
3. **Electron Client** - Desktop chat aplikace

## Doporučená Architektura

### 1. Auth Service (Port 8000)

**Technologie**: FastAPI + PyJWT + Redis

**Zodpovědnosti**:
- Příjem ověřeného emailu z hlavičky `X-User-Email` (od proxy)
- Generování JWT Access Tokenu (short-lived: 15-30 minut)
- Generování Refresh Tokenu (long-lived: 7-30 dní)
- Uložení refresh tokenů do Redis s TTL
- Revoke endpoint pro invalidaci tokenů

**Endpointy**:
```
POST /auth/token
  Headers: X-User-Email: user@example.com
  Response: {
    "access_token": "eyJ...",
    "refresh_token": "random_uuid",
    "token_type": "Bearer",
    "expires_in": 1800
  }

POST /auth/refresh
  Body: {"refresh_token": "..."}
  Response: {
    "access_token": "eyJ...",
    "expires_in": 1800
  }

POST /auth/revoke
  Headers: Authorization: Bearer <token>
  Body: {"refresh_token": "..."}
  Response: {"status": "revoked"}
```

**Důvody pro tento přístup**:
- **FastAPI**: Moderní, rychlý, automatická dokumentace (Swagger)
- **JWT pro Access Token**: Stateless validace, žádné DB dotazy při každém requestu
- **Redis pro Refresh Token**: Rychlé ověření, automatické expirování (TTL)
- **UUID pro Refresh Token**: Nepředvídatelný, lze snadno revokovat

### 2. LLM API Service (Port 8001)

**Technologie**: FastAPI + PyJWT + LLM Client (OpenAI/Anthropic)

**Zodpovědnosti**:
- Validace JWT Access Tokenu
- Extrakce user emailu z tokenu
- Volání LLM API
- Rate limiting per user
- Error handling pro expirované tokeny

**Endpointy**:
```
POST /llm/chat
  Headers: Authorization: Bearer <access_token>
  Body: {
    "message": "User question",
    "conversation_id": "optional_uuid"
  }
  Response: {
    "response": "LLM answer",
    "conversation_id": "uuid"
  }

GET /llm/health
  Response: {"status": "ok"}
```

**Bezpečnostní middleware**:
- JWT validace na každém requestu
- Kontrola expirace
- Odpověď 401 s `{"error": "token_expired"}` pro expirované tokeny

### 3. Electron Client

**Token Management Flow**:
```javascript
1. App start → Check if refresh_token exists in secure storage
2. If yes → Call /auth/refresh
3. If no → Redirect to Auth Service (proxy protected URL)
4. Store access_token in memory, refresh_token in encrypted local storage
5. On API call → Use access_token
6. On 401 token_expired → Auto refresh → Retry original request
7. On refresh fail → Redirect to auth
```

## Implementační Detaily

### JWT Structure (Access Token)

```json
{
  "sub": "user@example.com",
  "exp": 1735776000,
  "iat": 1735774200,
  "type": "access"
}
```

**Proč tento obsah**:
- `sub`: User identifier (email)
- `exp`: Expiration time (automatická validace)
- `iat`: Issued at (pro audit)
- `type`: Rozlišení access vs refresh JWT (pokud použijete JWT i pro refresh)

### Refresh Token Structure (Redis)

```
Key: refresh_token:<uuid>
Value: {
  "user_email": "user@example.com",
  "issued_at": "2026-01-01T12:00:00Z",
  "device_info": "electron_app_v1.0"
}
TTL: 30 days
```

### Bezpečnostní Doporučení

1. **HTTPS only** - Všechny služby musí běžet přes HTTPS
2. **Secure Headers**:
   - `X-User-Email` by měla být důvěryhodná (pouze od proxy)
   - Validace proxy IP adresy v Auth Service
3. **JWT Secret**: Silné, rotované, v environment variables
4. **Rate Limiting**: Na Auth Service i LLM API
5. **CORS**: Povolit pouze Electron app origin
6. **Refresh Token Rotation**: Při každém refresh vydat nový refresh token
7. **Token Storage v Electronu**:
   - Access token: V paměti (ne localStorage!)
   - Refresh token: electron-store s encryption

### Databázová Schema (Optional)

Pokud chcete audit log nebo user management:

```sql
-- PostgreSQL
CREATE TABLE users (
    email VARCHAR(255) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

CREATE TABLE token_audit (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255),
    action VARCHAR(50), -- 'issued', 'refreshed', 'revoked'
    token_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Struktura Projektu

```
oauth-token-system/
├── auth-service/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI app
│   │   ├── config.py         # Settings (JWT secret, Redis URL)
│   │   ├── models.py         # Pydantic models
│   │   ├── auth.py           # Token generation/validation
│   │   ├── redis_client.py   # Redis connection
│   │   └── middleware.py     # Proxy header validation
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── llm-service/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI app
│   │   ├── config.py
│   │   ├── auth.py           # JWT validation middleware
│   │   ├── llm_client.py     # OpenAI/Anthropic client
│   │   └── rate_limiter.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── electron-app/
│   ├── src/
│   │   ├── main.js           # Electron main process
│   │   ├── renderer.js       # UI logic
│   │   ├── auth-manager.js   # Token management
│   │   └── api-client.js     # API calls with auto-refresh
│   ├── package.json
│   └── .env.example
│
├── docker-compose.yml        # Redis + both services
└── README.md
```

## Deployment Flow

### Development:
```bash
# Redis
docker run -d -p 6379:6379 redis:alpine

# Auth Service
cd auth-service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# LLM Service
cd llm-service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

### Production:
```bash
docker-compose up -d
```

## Error Handling Strategie

### V LLM Service:
```python
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/llm"):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        try:
            payload = verify_jwt(token)
            request.state.user_email = payload["sub"]
        except jwt.ExpiredSignatureError:
            return JSONResponse(
                status_code=401,
                content={"error": "token_expired", "message": "Access token has expired"}
            )
        except jwt.InvalidTokenError:
            return JSONResponse(
                status_code=401,
                content={"error": "invalid_token", "message": "Invalid token"}
            )
    return await call_next(request)
```

### V Electron Client:
```javascript
async function callAPI(endpoint, data) {
  try {
    const response = await fetch(endpoint, {
      headers: { 'Authorization': `Bearer ${accessToken}` },
      body: JSON.stringify(data)
    });

    if (response.status === 401) {
      const error = await response.json();
      if (error.error === 'token_expired') {
        // Auto refresh
        await refreshAccessToken();
        // Retry original request
        return callAPI(endpoint, data);
      }
    }

    return response.json();
  } catch (error) {
    console.error('API call failed:', error);
    throw error;
  }
}
```

## Výhody Tohoto Přístupu

1. **Bezpečnost**: JWT jsou standardní, těžko padělatelné
2. **Škálovatelnost**: Stateless access tokeny, LLM service nemusí kontaktovat Auth service
3. **Performance**: Redis je extrémně rychlý pro refresh token lookup
4. **User Experience**: Automatický refresh, uživatel nemusí znovu přihlašovat
5. **Audit**: Všechny token operace lze logovat
6. **Revokace**: Refresh tokeny lze okamžitě zneplatnit v Redis

## Alternativní Přístupy

### A) Obě tokeny jako JWT (bez Redis)
**Výhody**: Jednodušší, žádná databáze
**Nevýhody**: Nelze revokovat tokeny, delší refresh token JWT = bezpečnostní riziko

### B) Session-based (cookies)
**Výhody**: Jednodušší pro web
**Nevýhody**: Nehodí se pro Electron app, CSRF problémy

### C) OAuth2 s AuthorizationServer (Keycloak, Auth0)
**Výhody**: Enterprise ready, vše hotové
**Nevýhody**: Overkill pro tento use case, náročnější setup

## Časový Odhad Implementace

- Auth Service: 4-6 hodin
- LLM Service: 3-4 hodiny
- Electron token management: 2-3 hodiny
- Testování + bugfixing: 3-4 hodiny
**Celkem**: 12-17 hodin čistého development času

## Doporučené Knihovny

### Python:
```
fastapi==0.108.0
uvicorn[standard]==0.25.0
pyjwt==2.8.0
redis==5.0.1
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0
openai==1.6.0  # nebo anthropic
```

### Electron:
```
electron-store (pro bezpečné uložení refresh tokenu)
axios (pro HTTP requesty)
```
