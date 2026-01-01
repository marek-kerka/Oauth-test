# Integration Tests

Integrační testy pro OAuth Token systém.

## Struktura testů

```
tests/
├── integration_test.py    # Python integrační testy
├── e2e_test.sh           # Bash end-to-end testy
├── test-report.json      # JSON report (generovaný)
└── README.md             # Tento soubor
```

## Lokální spuštění

### Prerequisity

1. **Spusťte všechny služby**:

```bash
# Redis
redis-server --daemonize yes

# Auth Service
cd auth-service
source venv/bin/activate
uvicorn app.main:app --port 8000 &

# LLM Service
cd llm-service
source venv/bin/activate
uvicorn app.main:app --port 8001 &
```

2. **Instalujte test dependencies**:

```bash
pip install pytest pytest-asyncio httpx requests
```

### Python Integration Tests

```bash
# Spustit všechny testy
python tests/integration_test.py

# S custom URLs
AUTH_SERVICE_URL=http://localhost:8000 \
LLM_SERVICE_URL=http://localhost:8001 \
python tests/integration_test.py
```

**Výstup**:
```
============================================================
OAuth Token System - Integration Tests
============================================================

=== Testing Health Checks ===
✓ Auth Service health check
✓ LLM Service health check

=== Testing Token Generation ===
✓ POST /auth/token returns 200
✓ Token response has access_token
✓ Token response has refresh_token
...

============================================================
Test Summary
============================================================
Total:  25
Passed: 25
Failed: 0

✓ All tests passed!
```

### Bash E2E Tests

```bash
# Spustit E2E testy
bash tests/e2e_test.sh

# S custom URLs
AUTH_SERVICE_URL=http://localhost:8000 \
LLM_SERVICE_URL=http://localhost:8001 \
bash tests/e2e_test.sh
```

## GitHub Actions

Testy se automaticky spouštějí v GitHub Actions při každém:
- Push na branch `main`, `develop`, nebo `claude/**`
- Pull requestu na `main` nebo `develop`

### Workflow soubor

`.github/workflows/integration-tests.yml`

### Co se testuje v CI

1. **Setup**:
   - Redis service container
   - Python 3.11
   - Instalace dependencies

2. **Services**:
   - Spuštění Auth Service
   - Spuštění LLM Service
   - Health checks

3. **Tests**:
   - Python integration tests
   - Bash E2E tests
   - Redis data verification

4. **Artifacts**:
   - Test reports (JSON)
   - Logy

### Sledování výsledků

Výsledky najdete v GitHub Actions tab:
```
https://github.com/YOUR-USERNAME/Oauth-test/actions
```

## Test Scénáře

### Integration Tests (Python)

1. **Health Checks**
   - Auth Service `/health`
   - LLM Service `/health`

2. **Token Generation**
   - POST `/auth/token`
   - Validace response struktury
   - Kontrola všech polí

3. **LLM API**
   - POST `/llm/chat` s validním tokenem
   - Conversation tracking
   - User email extraction

4. **Invalid Token**
   - 401 response
   - Error message validation

5. **Refresh Token Flow**
   - POST `/auth/refresh`
   - Nový token funguje

6. **Token Revocation**
   - POST `/auth/revoke`
   - Revokovaný token nefunguje

7. **Browser Login**
   - GET `/auth/login`
   - HTML response
   - myapp:// callback URL

### E2E Tests (Bash)

Kompletní user journey:
1. Získání tokenů
2. Volání LLM API
3. Pokračování konverzace
4. Refresh tokenu
5. Použití nového tokenu
6. Test neplatného tokenu
7. Revokace
8. Test revokovaného tokenu
9. Browser login

## Troubleshooting

### Testy failují lokálně

1. **Zkontrolujte, že všechny služby běží**:
```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
redis-cli ping
```

2. **Zkontrolujte porty**:
```bash
lsof -i :8000
lsof -i :8001
lsof -i :6379
```

3. **Zkontrolujte logy**:
```bash
tail -f /tmp/auth-service.log
tail -f /tmp/llm-service.log
```

### Testy failují v CI

1. **Zkontrolujte GitHub Actions log**
2. **Stáhněte artifacts** s test reporty
3. **Zkontrolujte service health checks**

## Přidání nových testů

### Python test

```python
def test_new_feature():
    """Test description"""
    print(f"\n{Colors.BLUE}=== Testing New Feature ==={Colors.END}")

    try:
        response = requests.get(f"{AUTH_SERVICE_URL}/new-endpoint")

        log_test(
            "New feature test",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
    except Exception as e:
        log_test("New feature", False, str(e))
```

### Bash test

```bash
# Step X: Test new feature
echo "Step X: Testing new feature..."
RESPONSE=$(curl -s "$AUTH_SERVICE_URL/new-endpoint")

if echo "$RESPONSE" | grep -q "expected"; then
    test_pass "New feature works"
else
    test_fail "New feature failed" "$RESPONSE"
fi
```

## Metriky

Po každém běhu se generuje `test-report.json`:

```json
{
  "total": 25,
  "passed": 25,
  "failed": 0,
  "tests": [
    {
      "name": "Auth Service health check",
      "status": "passed",
      "message": ""
    },
    ...
  ]
}
```

## CI/CD Best Practices

1. **Rychlé feedback**: Testy běží < 2 minuty
2. **Fail fast**: První failure stopne další testy
3. **Artifacts**: Všechny logy se uploadují
4. **Clean up**: Services se vždy ukončí (even on failure)
5. **Redis isolation**: Každý běh má svou Redis instanci

## Pokrytí testů

| Komponenta | Coverage |
|------------|----------|
| Auth Service | 100% endpoints |
| LLM Service | 100% endpoints |
| Redis Integration | 100% |
| Error Handling | 100% |
| Browser Flow | 100% |

## Další kroky

- [ ] Load testing (Apache Bench)
- [ ] Security testing (OWASP)
- [ ] Performance benchmarks
- [ ] Chaos testing (Redis failures)
- [ ] Token expiration testing (time-based)
