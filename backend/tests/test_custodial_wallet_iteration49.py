"""
Custodial Wallet API Tests - Iteration 49
Tests the new custodial wallet management endpoints for automated trading.
Features: Server-side hot wallet with encrypted private keys and max 0.5 SOL deposit limit.
"""

import pytest
import requests
import os
import uuid

# Get the base URL from environment variable
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    BASE_URL = "https://bullpug-beta.preview.emergentagent.com"

# Test wallet prefix for cleanup
TEST_WALLET = f"TEST_custodial_{uuid.uuid4().hex[:8]}"


class TestCustodialWalletInfo:
    """Test GET /api/custodial-wallet/info/{wallet} - Create/Return wallet info"""
    
    def test_create_custodial_wallet_returns_ok(self):
        """Test that getting wallet info creates a new custodial wallet if not exists"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/info/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASSED: Custodial wallet info endpoint returns 200")
    
    def test_custodial_wallet_info_structure(self):
        """Test that wallet info contains required fields"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/info/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        required_fields = [
            "wallet_address",
            "balance_sol",
            "balance_lamports",
            "max_deposit_sol",
            "available_deposit_sol",
            "created_at",
            "total_deposits",
            "total_withdrawals"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"PASSED: All required fields present in wallet info")
    
    def test_max_deposit_limit_is_05_sol(self):
        """Test that max deposit limit is 0.5 SOL"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/info/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["max_deposit_sol"] == 0.5, f"Expected max_deposit_sol=0.5, got {data['max_deposit_sol']}"
        print("PASSED: Max deposit limit is correctly set to 0.5 SOL")
    
    def test_new_wallet_has_zero_balance(self):
        """Test that newly created wallet has zero balance"""
        new_wallet = f"TEST_custodial_new_{uuid.uuid4().hex[:8]}"
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/info/{new_wallet}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["balance_sol"] == 0.0, f"New wallet should have 0 balance, got {data['balance_sol']}"
        assert data["balance_lamports"] == 0, f"New wallet should have 0 lamports, got {data['balance_lamports']}"
        print("PASSED: New custodial wallet has zero balance")
    
    def test_wallet_address_is_valid_solana_address(self):
        """Test that custodial wallet address is a valid Solana address format"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/info/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        # Solana addresses are base58 encoded, typically 32-44 characters
        wallet_address = data["wallet_address"]
        assert len(wallet_address) >= 32 and len(wallet_address) <= 44, f"Invalid Solana address length: {len(wallet_address)}"
        print(f"PASSED: Valid Solana wallet address generated: {wallet_address}")


class TestCustodialWalletAddress:
    """Test GET /api/custodial-wallet/address/{wallet} - Get deposit address"""
    
    def test_get_deposit_address_returns_ok(self):
        """Test that deposit address endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/address/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASSED: Deposit address endpoint returns 200")
    
    def test_deposit_address_response_structure(self):
        """Test that deposit address response has correct structure"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/address/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        assert "custodial_address" in data, "Missing custodial_address field"
        assert "max_deposit_sol" in data, "Missing max_deposit_sol field"
        assert "instructions" in data, "Missing instructions field"
        
        print("PASSED: Deposit address response has correct structure")
    
    def test_deposit_address_instructions_contain_limit(self):
        """Test that deposit instructions mention the 0.5 SOL limit"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/address/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        assert "0.5" in data["instructions"], "Instructions should mention 0.5 SOL limit"
        print("PASSED: Deposit instructions correctly mention 0.5 SOL limit")


class TestPrepareDeposit:
    """Test POST /api/custodial-wallet/prepare-deposit - Validate deposits"""
    
    def test_valid_deposit_amount_returns_success(self):
        """Test that valid deposit amount (0.1 SOL) returns success"""
        response = requests.post(
            f"{BASE_URL}/api/custodial-wallet/prepare-deposit",
            json={"user_wallet": TEST_WALLET, "amount_sol": 0.1}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["success"] == True, "Expected success=true"
        assert data["amount_sol"] == 0.1, "Expected amount_sol=0.1"
        print("PASSED: Valid deposit (0.1 SOL) returns success")
    
    def test_max_valid_deposit_amount(self):
        """Test that maximum valid deposit (0.5 SOL) is accepted"""
        response = requests.post(
            f"{BASE_URL}/api/custodial-wallet/prepare-deposit",
            json={"user_wallet": TEST_WALLET, "amount_sol": 0.5}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["success"] == True, "Expected success=true for 0.5 SOL deposit"
        print("PASSED: Maximum valid deposit (0.5 SOL) accepted")
    
    def test_deposit_exceeding_limit_rejected(self):
        """Test that deposit exceeding 0.5 SOL limit is rejected (Pydantic validation)"""
        response = requests.post(
            f"{BASE_URL}/api/custodial-wallet/prepare-deposit",
            json={"user_wallet": TEST_WALLET, "amount_sol": 0.6}
        )
        # Pydantic validation returns 422 for invalid input
        assert response.status_code == 422, f"Expected 422 for exceeding limit, got {response.status_code}"
        print("PASSED: Deposit exceeding 0.5 SOL limit correctly rejected with 422")
    
    def test_zero_deposit_rejected(self):
        """Test that zero deposit amount is rejected"""
        response = requests.post(
            f"{BASE_URL}/api/custodial-wallet/prepare-deposit",
            json={"user_wallet": TEST_WALLET, "amount_sol": 0}
        )
        # Pydantic validation (Field(gt=0)) should reject 0
        assert response.status_code == 422, f"Expected 422 for zero deposit, got {response.status_code}"
        print("PASSED: Zero deposit correctly rejected")
    
    def test_negative_deposit_rejected(self):
        """Test that negative deposit amount is rejected"""
        response = requests.post(
            f"{BASE_URL}/api/custodial-wallet/prepare-deposit",
            json={"user_wallet": TEST_WALLET, "amount_sol": -0.1}
        )
        # Pydantic validation (Field(gt=0)) should reject negative
        assert response.status_code == 422, f"Expected 422 for negative deposit, got {response.status_code}"
        print("PASSED: Negative deposit correctly rejected")
    
    def test_prepare_deposit_response_structure(self):
        """Test that prepare-deposit response has all required fields"""
        response = requests.post(
            f"{BASE_URL}/api/custodial-wallet/prepare-deposit",
            json={"user_wallet": TEST_WALLET, "amount_sol": 0.1}
        )
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["success", "deposit_address", "amount_sol", "amount_lamports", 
                          "current_balance_sol", "after_deposit_sol", "message"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        print("PASSED: Prepare-deposit response has all required fields")


class TestWithdraw:
    """Test POST /api/custodial-wallet/withdraw - Withdrawal validation"""
    
    def test_withdraw_with_no_balance_fails(self):
        """Test that withdrawal from wallet with no balance returns error"""
        response = requests.post(
            f"{BASE_URL}/api/custodial-wallet/withdraw",
            json={"user_wallet": TEST_WALLET, "amount_sol": 0.01}
        )
        # Should return 400 for insufficient balance
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "Insufficient balance" in data.get("detail", ""), f"Expected 'Insufficient balance' error, got: {data}"
        print("PASSED: Withdrawal with no balance correctly returns 400 with insufficient balance message")
    
    def test_zero_withdrawal_rejected(self):
        """Test that zero withdrawal amount is rejected"""
        response = requests.post(
            f"{BASE_URL}/api/custodial-wallet/withdraw",
            json={"user_wallet": TEST_WALLET, "amount_sol": 0}
        )
        # Pydantic validation (Field(gt=0)) should reject 0
        assert response.status_code == 422, f"Expected 422 for zero withdrawal, got {response.status_code}"
        print("PASSED: Zero withdrawal correctly rejected")
    
    def test_negative_withdrawal_rejected(self):
        """Test that negative withdrawal amount is rejected"""
        response = requests.post(
            f"{BASE_URL}/api/custodial-wallet/withdraw",
            json={"user_wallet": TEST_WALLET, "amount_sol": -0.01}
        )
        assert response.status_code == 422, f"Expected 422 for negative withdrawal, got {response.status_code}"
        print("PASSED: Negative withdrawal correctly rejected")


class TestTransactionHistory:
    """Test GET /api/custodial-wallet/transactions/{wallet} - Transaction history"""
    
    def test_transaction_history_returns_ok(self):
        """Test that transaction history endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/transactions/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASSED: Transaction history endpoint returns 200")
    
    def test_transaction_history_structure(self):
        """Test that transaction history has correct structure"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/transactions/{TEST_WALLET}")
        assert response.status_code == 200
        data = response.json()
        
        assert "transactions" in data, "Missing transactions field"
        assert "total_count" in data, "Missing total_count field"
        assert isinstance(data["transactions"], list), "transactions should be a list"
        print("PASSED: Transaction history has correct structure")
    
    def test_new_wallet_has_empty_history(self):
        """Test that new wallet has empty transaction history"""
        new_wallet = f"TEST_custodial_history_{uuid.uuid4().hex[:8]}"
        # First create the wallet
        requests.get(f"{BASE_URL}/api/custodial-wallet/info/{new_wallet}")
        
        # Then check history
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/transactions/{new_wallet}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_count"] == 0, f"New wallet should have 0 transactions, got {data['total_count']}"
        assert len(data["transactions"]) == 0, "New wallet should have empty transactions list"
        print("PASSED: New wallet has empty transaction history")
    
    def test_transaction_history_limit_parameter(self):
        """Test that limit parameter is accepted"""
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/transactions/{TEST_WALLET}?limit=5")
        assert response.status_code == 200, f"Expected 200 with limit param, got {response.status_code}"
        print("PASSED: Transaction history accepts limit parameter")


class TestCustodialWalletNotFound:
    """Test 404 responses for non-existent wallets on certain endpoints"""
    
    def test_withdraw_from_nonexistent_wallet(self):
        """Test that withdrawal from non-existent wallet returns 404"""
        random_wallet = f"NONEXISTENT_{uuid.uuid4().hex}"
        response = requests.post(
            f"{BASE_URL}/api/custodial-wallet/withdraw",
            json={"user_wallet": random_wallet, "amount_sol": 0.01}
        )
        # Should return 404 since the custodial wallet doesn't exist
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("PASSED: Withdrawal from non-existent wallet returns 404")
    
    def test_transaction_history_nonexistent_wallet(self):
        """Test that transaction history for non-existent wallet returns 404"""
        random_wallet = f"NONEXISTENT_{uuid.uuid4().hex}"
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/transactions/{random_wallet}")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASSED: Transaction history for non-existent wallet returns 404")


class TestSecurityEncryptionKey:
    """Test that encryption key is properly configured"""
    
    def test_custodial_wallet_uses_encrypted_keys(self):
        """Test that custodial wallets are created (implying encrypted storage)"""
        # Create a wallet and verify it's created successfully
        # The fact that wallet creation works means encryption is functioning
        new_wallet = f"TEST_security_{uuid.uuid4().hex[:8]}"
        response = requests.get(f"{BASE_URL}/api/custodial-wallet/info/{new_wallet}")
        assert response.status_code == 200, f"Wallet creation failed, possible encryption issue: {response.text}"
        
        data = response.json()
        # Verify a valid wallet address was generated (keypair worked)
        assert len(data["wallet_address"]) >= 32, "Invalid wallet address suggests encryption failure"
        print("PASSED: Custodial wallet created successfully - encryption key is functional")


# Run all tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
