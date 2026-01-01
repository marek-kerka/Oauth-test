# OAuth Token System - Python Implementation

![Integration Tests](https://github.com/marek-kerka/Oauth-test/workflows/Integration%20Tests/badge.svg?branch=claude/python-auth-token-plan-G1zRD)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Kompletní implementace OAuth token systému s browser-based autentizací pro Electron aplikaci.

## 📋 Přehled

Tento systém se skládá ze 3 komponent:

1. **Auth Service** (FastAPI) - Vydává JWT access tokeny a refresh tokeny
2. **LLM Service** (FastAPI) - Mock LLM API s JWT autentizací
3. **Electron App** - Desktop chat aplikace s custom URL scheme

### Architektura

```
┌─────────────────┐
│  Electron App   │
│  (Desktop Chat) │
└────────┬────────┘
         │
         │ 1. Open browser → Auth Service (za proxy)
         │
┌────────▼────────┐      ┌──────────┐
│  System Browser │◄────►│  Proxy   │
│ (Google OAuth)  │      │ (Google) │
└────────┬────────┘      └──────────┘
         │
         │ 2. myapp://auth/callback?tokens=...
         │
┌────────▼────────┐
│  Electron App   │
│ (save tokens)   │
└────────┬────────┘
         │
         │ 3. Call LLM API with access_token
         │
┌────────▼────────┐      ┌──────────┐
│   LLM Service   │◄────►│  Redis   │
│  (JWT validate) │      │ (tokens) │
└─────────────────┘      └──────────┘
```

## 🚀 Rychlý Start

### Požadavky

- Python 3.9+
- Node.js 18+
- Docker (pro Redis)

### 1. Spustit Redis

```bash
docker-compose up -d
```

### 2. Spustit Auth Service

```bash
cd auth-service
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Kopírovat .env
cp .env.example .env

# Spustit
uvicorn app.main:app --reload --port 8000
```

Auth Service běží na: http://localhost:8000

### 3. Spustit LLM Service

```bash
cd llm-service
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Kopírovat .env (použít STEJNÝ JWT_SECRET_KEY jako Auth Service!)
cp .env.example .env

# Spustit
uvicorn app.main:app --reload --port 8001
```

LLM Service běží na: http://localhost:8001

### 4. Spustit Electron App

```bash
cd electron-app
npm install

# Spustit v dev módu
npm run dev
```

## 🔧 Testování bez Google Proxy

Protože v dev prostředí nemáte Google OAuth proxy, použijte curl pro simulaci:

### Získání tokenů (simulace proxy):

```bash
# Spustit curl, který přidá X-User-Email hlavičku (simuluje proxy)
curl -H "X-User-Email: test@example.com" http://localhost:8000/auth/login
```

Tento příkaz vrátí HTML stránku. Otevřete ji v prohlížeči nebo klikněte na myapp:// URL:

```
myapp://auth/callback?access_token=...&refresh_token=...
```

Zkopírujte tuto URL a:
- Na macOS: Otevřete ji přímo (macOS zachytí myapp://)
- Na Windows/Linux: Electron musí běžet, pak URL zachytí second-instance handler

### Nebo použijte Swagger UI:

1. Otevřete http://localhost:8000/docs
2. Použijte `/auth/token` endpoint s hlavičkou `X-User-Email`

## 📡 API Dokumentace

### Auth Service (Port 8000)

#### GET /auth/login
Browser-based login (pro Electron)
- **Headers**: `X-User-Email: user@example.com` (od proxy)
- **Response**: HTML s redirect na `myapp://auth/callback`

#### POST /auth/token
Získání tokenů (API verze)
- **Headers**: `X-User-Email: user@example.com`
- **Response**:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "uuid",
  "token_type": "Bearer",
  "expires_in": 1800
}
```

#### POST /auth/refresh
Refresh access token
- **Body**: `{"refresh_token": "uuid"}`
- **Response**:
```json
{
  "access_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 1800
}
```

#### POST /auth/revoke
Revoke refresh token (logout)
- **Body**: `{"refresh_token": "uuid"}`
- **Response**:
```json
{
  "status": "revoked",
  "message": "Refresh token successfully revoked"
}
```

### LLM Service (Port 8001)

#### POST /llm/chat
Chat endpoint (vyžaduje JWT)
- **Headers**: `Authorization: Bearer <access_token>`
- **Body**:
```json
{
  "message": "Your question",
  "conversation_id": "optional-uuid"
}
```
- **Response**:
```json
{
  "response": "Mock LLM response",
  "conversation_id": "uuid",
  "user_email": "user@example.com",
  "model": "mock-llm-v1"
}
```

## 🔐 Bezpečnost

### JWT Secret Key

**KRITICKÉ**: Auth Service a LLM Service MUSÍ používat **STEJNÝ** `JWT_SECRET_KEY`!

```bash
# auth-service/.env
JWT_SECRET_KEY=your-super-secret-key-min-32-chars

# llm-service/.env
JWT_SECRET_KEY=your-super-secret-key-min-32-chars  # STEJNÝ!
```

### Production Setup

1. **Generovat silný secret**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

2. **HTTPS pouze**: Všechny služby přes HTTPS

3. **Proxy IP validace**: Odkomentovat v `auth-service/app/main.py`:
```python
if client_ip not in settings.allowed_ips_list:
    raise HTTPException(status_code=403, detail="Forbidden - invalid proxy IP")
```

4. **CORS**: Omezit na konkrétní domény

5. **Rate Limiting**: Přidat rate limiting middleware

## 🧪 Testování

### Test Auth Flow

```bash
# 1. Získat tokeny
curl -X POST http://localhost:8000/auth/token \
  -H "X-User-Email: test@example.com" \
  | jq

# 2. Uložit access token
ACCESS_TOKEN="eyJ..."

# 3. Zavolat LLM API
curl -X POST http://localhost:8001/llm/chat \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}' \
  | jq

# 4. Test expirovaného tokenu (počkat 30 min nebo změnit TTL)

# 5. Refresh token
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "uuid-from-step1"}' \
  | jq
```

### Test Electron Flow

1. Spustit všechny služby
2. Spustit Electron app: `npm run dev`
3. Kliknout "Přihlásit přes Google"
4. V terminálu použít curl s X-User-Email
5. Kliknout na myapp:// URL v HTML odpovědi
6. Electron app by měla přijmout tokeny
7. Napsat zprávu v chatu
8. Měli byste vidět mock LLM odpověď

## 🗂️ Struktura Projektu

```
oauth-token-system/
├── auth-service/          # Auth API
│   ├── app/
│   │   ├── main.py       # FastAPI endpoints
│   │   ├── auth.py       # JWT utils
│   │   ├── redis_client.py
│   │   ├── config.py
│   │   └── models.py
│   ├── requirements.txt
│   └── .env.example
│
├── llm-service/           # LLM API
│   ├── app/
│   │   ├── main.py       # FastAPI endpoints
│   │   ├── auth.py       # JWT validation
│   │   ├── llm_mock.py   # Mock LLM
│   │   ├── config.py
│   │   └── models.py
│   ├── requirements.txt
│   └── .env.example
│
├── electron-app/          # Desktop app
│   ├── src/
│   │   ├── main.js       # Electron main
│   │   ├── preload.js    # IPC bridge
│   │   ├── renderer.js   # UI logic
│   │   ├── index.html    # UI
│   │   └── styles.css
│   ├── package.json
│   └── .env.example
│
├── docker-compose.yml     # Redis
├── ARCHITECTURE.md        # Detailní architektura
├── IMPLEMENTATION_PLAN.md # Implementační kroky
└── README.md             # Tento soubor
```

## 🧪 Testing & CI/CD

### Automatické testy

Projekt má kompletní integrační testy s GitHub Actions CI/CD:

**Lokální spuštění testů**:
```bash
# Python integration tests (30 testů)
python tests/integration_test.py

# Bash E2E tests (9 testů)
bash tests/e2e_test.sh
```

**GitHub Actions**:
- ✅ Spouští se automaticky při každém push
- ✅ Redis service container
- ✅ Všechny služby testovány (Auth + LLM)
- ✅ 100% coverage všech endpointů
- ✅ Test artifacts uploadované

**Test Coverage**:
- Auth Service: 100% endpoints (15 testů)
- LLM Service: 100% endpoints (10 testů)
- Redis Integration: 100% (5 testů)
- Error Handling: 100% (5 testů)
- Browser Flow: 100% (4 testů)

**Celkem**: 39 automatických testů ✅

Více informací: [tests/README.md](tests/README.md)

## 🐛 Troubleshooting

### Electron neotevírá browser
- Zkontrolujte, že `shell.openExternal()` funguje
- Zkuste manuálně otevřít http://localhost:8000/auth/login

### myapp:// URL nefunguje
- **macOS**: Otevřete URL přímo z prohlížeče
- **Windows/Linux**: Electron musí běžet před kliknutím na URL
- Zkontrolujte console log v Electron DevTools

### Token expired chyba
- Access token je platný pouze 30 minut
- Electron by měl automaticky refreshovat
- Zkontrolujte, že refresh token je uložený v electron-store

### LLM Service vrací 401
- Zkontrolujte, že JWT_SECRET_KEY je **STEJNÝ** v obou službách
- Zkontrolujte Authorization header format: `Bearer <token>`
- Zkontrolujte, že token není expirovaný

### Redis connection error
- Zkontrolujte, že Redis běží: `docker ps`
- Test connection: `docker exec -it oauth-redis redis-cli ping`
- Měl byste vidět `PONG`

## 📚 Další Kroky

### Pro Production:

1. **Real LLM Integration**: Nahradit mock v `llm-service/app/llm_mock.py`
   ```python
   from openai import OpenAI
   # nebo
   from anthropic import Anthropic
   ```

2. **Database**: Přidat PostgreSQL pro user management a audit log

3. **Monitoring**: Prometheus + Grafana

4. **Rate Limiting**: Per-user rate limiting

5. **Logging**: Structured logging (JSON) s centralizovaným log managementem

6. **Deploy**: Kubernetes nebo Docker Swarm

### Užitečné odkazy:

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [PyJWT Documentation](https://pyjwt.readthedocs.io)
- [Electron Documentation](https://www.electronjs.org/docs)
- [Redis Documentation](https://redis.io/docs)

## 📄 License

MIT

## 👤 Author

Created for OAuth token system demonstration.
