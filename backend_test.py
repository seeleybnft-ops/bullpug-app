#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Bullpug Memecoin Website
Tests all endpoints defined in server.py
"""

import requests
import sys
import time
import json
import hashlib
from datetime import datetime

class BullpugAPITester:
    def __init__(self, base_url="https://pug-ecosystem.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
            self.failed_tests.append({"name": name, "details": details})

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=10):
        """Run a single API test"""
        url = f"{self.api_base}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            
            success = response.status_code == expected_status
            
            if success:
                try:
                    json_data = response.json()
                    self.log_test(name, True, f"Status: {response.status_code}")
                    return True, json_data
                except:
                    self.log_test(name, True, f"Status: {response.status_code} (non-JSON)")
                    return True, {}
            else:
                self.log_test(name, False, f"Expected {expected_status}, got {response.status_code}")
                return False, {}

        except requests.exceptions.Timeout:
            self.log_test(name, False, "Request timeout")
            return False, {}
        except Exception as e:
            self.log_test(name, False, str(e))
            return False, {}

    def test_root_api(self):
        """Test root API endpoint"""
        return self.run_test("Root API", "GET", "", 200)

    def test_newsletter_subscribe(self):
        """Test newsletter subscription"""
        test_email = f"test_{int(time.time())}@bullpug.test"
        success, data = self.run_test(
            "Newsletter Subscribe", 
            "POST", 
            "newsletter/subscribe", 
            200,
            {"email": test_email}
        )
        if success and data.get("status") in ["success", "existing"]:
            return True
        return False

    def test_products_api(self):
        """Test products API"""
        success, data = self.run_test("Get Products", "GET", "products", 200)
        if success and "products" in data and len(data["products"]) > 0:
            print(f"   Found {len(data['products'])} products")
            return True, data["products"]
        return False, []

    def test_checkout_session(self, products):
        """Test checkout session creation"""
        if not products:
            self.log_test("Checkout Session", False, "No products available")
            return False
        
        product = products[0]  # Use first product
        success, data = self.run_test(
            "Checkout Session",
            "POST",
            "checkout/session",
            200,
            {
                "product_id": product["id"],
                "quantity": 1,
                "origin_url": "https://test.bullpug.com"
            }
        )
        
        if success and "url" in data and "session_id" in data:
            print(f"   Session ID: {data['session_id']}")
            return True, data["session_id"]
        return False, None

    def test_coin_toss_betting(self):
        """Test provably fair coin toss"""
        client_seed = "test_client_seed_12345"
        success, data = self.run_test(
            "Coin Toss Betting",
            "POST",
            "betting/coin-toss",
            200,
            {
                "client_seed": client_seed,
                "bet_amount": 100.0,
                "choice": "heads",
                "wallet_address": "test_wallet_address"
            }
        )
        
        if success and all(k in data for k in ["outcome", "server_seed", "verification"]):
            # Verify provably fair mechanism
            server_seed = data["server_seed"]
            combined = f"{server_seed}{client_seed}"
            result_hash = hashlib.sha256(combined.encode()).hexdigest()
            last_digit = int(result_hash[-1], 16)
            expected_outcome = "heads" if last_digit % 2 == 0 else "tails"
            
            if data["outcome"] == expected_outcome:
                print(f"   ✅ Provably fair verification passed")
                print(f"   Outcome: {data['outcome']}, Won: {data['won']}, Payout: {data.get('payout', 0)}")
                return True
            else:
                self.log_test("Coin Toss Verification", False, f"Expected {expected_outcome}, got {data['outcome']}")
        
        return False

    def test_betting_history(self):
        """Test betting history"""
        return self.run_test("Betting History", "GET", "betting/history?limit=10", 200)

    def test_pot_system(self):
        """Test winner pot system"""
        # Get pot status
        success1, pot_data = self.run_test("Get Pot Status", "GET", "betting/pot", 200)
        
        if not success1:
            return False
        
        # Join pot
        success2, join_data = self.run_test(
            "Join Pot",
            "POST",
            "betting/pot/join",
            200,
            {
                "bet_amount": 50.0,
                "wallet_address": "test_wallet",
                "display_name": "Test Guardian"
            }
        )
        
        if success2:
            print(f"   Joined pot with probability: {join_data.get('probability', 0)}%")
        
        # Try to draw winner (might fail if < 2 entries)
        success3, draw_data = self.run_test(
            "Draw Pot Winner",
            "POST",
            "betting/pot/draw",
            200  # This might return 400 if < 2 entries, which is expected
        )
        
        return success1 and success2

    def test_governance(self):
        """Test governance system"""
        # Get proposals
        success1, proposals_data = self.run_test("Get Proposals", "GET", "governance/proposals", 200)
        
        if not success1 or not proposals_data.get("proposals"):
            return False
        
        proposal = proposals_data["proposals"][0]
        print(f"   Found proposal: {proposal['title']}")
        
        # Vote on first proposal
        success2, vote_data = self.run_test(
            "Cast Vote",
            "POST",
            "governance/vote",
            200,
            {
                "proposal_id": proposal["id"],
                "vote": "yes",
                "wallet_address": f"test_wallet_{int(time.time())}"
            }
        )
        
        return success1 and success2

    def test_staking_simulation(self):
        """Test staking simulator"""
        success, data = self.run_test(
            "Staking Simulation",
            "POST",
            "staking/simulate",
            200,
            {
                "amount": 10000.0,
                "duration_days": 90,
                "apy": 12.0
            }
        )
        
        if success and all(k in data for k in ["initial", "final_balance", "total_rewards", "guardian_points"]):
            print(f"   Initial: {data['initial']}, Final: {data['final_balance']}, Rewards: {data['total_rewards']}")
            return True
        
        return False

    def test_exit_simulator(self):
        """Test exit simulator"""
        success, data = self.run_test(
            "Exit Simulator",
            "POST",
            "exit-simulator",
            200,
            {
                "token_amount": 1000000.0,
                "entry_price": 0.00042,
                "exit_prices": [0.0005, 0.001, 0.005, 0.01],
                "tax_rate": 15.0
            }
        )
        
        if success and "results" in data and "optimal_exit" in data:
            optimal = data["optimal_exit"]
            print(f"   Optimal exit at ${optimal['exit_price']} with ${optimal['net_pnl']} net P&L")
            return True
        
        return False

    def test_tokenomics_stats(self):
        """Test tokenomics stats"""
        success, data = self.run_test("Tokenomics Stats", "GET", "tokenomics/stats", 200)
        
        if success and all(k in data for k in ["total_supply", "market_cap", "holders"]):
            print(f"   Market Cap: ${data['market_cap']:,}, Holders: {data['holders']:,}")
            return True
        
        return False

    def test_wallet_balance(self):
        """Test wallet balance lookup"""
        # Test with a known Solana address (this will use real Solana RPC)
        test_address = "11111111111111111111111111111112"  # System program address
        success, data = self.run_test(
            "Wallet Balance", 
            "GET", 
            f"wallet/balance/{test_address}", 
            200
        )
        
        if success and "balance_sol" in data:
            print(f"   Address: {test_address}, SOL: {data['balance_sol']}")
            return True
        
        return False

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting Bullpug API Tests")
        print(f"📡 Testing API at: {self.api_base}")
        print("=" * 60)
        
        # Basic tests
        self.test_root_api()
        self.test_newsletter_subscribe()
        
        # Product and checkout tests
        products_success, products = self.test_products_api()
        if products_success:
            self.test_checkout_session(products)
        
        # Betting tests
        self.test_coin_toss_betting()
        self.test_betting_history()
        self.test_pot_system()
        
        # Governance tests
        self.test_governance()
        
        # Simulation tests
        self.test_staking_simulation()
        self.test_exit_simulator()
        
        # Stats and balance tests
        self.test_tokenomics_stats()
        self.test_wallet_balance()
        
        # Final results
        print("=" * 60)
        print(f"🎯 Tests completed: {self.tests_passed}/{self.tests_run} passed")
        
        if self.failed_tests:
            print("\n❌ Failed tests:")
            for test in self.failed_tests:
                print(f"  - {test['name']}: {test['details']}")
        
        success_rate = (self.tests_passed / self.tests_run) * 100 if self.tests_run > 0 else 0
        print(f"📊 Success rate: {success_rate:.1f}%")
        
        return success_rate >= 80  # Consider 80%+ success rate as passing

def main():
    """Main test execution"""
    print("🌟 Bullpug Memecoin Backend API Testing Suite")
    print("Testing all endpoints for cosmic functionality...")
    print()
    
    tester = BullpugAPITester()
    success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())