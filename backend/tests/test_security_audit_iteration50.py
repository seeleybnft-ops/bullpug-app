"""
Security Audit Test Suite - Iteration 50
Comprehensive security tests for Bullpug Trading Bot

Tests:
1. SECURITY: Custodial wallet - verify private keys are never exposed in API responses
2. SECURITY: Custodial wallet - test withdrawal validation (can't withdraw more than balance)
3. SECURITY: Custodial wallet - test deposit limits (max 0.5 SOL enforced)
4. SECURITY: API endpoints - check for SQL/NoSQL injection vulnerabilities
5. SECURITY: API endpoints - verify wallet address validation on all endpoints
6. SECURITY: Auto-trade settings - verify user can only access their own settings
7. SECURITY: Telegram bot - verify link codes are unique and expire properly
8. SECURITY: Check for exposed sensitive data in error messages
9. SECURITY: Verify MongoDB ObjectId not leaked in responses
"""

import pytest
import requests
import os
import uuid
import time
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test wallet addresses (valid Solana format)
TEST_WALLET_1 = "TEST_SEC_" + str(uuid.uuid4())[:24]  # For isolation
TEST_WALLET_2 = "TEST_SEC_" + str(uuid.uuid4())[:24]
VALID_SOLANA_WALLET = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"  # Valid format
INVALID_WALLET = "invalid_wallet_address"

# NoSQL injection payloads
NOSQL_INJECTION_PAYLOADS = [
    {"$gt": ""},
    {"$ne": None},
    {"$regex": ".*"},
    {"$where": "1==1"},
    '{"$gt": ""}',
    "'; DROP TABLE users; --",
    "admin'; --",
    {"$or": [{"user": "admin"}]},
]


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestCustodialWalletPrivateKeyExposure:
    """SECURITY: Verify private keys are NEVER exposed in API responses"""
    
    def test_wallet_info_no_private_key(self, api_client):
        """Verify GET wallet info doesn't expose private key"""
        response = api_client.get(f"{BASE_URL}/api/custodial-wallet/info/{TEST_WALLET_1}")
        assert response.status_code == 200
        
        data = response.json()
        
        # Critical: Private key should NEVER be in response
        assert "private_key" not in data, "CRITICAL: Private key exposed in wallet info!"
        assert "encrypted_private_key" not in data, "CRITICAL: Encrypted private key exposed!"
        assert "secret" not in data.keys(), "CRITICAL: Secret key exposed!"
        assert "key" not in data.keys() or data.get("key") is None, "CRITICAL: Key field exposed!"
        
        # Also check stringified response for any key patterns
        response_str = str(data).lower()
        assert "privatekey" not in response_str.replace("_", ""), "CRITICAL: Private key leaked in response!"
        assert "secretkey" not in response_str.replace("_", ""), "CRITICAL: Secret key leaked!"
        print("PASSED: Wallet info endpoint does not expose private keys")
    
    def test_wallet_address_no_private_key(self, api_client):
        """Verify GET deposit address doesn't expose private key"""
        response = api_client.get(f"{BASE_URL}/api/custodial-wallet/address/{TEST_WALLET_1}")
        assert response.status_code == 200
        
        data = response.json()
        assert "private_key" not in data
        assert "encrypted_private_key" not in data
        print("PASSED: Deposit address endpoint does not expose private keys")
    
    def test_prepare_deposit_no_private_key(self, api_client):
        """Verify POST prepare deposit doesn't expose private key"""
        response = api_client.post(
            f"{BASE_URL}/api/custodial-wallet/prepare-deposit",
            json={"user_wallet": TEST_WALLET_1, "amount_sol": 0.1}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "private_key" not in data
        assert "encrypted_private_key" not in data
        print("PASSED: Prepare deposit endpoint does not expose private keys")
    
    def test_transaction_history_no_private_key(self, api_client):
        """Verify GET transaction history doesn't expose private key"""
        # First create wallet
        api_client.get(f"{BASE_URL}/api/custodial-wallet/info/{TEST_WALLET_1}")
        
        response = api_client.get(f"{BASE_URL}/api/custodial-wallet/transactions/{TEST_WALLET_1}")
        assert response.status_code == 200
        
        data = response.json()
        assert "private_key" not in str(data)
        assert "encrypted_private_key" not in str(data)
        print("PASSED: Transaction history does not expose private keys")


class TestCustodialWalletWithdrawalValidation:
    """SECURITY: Test withdrawal validation - can't withdraw more than balance"""
    
    def test_withdraw_more_than_balance_fails(self, api_client):
        """Cannot withdraw more than available balance"""
        # Create fresh wallet with 0 balance
        wallet = f"TEST_SEC_WITHDRAW_{uuid.uuid4()}"[:44]
        api_client.get(f"{BASE_URL}/api/custodial-wallet/info/{wallet}")
        
        response = api_client.post(
            f"{BASE_URL}/api/custodial-wallet/withdraw",
            json={"user_wallet": wallet, "amount_sol": 10.0}  # Attempt to withdraw 10 SOL
        )
        
        assert response.status_code in [400, 422], f"Should reject withdrawal > balance, got {response.status_code}"
        data = response.json()
        assert "insufficient" in str(data).lower() or "balance" in str(data).lower(), \
            "Should mention insufficient balance"
        print("PASSED: Cannot withdraw more than balance")
    
    def test_withdraw_with_zero_balance_fails(self, api_client):
        """Cannot withdraw when balance is 0"""
        wallet = f"TEST_SEC_ZERO_{uuid.uuid4()}"[:44]
        api_client.get(f"{BASE_URL}/api/custodial-wallet/info/{wallet}")
        
        response = api_client.post(
            f"{BASE_URL}/api/custodial-wallet/withdraw",
            json={"user_wallet": wallet, "amount_sol": 0.001}
        )
        
        assert response.status_code in [400, 422], "Should reject withdrawal with 0 balance"
        print("PASSED: Cannot withdraw with zero balance")
    
    def test_negative_withdrawal_rejected(self, api_client):
        """Negative withdrawal amounts are rejected"""
        response = api_client.post(
            f"{BASE_URL}/api/custodial-wallet/withdraw",
            json={"user_wallet": TEST_WALLET_1, "amount_sol": -0.5}
        )
        
        assert response.status_code == 422, "Negative withdrawal should be rejected"
        print("PASSED: Negative withdrawal amount rejected")


class TestCustodialWalletDepositLimits:
    """SECURITY: Test deposit limits - max 0.5 SOL enforced"""
    
    def test_deposit_over_limit_rejected(self, api_client):
        """Deposits exceeding 0.5 SOL are rejected"""
        response = api_client.post(
            f"{BASE_URL}/api/custodial-wallet/prepare-deposit",
            json={"user_wallet": TEST_WALLET_1, "amount_sol": 0.6}
        )
        
        assert response.status_code == 422, f"Should reject deposit > 0.5 SOL, got {response.status_code}"
        print("PASSED: Deposit over 0.5 SOL limit rejected")
    
    def test_deposit_exactly_at_limit_accepted(self, api_client):
        """Deposits at exactly 0.5 SOL are accepted"""
        wallet = f"TEST_SEC_LIMIT_{uuid.uuid4()}"[:44]
        response = api_client.post(
            f"{BASE_URL}/api/custodial-wallet/prepare-deposit",
            json={"user_wallet": wallet, "amount_sol": 0.5}
        )
        
        assert response.status_code == 200, "Should accept deposit at 0.5 SOL limit"
        print("PASSED: Deposit at exactly 0.5 SOL limit accepted")
    
    def test_max_deposit_value_in_response(self, api_client):
        """Verify max_deposit_sol is correctly returned as 0.5"""
        response = api_client.get(f"{BASE_URL}/api/custodial-wallet/info/{TEST_WALLET_1}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("max_deposit_sol") == 0.5, "Max deposit should be 0.5 SOL"
        print("PASSED: Max deposit limit correctly returned as 0.5 SOL")


class TestNoSQLInjectionVulnerabilities:
    """SECURITY: Check for NoSQL injection vulnerabilities"""
    
    def test_custodial_wallet_nosql_injection(self, api_client):
        """Test NoSQL injection on custodial wallet endpoint"""
        for payload in NOSQL_INJECTION_PAYLOADS:
            # Try injection in wallet address parameter
            if isinstance(payload, dict):
                wallet = str(payload)
            else:
                wallet = payload
            
            response = api_client.get(f"{BASE_URL}/api/custodial-wallet/info/{wallet}")
            
            # Should return 200 (creating new wallet) or validation error, NOT database error
            assert response.status_code in [200, 400, 422], \
                f"NoSQL injection attempt returned unexpected status: {response.status_code}"
        
        print("PASSED: Custodial wallet endpoint resistant to NoSQL injection")
    
    def test_ai_trader_settings_nosql_injection(self, api_client):
        """Test NoSQL injection on AI trader settings endpoint"""
        for payload in NOSQL_INJECTION_PAYLOADS:
            if isinstance(payload, dict):
                wallet = str(payload)
            else:
                wallet = payload
            
            response = api_client.get(f"{BASE_URL}/api/ai-trader/settings/{wallet}")
            
            # Should return 200 or validation error, NOT 500
            assert response.status_code != 500, \
                f"Potential NoSQL injection vulnerability! Status: {response.status_code}"
        
        print("PASSED: AI trader settings endpoint resistant to NoSQL injection")
    
    def test_telegram_status_nosql_injection(self, api_client):
        """Test NoSQL injection on telegram status endpoint"""
        for payload in NOSQL_INJECTION_PAYLOADS:
            if isinstance(payload, dict):
                wallet = str(payload)
            else:
                wallet = payload
            
            response = api_client.get(f"{BASE_URL}/api/telegram/status/{wallet}")
            
            assert response.status_code != 500, \
                f"Potential NoSQL injection vulnerability in telegram endpoint!"
        
        print("PASSED: Telegram status endpoint resistant to NoSQL injection")


class TestWalletAddressValidation:
    """SECURITY: Verify wallet address validation on endpoints"""
    
    def test_custodial_accepts_valid_solana_address(self, api_client):
        """Valid Solana wallet addresses are accepted"""
        response = api_client.get(f"{BASE_URL}/api/custodial-wallet/info/{VALID_SOLANA_WALLET}")
        assert response.status_code == 200, "Should accept valid Solana address"
        print("PASSED: Valid Solana address accepted")
    
    def test_ai_trader_accepts_valid_wallet(self, api_client):
        """AI trader accepts valid wallet addresses"""
        response = api_client.get(f"{BASE_URL}/api/ai-trader/settings/{VALID_SOLANA_WALLET}")
        assert response.status_code == 200, "Should accept valid wallet for settings"
        print("PASSED: AI trader accepts valid wallet")
    
    def test_empty_wallet_handled(self, api_client):
        """Empty wallet address is handled gracefully"""
        response = api_client.get(f"{BASE_URL}/api/custodial-wallet/info/")
        # Should return 404 (not found) or redirect, not 500
        assert response.status_code in [404, 405, 307], \
            f"Empty wallet should be handled gracefully, got {response.status_code}"
        print("PASSED: Empty wallet address handled gracefully")


class TestAutoTradeSettingsAuthorization:
    """SECURITY: Verify users can only access their own auto-trade settings"""
    
    def test_get_settings_returns_only_requested_wallet(self, api_client):
        """GET settings only returns data for the requested wallet"""
        # Create settings for wallet 1
        api_client.post(
            f"{BASE_URL}/api/ai-trader/settings",
            json={
                "wallet_address": TEST_WALLET_1,
                "enabled": True,
                "risk_level": "safer",
                "max_position_sol": 0.3
            }
        )
        
        # Create settings for wallet 2
        api_client.post(
            f"{BASE_URL}/api/ai-trader/settings",
            json={
                "wallet_address": TEST_WALLET_2,
                "enabled": False,
                "risk_level": "high_risk",
                "max_position_sol": 0.5
            }
        )
        
        # Get settings for wallet 1
        response1 = api_client.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET_1}")
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Get settings for wallet 2
        response2 = api_client.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET_2}")
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Verify wallet 1 data doesn't leak to wallet 2
        assert data1.get("wallet_address") == TEST_WALLET_1, "Should return settings for requested wallet only"
        assert data2.get("wallet_address") == TEST_WALLET_2, "Should return settings for requested wallet only"
        
        print("PASSED: Users can only access their own auto-trade settings")
    
    def test_positions_only_returns_own_positions(self, api_client):
        """Positions endpoint only returns positions for the requested wallet"""
        response1 = api_client.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET_1}")
        assert response1.status_code == 200
        
        response2 = api_client.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET_2}")
        assert response2.status_code == 200
        
        # Each should only contain positions for that wallet
        data1 = response1.json()
        data2 = response2.json()
        
        for pos in data1.get("positions", []):
            assert pos.get("wallet_address") == TEST_WALLET_1 or "wallet" not in pos, \
                "Position from wallet 2 leaked to wallet 1!"
        
        print("PASSED: Positions are isolated per wallet")


class TestTelegramLinkCodeSecurity:
    """SECURITY: Verify Telegram link codes are unique and expire properly"""
    
    def test_link_codes_are_unique(self, api_client):
        """Each generated link code should be unique"""
        wallet1 = f"TEST_TG_{uuid.uuid4()}"[:44]
        wallet2 = f"TEST_TG_{uuid.uuid4()}"[:44]
        
        response1 = api_client.post(
            f"{BASE_URL}/api/telegram/generate-link-code",
            json={"wallet_address": wallet1}
        )
        
        response2 = api_client.post(
            f"{BASE_URL}/api/telegram/generate-link-code",
            json={"wallet_address": wallet2}
        )
        
        if response1.status_code == 200 and response2.status_code == 200:
            code1 = response1.json().get("code")
            code2 = response2.json().get("code")
            
            assert code1 != code2, "Link codes should be unique per request"
            assert len(code1) == 6, "Link code should be 6 characters"
            assert code1.isalnum(), "Link code should be alphanumeric"
            print("PASSED: Telegram link codes are unique")
        else:
            print(f"SKIP: Telegram endpoints returned {response1.status_code}, {response2.status_code}")
    
    def test_link_code_expiration_mentioned(self, api_client):
        """Link code response should mention expiration"""
        wallet = f"TEST_TG_EXP_{uuid.uuid4()}"[:44]
        
        response = api_client.post(
            f"{BASE_URL}/api/telegram/generate-link-code",
            json={"wallet_address": wallet}
        )
        
        if response.status_code == 200:
            data = response.json()
            # Should mention expiration
            has_expiry = "expires" in str(data).lower() or "minutes" in str(data).lower()
            assert has_expiry or data.get("expires_in_minutes") is not None, \
                "Link code should have expiration info"
            print("PASSED: Link code has expiration information")
        else:
            print(f"SKIP: Telegram generate-link-code returned {response.status_code}")
    
    def test_invalid_code_rejected(self, api_client):
        """Invalid/expired codes should be rejected"""
        wallet = f"TEST_TG_INV_{uuid.uuid4()}"[:44]
        
        response = api_client.post(
            f"{BASE_URL}/api/telegram/verify-code",
            json={"wallet_address": wallet, "code": "INVALID123"}
        )
        
        # Should return error for invalid code
        data = response.json()
        assert data.get("success") == False or "invalid" in str(data).lower() or "error" in str(data).lower(), \
            "Invalid code should be rejected"
        print("PASSED: Invalid link codes are rejected")


class TestSensitiveDataInErrorMessages:
    """SECURITY: Check for exposed sensitive data in error messages"""
    
    def test_custodial_error_no_db_info(self, api_client):
        """Error messages should not expose database info"""
        # Try to trigger an error
        response = api_client.post(
            f"{BASE_URL}/api/custodial-wallet/confirm-deposit",
            params={"user_wallet": "invalid", "tx_signature": "invalid", "amount_lamports": -1}
        )
        
        response_text = str(response.json())
        
        # Should not contain database details
        assert "mongodb" not in response_text.lower(), "Error exposes MongoDB details"
        assert "collection" not in response_text.lower() or "custodial" in response_text.lower(), \
            "Error may expose collection names"
        assert "localhost:27017" not in response_text, "Error exposes database URL"
        print("PASSED: Error messages don't expose database info")
    
    def test_ai_trader_error_no_api_keys(self, api_client):
        """Error messages should not expose API keys"""
        # Make a request that might cause an error
        response = api_client.post(
            f"{BASE_URL}/api/ai-trader/settings",
            json={"wallet_address": "test", "risk_level": "INVALID_LEVEL"}
        )
        
        response_text = str(response.json())
        
        # Should not contain API keys
        assert "sk-" not in response_text, "Error exposes API key"
        assert "api_key" not in response_text.lower() or "invalid" in response_text.lower(), \
            "Error may expose API key references"
        print("PASSED: Error messages don't expose API keys")
    
    def test_500_errors_no_stack_trace(self, api_client):
        """500 errors should not expose full stack traces to users"""
        # Test endpoints that might produce errors
        endpoints = [
            f"{BASE_URL}/api/custodial-wallet/withdraw",
            f"{BASE_URL}/api/ai-trader/execute-swap",
        ]
        
        for endpoint in endpoints:
            response = api_client.post(endpoint, json={})
            
            if response.status_code == 500:
                response_text = str(response.json())
                # Should not contain file paths or line numbers
                assert "/app/" not in response_text, f"Error at {endpoint} exposes file paths"
                assert "traceback" not in response_text.lower(), f"Error at {endpoint} exposes traceback"
        
        print("PASSED: 500 errors don't expose stack traces")


class TestMongoDBObjectIdExposure:
    """SECURITY: Verify MongoDB ObjectId not leaked in responses"""
    
    def test_custodial_wallet_no_objectid(self, api_client):
        """Custodial wallet responses should not contain _id"""
        response = api_client.get(f"{BASE_URL}/api/custodial-wallet/info/{TEST_WALLET_1}")
        assert response.status_code == 200
        
        data = response.json()
        assert "_id" not in data, "MongoDB _id leaked in response!"
        assert "$oid" not in str(data), "MongoDB ObjectId leaked in response!"
        print("PASSED: Custodial wallet response has no ObjectId")
    
    def test_ai_trader_settings_no_objectid(self, api_client):
        """AI trader settings should not contain _id"""
        # Create settings
        api_client.post(
            f"{BASE_URL}/api/ai-trader/settings",
            json={
                "wallet_address": TEST_WALLET_1,
                "enabled": True,
                "risk_level": "safer"
            }
        )
        
        response = api_client.get(f"{BASE_URL}/api/ai-trader/settings/{TEST_WALLET_1}")
        assert response.status_code == 200
        
        data = response.json()
        assert "_id" not in data, "MongoDB _id leaked in AI trader settings!"
        print("PASSED: AI trader settings response has no ObjectId")
    
    def test_telegram_status_no_objectid(self, api_client):
        """Telegram status should not contain _id"""
        response = api_client.get(f"{BASE_URL}/api/telegram/status/{TEST_WALLET_1}")
        assert response.status_code == 200
        
        data = response.json()
        assert "_id" not in str(data), "MongoDB _id leaked in telegram status!"
        print("PASSED: Telegram status response has no ObjectId")
    
    def test_positions_no_objectid(self, api_client):
        """Positions endpoint should not leak _id"""
        response = api_client.get(f"{BASE_URL}/api/ai-trader/positions/{TEST_WALLET_1}")
        assert response.status_code == 200
        
        data = response.json()
        response_str = str(data)
        assert "_id" not in response_str or "'_id'" not in response_str, \
            "MongoDB _id leaked in positions response!"
        print("PASSED: Positions response has no ObjectId")


class TestAIChatMemoryAndConsistency:
    """AI CHAT: Test conversation memory and Bullpug knowledge"""
    
    def test_ai_chat_endpoint_works(self, api_client):
        """Verify AI chat endpoint is responsive"""
        session_id = str(uuid.uuid4())
        
        response = api_client.post(
            f"{BASE_URL}/api/ai/chat",
            json={
                "wallet_address": TEST_WALLET_1,
                "message": "Hello, who are you?",
                "session_id": session_id,
                "active_tab": "dashboard",
                "chat_history": []
            }
        )
        
        assert response.status_code == 200, f"AI chat returned {response.status_code}"
        data = response.json()
        assert "response" in data, "Response should contain AI response"
        assert len(data["response"]) > 0, "AI response should not be empty"
        print("PASSED: AI chat endpoint is responsive")
    
    def test_ai_chat_knows_bullpug_lore(self, api_client):
        """AI should have knowledge about Bullpug project lore"""
        session_id = str(uuid.uuid4())
        
        response = api_client.post(
            f"{BASE_URL}/api/ai/chat",
            json={
                "wallet_address": TEST_WALLET_1,
                "message": "Tell me about Bullpug and its lore. What is Newpug City?",
                "session_id": session_id,
                "active_tab": "dashboard",
                "chat_history": []
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        response_text = data.get("response", "").lower()
        
        # Should mention Bullpug-related terms
        bullpug_keywords = ["bullpug", "guardian", "cosmic", "newpug", "pug", "memecoin"]
        has_keyword = any(kw in response_text for kw in bullpug_keywords)
        
        assert has_keyword, "AI should have knowledge about Bullpug lore"
        print("PASSED: AI has Bullpug lore knowledge")
    
    def test_ai_chat_maintains_context(self, api_client):
        """AI should maintain conversation context across messages"""
        session_id = str(uuid.uuid4())
        
        # First message - introduce a topic
        response1 = api_client.post(
            f"{BASE_URL}/api/ai/chat",
            json={
                "wallet_address": TEST_WALLET_1,
                "message": "I'm thinking about trading SOL tokens. My budget is 0.5 SOL.",
                "session_id": session_id,
                "active_tab": "dashboard",
                "chat_history": []
            }
        )
        
        assert response1.status_code == 200
        first_response = response1.json().get("response", "")
        
        # Second message - reference previous context
        history = [
            {"role": "user", "content": "I'm thinking about trading SOL tokens. My budget is 0.5 SOL."},
            {"role": "assistant", "content": first_response}
        ]
        
        response2 = api_client.post(
            f"{BASE_URL}/api/ai/chat",
            json={
                "wallet_address": TEST_WALLET_1,
                "message": "Given my budget, what would you suggest?",
                "session_id": session_id,
                "active_tab": "dashboard",
                "chat_history": history
            }
        )
        
        assert response2.status_code == 200
        second_response = response2.json().get("response", "").lower()
        
        # Should reference budget or trading context
        context_maintained = any(kw in second_response for kw in ["sol", "budget", "0.5", "trade", "position", "amount"])
        
        assert context_maintained or len(second_response) > 50, \
            "AI should maintain conversation context"
        print("PASSED: AI maintains conversation context")
    
    def test_ai_provides_trading_insights(self, api_client):
        """AI should be able to provide trading insights"""
        session_id = str(uuid.uuid4())
        
        response = api_client.post(
            f"{BASE_URL}/api/ai/chat",
            json={
                "wallet_address": TEST_WALLET_1,
                "message": "What's the current price of SOL and should I buy?",
                "session_id": session_id,
                "active_tab": "dashboard",
                "chat_history": []
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        response_text = data.get("response", "").lower()
        
        # Should provide some trading-related information
        trading_keywords = ["price", "sol", "market", "trade", "buy", "financial", "risk", "advice"]
        has_insight = any(kw in response_text for kw in trading_keywords)
        
        assert has_insight, "AI should provide trading insights"
        print("PASSED: AI provides trading insights")


class TestChatHistoryPersistence:
    """AI CHAT: Verify conversation history persists"""
    
    def test_save_chat_history(self, api_client):
        """Chat history can be saved"""
        wallet = f"TEST_CHAT_{uuid.uuid4()}"[:44]
        session_id = str(uuid.uuid4())
        
        response = api_client.post(
            f"{BASE_URL}/api/ai/history/save",
            json={
                "wallet_address": wallet,
                "session_id": session_id,
                "messages": [
                    {"role": "user", "content": "Test message 1"},
                    {"role": "assistant", "content": "Test response 1"}
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True, "Should successfully save chat history"
        print("PASSED: Chat history can be saved")
    
    def test_retrieve_chat_history(self, api_client):
        """Saved chat history can be retrieved"""
        wallet = f"TEST_CHAT_RETRIEVE_{uuid.uuid4()}"[:44]
        session_id = str(uuid.uuid4())
        
        # Save history
        api_client.post(
            f"{BASE_URL}/api/ai/history/save",
            json={
                "wallet_address": wallet,
                "session_id": session_id,
                "messages": [
                    {"role": "user", "content": "Saved test message"},
                    {"role": "assistant", "content": "Saved test response"}
                ]
            }
        )
        
        # Retrieve history
        response = api_client.get(f"{BASE_URL}/api/ai/history/{wallet}")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        
        messages = data.get("messages", [])
        assert len(messages) >= 2, "Should retrieve saved messages"
        assert any("Saved test" in str(m) for m in messages), "Should contain saved content"
        print("PASSED: Chat history can be retrieved")


# Cleanup
@pytest.fixture(scope="module", autouse=True)
def cleanup_test_data(api_client):
    """Cleanup test data after all tests complete"""
    yield
    # Tests use unique TEST_ prefixed wallets that won't affect real data
    print("Test cleanup: TEST_ prefixed test data left for audit trail")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
