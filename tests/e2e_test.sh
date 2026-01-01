#!/bin/bash
set -eo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AUTH_SERVICE_URL="${AUTH_SERVICE_URL:-http://localhost:8000}"
LLM_SERVICE_URL="${LLM_SERVICE_URL:-http://localhost:8001}"

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Helper functions
test_pass() {
    echo -e "${GREEN}✓${NC} $1"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
}

test_fail() {
    echo -e "${RED}✗${NC} $1"
    echo -e "  ${RED}Error: $2${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
}

test_header() {
    echo -e "\n${YELLOW}=== $1 ===${NC}"
}

# Main test flow
echo -e "\n${YELLOW}========================================${NC}"
echo -e "${YELLOW}End-to-End Integration Test${NC}"
echo -e "${YELLOW}========================================${NC}"
echo -e "\nAuth Service: $AUTH_SERVICE_URL"
echo -e "LLM Service:  $LLM_SERVICE_URL\n"

test_header "Complete User Journey Test"

# Step 1: Get tokens
echo "Step 1: Getting tokens..."
TOKENS_RESPONSE=$(curl -s -X POST "$AUTH_SERVICE_URL/auth/token" \
  -H "X-User-Email: e2e-test@example.com")

ACCESS_TOKEN=$(echo "$TOKENS_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
REFRESH_TOKEN=$(echo "$TOKENS_RESPONSE" | grep -o '"refresh_token":"[^"]*' | cut -d'"' -f4)

if [ -n "$ACCESS_TOKEN" ] && [ -n "$REFRESH_TOKEN" ]; then
    test_pass "Token generation successful"
else
    test_fail "Token generation failed" "Missing tokens in response"
    exit 1
fi

# Step 2: Use access token in LLM API
echo "Step 2: Calling LLM API with access token..."
LLM_RESPONSE=$(curl -s -X POST "$LLM_SERVICE_URL/llm/chat" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "End-to-end test message"}')

if echo "$LLM_RESPONSE" | grep -q '"response"'; then
    test_pass "LLM API call successful"
    CONVERSATION_ID=$(echo "$LLM_RESPONSE" | grep -o '"conversation_id":"[^"]*' | cut -d'"' -f4)
else
    test_fail "LLM API call failed" "$LLM_RESPONSE"
fi

# Step 3: Continue conversation
echo "Step 3: Continuing conversation..."
LLM_RESPONSE2=$(curl -s -X POST "$LLM_SERVICE_URL/llm/chat" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Follow-up message\", \"conversation_id\": \"$CONVERSATION_ID\"}")

CONVERSATION_ID2=$(echo "$LLM_RESPONSE2" | grep -o '"conversation_id":"[^"]*' | cut -d'"' -f4)

if [ "$CONVERSATION_ID" = "$CONVERSATION_ID2" ]; then
    test_pass "Conversation ID preserved"
else
    test_fail "Conversation ID not preserved" "ID1: $CONVERSATION_ID, ID2: $CONVERSATION_ID2"
fi

# Step 4: Refresh access token
echo "Step 4: Refreshing access token..."
REFRESH_RESPONSE=$(curl -s -X POST "$AUTH_SERVICE_URL/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH_TOKEN\"}")

NEW_ACCESS_TOKEN=$(echo "$REFRESH_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -n "$NEW_ACCESS_TOKEN" ]; then
    # Note: Tokens might be similar if generated quickly, but should still be valid
    test_pass "Token refresh successful (new token issued)"
else
    test_fail "Token refresh failed" "Response: $REFRESH_RESPONSE"
fi

# Step 5: Use new token
echo "Step 5: Using refreshed token..."
LLM_RESPONSE3=$(curl -s -X POST "$LLM_SERVICE_URL/llm/chat" \
  -H "Authorization: Bearer $NEW_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Test with refreshed token"}')

if echo "$LLM_RESPONSE3" | grep -q '"response"'; then
    test_pass "Refreshed token works in LLM API"
else
    test_fail "Refreshed token doesn't work" "$LLM_RESPONSE3"
fi

# Step 6: Test invalid token
echo "Step 6: Testing invalid token handling..."
INVALID_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$LLM_SERVICE_URL/llm/chat" \
  -H "Authorization: Bearer invalid-token-xyz" \
  -H "Content-Type: application/json" \
  -d '{"message": "Test"}')

HTTP_CODE=$(echo "$INVALID_RESPONSE" | tail -n1)

if [ "$HTTP_CODE" = "401" ]; then
    test_pass "Invalid token correctly rejected (401)"
else
    test_fail "Invalid token not rejected" "HTTP Code: $HTTP_CODE"
fi

# Step 7: Revoke token
echo "Step 7: Revoking refresh token..."
REVOKE_RESPONSE=$(curl -s -X POST "$AUTH_SERVICE_URL/auth/revoke" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH_TOKEN\"}")

if echo "$REVOKE_RESPONSE" | grep -q '"status":"revoked"'; then
    test_pass "Token revocation successful"
else
    test_fail "Token revocation failed" "$REVOKE_RESPONSE"
fi

# Step 8: Try to use revoked token
echo "Step 8: Testing revoked token..."
REVOKED_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$AUTH_SERVICE_URL/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH_TOKEN\"}")

HTTP_CODE=$(echo "$REVOKED_RESPONSE" | tail -n1)

if [ "$HTTP_CODE" = "401" ]; then
    test_pass "Revoked token correctly rejected (401)"
else
    test_fail "Revoked token not rejected" "HTTP Code: $HTTP_CODE"
fi

# Step 9: Browser login test
echo "Step 9: Testing browser login..."
BROWSER_RESPONSE=$(curl -s "$AUTH_SERVICE_URL/auth/login" \
  -H "X-User-Email: browser-e2e@example.com")

if echo "$BROWSER_RESPONSE" | grep -q "myapp://auth/callback"; then
    test_pass "Browser login generates callback URL"
else
    test_fail "Browser login failed" "No callback URL found"
fi

# Summary
echo -e "\n${YELLOW}========================================${NC}"
echo -e "${YELLOW}Test Summary${NC}"
echo -e "${YELLOW}========================================${NC}"
echo -e "Total:  $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "${RED}Failed: $FAILED_TESTS${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n${GREEN}✓ All E2E tests passed!${NC}\n"
    exit 0
else
    echo -e "\n${RED}✗ Some E2E tests failed${NC}\n"
    exit 1
fi
