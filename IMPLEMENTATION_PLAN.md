# Implementační Plán - Krok za Krokem

## Fáze 1: Setup Projektu (30 min)

### 1.1 Vytvoření struktury adresářů
```bash
mkdir -p auth-service/app
mkdir -p llm-service/app
mkdir -p electron-app/src
```

### 1.2 Inicializace Python projektů
```bash
cd auth-service
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn pyjwt redis python-dotenv pydantic-settings

cd ../llm-service
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn pyjwt python-dotenv openai
```

### 1.3 Spuštění Redis
```bash
docker run -d --name oauth-redis -p 6379:6379 redis:alpine
```

## Fáze 2: Auth Service (3-4 hodiny)

### 2.1 Core komponenty
Vytvořit v tomto pořadí:

1. **config.py** - Konfigurace (JWT secret, Redis URL, token TTL)
2. **redis_client.py** - Redis connection pool
3. **models.py** - Pydantic modely pro request/response
4. **auth.py** - JWT generování a validace + refresh token management
5. **main.py** - FastAPI endpoints

### 2.2 Testování
```bash
# Test token issuance
curl -X POST http://localhost:8000/auth/token \
  -H "X-User-Email: test@example.com"

# Test refresh
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "..."}'
```

## Fáze 3: LLM Service (2-3 hodiny)

### 3.1 Core komponenty
1. **config.py** - JWT secret (stejný jako Auth Service!)
2. **auth.py** - JWT validation middleware
3. **llm_client.py** - OpenAI/Anthropic wrapper
4. **main.py** - FastAPI endpoints s auth middleware

### 3.2 Testování
```bash
# Získat token z Auth Service
TOKEN=$(curl -X POST http://localhost:8000/auth/token \
  -H "X-User-Email: test@example.com" | jq -r '.access_token')

# Test LLM endpoint
curl -X POST http://localhost:8001/llm/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'
```

## Fáze 4: Electron App (2-3 hodiny)

### 4.1 Core komponenty
1. **auth-manager.js** - Token storage a refresh logika
2. **api-client.js** - HTTP client s auto-retry na token expiration
3. **renderer.js** - Chat UI
4. **main.js** - Electron main process

### 4.2 Token Flow
```
User opens app
  → Check refresh token in electron-store
  → If exists: Call /auth/refresh → Get access token
  → If not: Open browser to proxy-protected auth URL
  → After auth: Receive tokens → Store securely

User sends message
  → Call /llm/chat with access token
  → If 401 token_expired:
      → Call /auth/refresh
      → Retry /llm/chat
  → Display response
```

## Fáze 5: Production Ready (2-3 hodiny)

### 5.1 Docker Setup
Vytvořit:
- `auth-service/Dockerfile`
- `llm-service/Dockerfile`
- `docker-compose.yml`

### 5.2 Environment Variables
```env
# auth-service/.env
JWT_SECRET_KEY=<strong-random-secret-min-32-chars>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
REDIS_URL=redis://localhost:6379
ALLOWED_PROXY_IPS=192.168.1.1,10.0.0.1

# llm-service/.env
JWT_SECRET_KEY=<same-as-auth-service>
JWT_ALGORITHM=HS256
OPENAI_API_KEY=sk-...
# nebo
ANTHROPIC_API_KEY=sk-ant-...
```

### 5.3 Security Checklist
- [ ] HTTPS ve production
- [ ] Strong JWT secret (min 32 znaků, random)
- [ ] Validace proxy IP v Auth Service
- [ ] Rate limiting na oba services
- [ ] CORS nastavení
- [ ] Secrets v environment variables (ne v kódu!)
- [ ] Refresh token rotation
- [ ] Logging (bez tokenů!)

## Fáze 6: Testování a Optimalizace (2-3 hodiny)

### 6.1 Integration Testing
```python
# tests/test_flow.py
def test_full_auth_flow():
    # 1. Get tokens
    response = client.post("/auth/token", headers={"X-User-Email": "test@example.com"})
    access_token = response.json()["access_token"]
    refresh_token = response.json()["refresh_token"]

    # 2. Use access token
    response = llm_client.post("/llm/chat",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"message": "test"})
    assert response.status_code == 200

    # 3. Refresh token
    response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    new_access_token = response.json()["access_token"]
    assert new_access_token != access_token
```

### 6.2 Performance Testing
```bash
# Test token generation speed
ab -n 1000 -c 10 -H "X-User-Email: test@example.com" \
  http://localhost:8000/auth/token

# Test LLM endpoint with auth
ab -n 100 -c 5 -H "Authorization: Bearer <token>" \
  -p message.json http://localhost:8001/llm/chat
```

## Možné Problémy a Řešení

### Problem: Token expiruje během dlouhé konverzace
**Řešení**: V Electron app nastavit timer, který refreshuje token každých 20 minut (pokud je TTL 30min)

### Problem: User má více zařízení
**Řešení**: V Redis ukládat refresh token s device identifier:
```
Key: refresh_token:<uuid>
Value: {
  "user_email": "...",
  "device_id": "electron_desktop_1",
  "device_name": "MacBook Pro"
}
```

### Problem: Redis spadne
**Řešení**:
1. Graceful degradation - vrátit error, ale necrashovat
2. Redis Sentinel pro HA
3. Fallback na PostgreSQL pro refresh tokeny

### Problem: JWT secret leak
**Řešení**:
1. Okamžitá rotace secretu
2. Invalidace všech refresh tokenů v Redis (FLUSHDB)
3. Force re-authentication všech uživatelů

## Nástroje pro Development

### Debugování JWT
```bash
# Decode JWT (bez validace)
echo "eyJ..." | base64 -d

# Online: https://jwt.io
```

### Redis monitoring
```bash
docker exec -it oauth-redis redis-cli
> KEYS refresh_token:*
> TTL refresh_token:<uuid>
> GET refresh_token:<uuid>
```

### FastAPI Swagger
- Auth Service: http://localhost:8000/docs
- LLM Service: http://localhost:8001/docs

## Doporučené Next Steps

Po základní implementaci:

1. **Monitoring**: Prometheus + Grafana pro metrics
2. **Logging**: Structured logging (JSON) s user_email (ne tokeny!)
3. **User Management**: Admin panel pro revokaci tokenů
4. **Analytics**: Tracking usage per user
5. **Multi-tenancy**: Pokud bude více organizací
6. **Token scopes**: Pokud budete mít různá oprávnění (read/write)

## Resources

- FastAPI docs: https://fastapi.tiangolo.com
- PyJWT docs: https://pyjwt.readthedocs.io
- Redis Python: https://redis-py.readthedocs.io
- OAuth2/JWT best practices: https://oauth.net/2/
- OWASP security: https://owasp.org/www-project-top-ten/
