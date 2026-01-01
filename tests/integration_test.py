#!/usr/bin/env python3
"""
Integration tests for OAuth Token System
Tests Auth Service, LLM Service, and Redis integration
"""

import os
import sys
import json
import time
import requests
from typing import Dict, Optional

# Configuration
AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://localhost:8000')
LLM_SERVICE_URL = os.getenv('LLM_SERVICE_URL', 'http://localhost:8001')

# Test results
test_results = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "tests": []
}


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def log_test(name: str, status: bool, message: str = ""):
    """Log test result"""
    test_results["total"] += 1
    if status:
        test_results["passed"] += 1
        print(f"{Colors.GREEN}✓{Colors.END} {name}")
    else:
        test_results["failed"] += 1
        print(f"{Colors.RED}✗{Colors.END} {name}")
        if message:
            print(f"  {Colors.RED}Error: {message}{Colors.END}")

    test_results["tests"].append({
        "name": name,
        "status": "passed" if status else "failed",
        "message": message
    })


def test_health_checks():
    """Test health endpoints"""
    print(f"\n{Colors.BLUE}=== Testing Health Checks ==={Colors.END}")

    try:
        # Auth Service
        response = requests.get(f"{AUTH_SERVICE_URL}/health", timeout=5)
        log_test(
            "Auth Service health check",
            response.status_code == 200 and response.json().get("status") == "ok",
            f"Status: {response.status_code}"
        )

        # LLM Service
        response = requests.get(f"{LLM_SERVICE_URL}/health", timeout=5)
        log_test(
            "LLM Service health check",
            response.status_code == 200 and response.json().get("status") == "ok",
            f"Status: {response.status_code}"
        )
    except Exception as e:
        log_test("Health checks", False, str(e))


def test_token_generation() -> Optional[Dict]:
    """Test token generation"""
    print(f"\n{Colors.BLUE}=== Testing Token Generation ==={Colors.END}")

    try:
        response = requests.post(
            f"{AUTH_SERVICE_URL}/auth/token",
            headers={"X-User-Email": "integration-test@example.com"},
            timeout=5
        )

        log_test(
            "POST /auth/token returns 200",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )

        data = response.json()

        # Validate response structure
        has_access = "access_token" in data
        has_refresh = "refresh_token" in data
        has_type = data.get("token_type") == "Bearer"
        has_expires = "expires_in" in data

        log_test(
            "Token response has access_token",
            has_access,
            "Missing access_token"
        )

        log_test(
            "Token response has refresh_token",
            has_refresh,
            "Missing refresh_token"
        )

        log_test(
            "Token type is Bearer",
            has_type,
            f"Type: {data.get('token_type')}"
        )

        log_test(
            "Token has expires_in",
            has_expires,
            "Missing expires_in"
        )

        if all([has_access, has_refresh, has_type, has_expires]):
            return data

    except Exception as e:
        log_test("Token generation", False, str(e))

    return None


def test_llm_api_with_token(access_token: str):
    """Test LLM API with valid token"""
    print(f"\n{Colors.BLUE}=== Testing LLM API with JWT ==={Colors.END}")

    try:
        # Test with valid token
        response = requests.post(
            f"{LLM_SERVICE_URL}/llm/chat",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={"message": "Integration test message"},
            timeout=5
        )

        log_test(
            "POST /llm/chat with valid token returns 200",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )

        data = response.json()

        log_test(
            "LLM response has 'response' field",
            "response" in data,
            "Missing response field"
        )

        log_test(
            "LLM response has 'conversation_id'",
            "conversation_id" in data,
            "Missing conversation_id"
        )

        log_test(
            "LLM response has 'user_email'",
            data.get("user_email") == "integration-test@example.com",
            f"Email: {data.get('user_email')}"
        )

        # Test conversation continuity
        conv_id = data.get("conversation_id")
        response2 = requests.post(
            f"{LLM_SERVICE_URL}/llm/chat",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "message": "Follow-up message",
                "conversation_id": conv_id
            },
            timeout=5
        )

        data2 = response2.json()
        log_test(
            "Conversation ID preserved across requests",
            data2.get("conversation_id") == conv_id,
            f"Expected: {conv_id}, Got: {data2.get('conversation_id')}"
        )

    except Exception as e:
        log_test("LLM API with token", False, str(e))


def test_invalid_token():
    """Test LLM API with invalid token"""
    print(f"\n{Colors.BLUE}=== Testing Invalid Token ==={Colors.END}")

    try:
        response = requests.post(
            f"{LLM_SERVICE_URL}/llm/chat",
            headers={
                "Authorization": "Bearer invalid-token-12345",
                "Content-Type": "application/json"
            },
            json={"message": "Test"},
            timeout=5
        )

        log_test(
            "Invalid token returns 401",
            response.status_code == 401,
            f"Status: {response.status_code}"
        )

        data = response.json()
        log_test(
            "Invalid token error message",
            data.get("error") == "invalid_token",
            f"Error: {data.get('error')}"
        )

    except Exception as e:
        log_test("Invalid token handling", False, str(e))


def test_refresh_token_flow(refresh_token: str):
    """Test refresh token flow"""
    print(f"\n{Colors.BLUE}=== Testing Refresh Token Flow ==={Colors.END}")

    try:
        # Refresh token
        response = requests.post(
            f"{AUTH_SERVICE_URL}/auth/refresh",
            headers={"Content-Type": "application/json"},
            json={"refresh_token": refresh_token},
            timeout=5
        )

        log_test(
            "POST /auth/refresh returns 200",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )

        data = response.json()

        log_test(
            "Refresh returns new access_token",
            "access_token" in data,
            "Missing access_token"
        )

        # Test new token works
        if "access_token" in data:
            response2 = requests.post(
                f"{LLM_SERVICE_URL}/llm/chat",
                headers={
                    "Authorization": f"Bearer {data['access_token']}",
                    "Content-Type": "application/json"
                },
                json={"message": "Test with refreshed token"},
                timeout=5
            )

            log_test(
                "Refreshed token works in LLM API",
                response2.status_code == 200,
                f"Status: {response2.status_code}"
            )

    except Exception as e:
        log_test("Refresh token flow", False, str(e))


def test_revoke_token(refresh_token: str):
    """Test token revocation"""
    print(f"\n{Colors.BLUE}=== Testing Token Revocation ==={Colors.END}")

    try:
        # Revoke token
        response = requests.post(
            f"{AUTH_SERVICE_URL}/auth/revoke",
            headers={"Content-Type": "application/json"},
            json={"refresh_token": refresh_token},
            timeout=5
        )

        log_test(
            "POST /auth/revoke returns 200",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )

        data = response.json()
        log_test(
            "Revoke status is 'revoked'",
            data.get("status") == "revoked",
            f"Status: {data.get('status')}"
        )

        # Try to use revoked token
        response2 = requests.post(
            f"{AUTH_SERVICE_URL}/auth/refresh",
            headers={"Content-Type": "application/json"},
            json={"refresh_token": refresh_token},
            timeout=5
        )

        log_test(
            "Revoked token cannot be refreshed",
            response2.status_code == 401,
            f"Status: {response2.status_code}"
        )

    except Exception as e:
        log_test("Token revocation", False, str(e))


def test_browser_login():
    """Test browser-based login endpoint"""
    print(f"\n{Colors.BLUE}=== Testing Browser Login ==={Colors.END}")

    try:
        response = requests.get(
            f"{AUTH_SERVICE_URL}/auth/login",
            headers={"X-User-Email": "browser-test@example.com"},
            timeout=5
        )

        log_test(
            "GET /auth/login returns 200",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )

        html_content = response.text

        log_test(
            "Browser login returns HTML",
            "<!DOCTYPE html>" in html_content,
            "Not HTML response"
        )

        log_test(
            "HTML contains myapp:// callback URL",
            "myapp://auth/callback" in html_content,
            "Missing callback URL"
        )

        log_test(
            "Callback URL contains access_token",
            "access_token=" in html_content,
            "Missing access_token parameter"
        )

        log_test(
            "Callback URL contains refresh_token",
            "refresh_token=" in html_content,
            "Missing refresh_token parameter"
        )

    except Exception as e:
        log_test("Browser login", False, str(e))


def main():
    """Run all integration tests"""
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}OAuth Token System - Integration Tests{Colors.END}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.END}")

    print(f"\nAuth Service: {AUTH_SERVICE_URL}")
    print(f"LLM Service:  {LLM_SERVICE_URL}")

    # Run tests
    test_health_checks()

    tokens = test_token_generation()

    if tokens:
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")

        if access_token:
            test_llm_api_with_token(access_token)
            test_invalid_token()

        if refresh_token:
            test_refresh_token_flow(refresh_token)
            # Generate new tokens for revoke test
            new_tokens = test_token_generation()
            if new_tokens:
                test_revoke_token(new_tokens.get("refresh_token"))

    test_browser_login()

    # Print summary
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}Test Summary{Colors.END}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"Total:  {test_results['total']}")
    print(f"{Colors.GREEN}Passed: {test_results['passed']}{Colors.END}")
    print(f"{Colors.RED}Failed: {test_results['failed']}{Colors.END}")

    if test_results['failed'] == 0:
        print(f"\n{Colors.GREEN}✓ All tests passed!{Colors.END}\n")
    else:
        print(f"\n{Colors.RED}✗ Some tests failed{Colors.END}\n")

    # Save results to file
    with open('tests/test-report.json', 'w') as f:
        json.dump(test_results, f, indent=2)

    # Exit with appropriate code
    sys.exit(0 if test_results['failed'] == 0 else 1)


if __name__ == "__main__":
    main()
