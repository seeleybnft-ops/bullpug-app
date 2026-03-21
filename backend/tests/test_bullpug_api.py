"""
Backend API tests for Bullpug memecoin website
Tests: Betting Arena (Coin Toss, Pot System), Exit Simulator (Monte Carlo), Wallet, Newsletter
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://pug-journal.preview.emergentagent.com')
BASE_URL = BASE_URL.rstrip('/')


class TestHealthAndRoot:
    """Test API health and root endpoints"""
    
    def test_api_root(self):
        """Test API root returns success"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Bullpug" in data["message"]
        print(f"API Root: {data['message']}")


class TestBettingCoinToss:
    """Test Coin Toss betting functionality with provably fair verification"""
    
    def test_coin_toss_heads(self):
        """Test coin toss with heads choice"""
        payload = {
            "client_seed": "test_seed_123",
            "bet_amount": 100,
            "choice": "heads",
            "wallet_address": "TEST_wallet_123"
        }
        response = requests.post(f"{BASE_URL}/api/betting/coin-toss", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        # Verify all provably fair fields are present
        assert "outcome" in data
        assert data["outcome"] in ["heads", "tails"]
        assert "won" in data
        assert isinstance(data["won"], bool)
        assert "server_seed" in data
        assert "server_seed_hash" in data
        assert "client_seed" in data
        assert data["client_seed"] == "test_seed_123"
        assert "result_hash" in data
        assert "verification" in data
        assert "payout" in data
        assert "bet_amount" in data
        assert data["bet_amount"] == 100
        assert "house_fee_percent" in data
        assert data["house_fee_percent"] == 5
        
        # Verify provably fair: outcome is determined by last hex digit of result_hash
        last_hex = data["result_hash"][-1]
        last_digit = int(last_hex, 16)
        expected_outcome = "heads" if last_digit % 2 == 0 else "tails"
        assert data["outcome"] == expected_outcome, f"Provably fair verification failed: {last_hex} -> {last_digit} -> {expected_outcome}"
        
        print(f"Coin toss result: {data['outcome']}, won: {data['won']}, payout: {data['payout']}")
    
    def test_coin_toss_tails(self):
        """Test coin toss with tails choice"""
        payload = {
            "client_seed": "another_test_seed",
            "bet_amount": 50,
            "choice": "tails"
        }
        response = requests.post(f"{BASE_URL}/api/betting/coin-toss", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["choice"] == "tails"
        assert "outcome" in data
        assert "won" in data
        print(f"Tails choice result: outcome={data['outcome']}, won={data['won']}")
    
    def test_coin_toss_payout_calculation(self):
        """Test payout is correct when winning"""
        # Run multiple flips to find a winning one
        for i in range(10):
            payload = {
                "client_seed": f"payout_test_{i}_{time.time()}",
                "bet_amount": 100,
                "choice": "heads"
            }
            response = requests.post(f"{BASE_URL}/api/betting/coin-toss", json=payload)
            assert response.status_code == 200
            data = response.json()
            
            if data["won"]:
                # Payout should be bet_amount * 2 * (1 - house_fee/100) = 100 * 2 * 0.95 = 190
                expected_payout = round(100 * 2 * (1 - 5/100), 2)
                assert data["payout"] == expected_payout, f"Expected payout {expected_payout}, got {data['payout']}"
                print(f"Payout verification passed: bet=100, payout={data['payout']}")
                break
            else:
                assert data["payout"] == 0
    
    def test_betting_history(self):
        """Test betting history endpoint"""
        response = requests.get(f"{BASE_URL}/api/betting/history?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert "history" in data
        assert isinstance(data["history"], list)
        print(f"Betting history contains {len(data['history'])} records")


class TestBettingPotSystem:
    """Test Winner Pot system with WebSocket updates"""
    
    def test_get_pot_status(self):
        """Test getting current pot status"""
        response = requests.get(f"{BASE_URL}/api/betting/pot")
        assert response.status_code == 200
        
        data = response.json()
        assert "id" in data
        assert "total_amount" in data
        assert "entry_count" in data
        assert "entries" in data
        assert "status" in data
        assert "draw_at" in data
        assert "house_fee_percent" in data
        assert data["house_fee_percent"] == 7
        
        print(f"Pot status: total={data['total_amount']}, entries={data['entry_count']}, status={data['status']}")
    
    def test_join_pot(self):
        """Test joining the pot"""
        payload = {
            "bet_amount": 50,
            "display_name": "TEST_Guardian_1",
            "wallet_address": "TEST_wallet_pot_1"
        }
        response = requests.post(f"{BASE_URL}/api/betting/pot/join", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "probability" in data
        assert "total_pot" in data
        assert "entry_count" in data
        assert data["total_pot"] >= 50
        
        print(f"Joined pot: probability={data['probability']}%, total_pot={data['total_pot']}")
    
    def test_join_pot_second_entry(self):
        """Test adding second entry to pot for draw test"""
        payload = {
            "bet_amount": 100,
            "display_name": "TEST_Guardian_2",
            "wallet_address": "TEST_wallet_pot_2"
        }
        response = requests.post(f"{BASE_URL}/api/betting/pot/join", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["entry_count"] >= 2
        print(f"Second entry added: total_pot={data['total_pot']}, entries={data['entry_count']}")
    
    def test_join_pot_invalid_amount(self):
        """Test pot join validation - zero/negative amount"""
        payload = {
            "bet_amount": 0,
            "display_name": "TEST_Invalid"
        }
        response = requests.post(f"{BASE_URL}/api/betting/pot/join", json=payload)
        assert response.status_code == 400
        print("Correctly rejected zero bet amount")
    
    def test_pot_entries_probability(self):
        """Verify pot entries have correct probability calculation"""
        response = requests.get(f"{BASE_URL}/api/betting/pot")
        assert response.status_code == 200
        
        data = response.json()
        if data["entries"] and data["total_amount"] > 0:
            total_prob = sum(e["probability"] for e in data["entries"])
            # Total probability should be close to 100%
            assert 99 <= total_prob <= 101, f"Probabilities sum to {total_prob}%, should be ~100%"
            print(f"Probability check passed: sum={total_prob}%")
    
    def test_draw_winner_requires_min_entries(self):
        """Test that draw requires minimum 2 entries"""
        # First, get current pot status - if it has 2+ entries, this test will pass
        response = requests.get(f"{BASE_URL}/api/betting/pot")
        pot_data = response.json()
        
        if pot_data["entry_count"] >= 2:
            # Can draw
            draw_response = requests.post(f"{BASE_URL}/api/betting/pot/draw")
            assert draw_response.status_code == 200
            draw_data = draw_response.json()
            assert "winner" in draw_data
            assert "payout" in draw_data
            assert "total_pot" in draw_data
            print(f"Draw successful: winner={draw_data['winner']}, payout={draw_data['payout']}")
        else:
            print(f"Skipping draw test - only {pot_data['entry_count']} entries")


class TestExitSimulatorMonteCarlo:
    """Test Monte Carlo simulation for exit strategy"""
    
    def test_monte_carlo_basic(self):
        """Test basic Monte Carlo simulation"""
        payload = {
            "token_amount": 1000000,
            "entry_price": 0.00042,
            "volatility": 0.8,
            "drift": 0.1,
            "days": 180,
            "simulations": 500,
            "tax_rate": 15
        }
        response = requests.post(f"{BASE_URL}/api/exit-simulator/monte-carlo", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify required fields
        assert "investment" in data
        assert data["investment"] == round(1000000 * 0.00042, 2)
        assert "token_amount" in data
        assert "entry_price" in data
        assert "simulations" in data
        assert data["simulations"] == 500
        assert "days" in data
        assert data["days"] == 180
        
        # Probability fields
        assert "prob_profit" in data
        assert "prob_2x" in data
        assert "prob_5x" in data
        assert "prob_10x" in data
        assert "prob_loss50" in data
        
        # Percentile fields
        assert "price_percentiles" in data
        assert "pnl_percentiles" in data
        assert "p50" in data["price_percentiles"]
        
        # P&L summary
        assert "mean_pnl" in data
        assert "median_pnl" in data
        assert "max_pnl" in data
        assert "min_pnl" in data
        assert "mean_final_price" in data
        
        # Chart data
        assert "chart" in data
        assert "days" in data["chart"]
        assert "sample_paths" in data["chart"]
        assert "bands" in data["chart"]
        
        # Histogram
        assert "histogram" in data
        assert isinstance(data["histogram"], list)
        
        print(f"Monte Carlo simulation: prob_profit={data['prob_profit']}%, mean_pnl=${data['mean_pnl']}")
        print(f"Price percentiles: p5=${data['price_percentiles']['p5']}, median=${data['price_percentiles']['p50']}, p95=${data['price_percentiles']['p95']}")
    
    def test_monte_carlo_high_volatility(self):
        """Test simulation with high volatility (typical for memecoins)"""
        payload = {
            "token_amount": 500000,
            "entry_price": 0.001,
            "volatility": 1.5,  # 150% annual volatility
            "drift": 0.2,
            "days": 90,
            "simulations": 300,
            "tax_rate": 20
        }
        response = requests.post(f"{BASE_URL}/api/exit-simulator/monte-carlo", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["volatility"] == 1.5
        assert data["drift"] == 0.2
        # High volatility should produce wider range
        assert data["max_pnl"] > data["min_pnl"]
        print(f"High volatility simulation: max_pnl=${data['max_pnl']}, min_pnl=${data['min_pnl']}")
    
    def test_monte_carlo_chart_data_structure(self):
        """Verify chart data structure for frontend rendering"""
        payload = {
            "token_amount": 100000,
            "entry_price": 0.0005,
            "volatility": 0.6,
            "drift": 0.05,
            "days": 60,
            "simulations": 200,
            "tax_rate": 10
        }
        response = requests.post(f"{BASE_URL}/api/exit-simulator/monte-carlo", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        chart = data["chart"]
        
        # Verify bands structure
        bands = chart["bands"]
        assert "p5" in bands
        assert "p25" in bands
        assert "p50" in bands
        assert "p75" in bands
        assert "p95" in bands
        
        # All bands should have same length as days array
        days_len = len(chart["days"])
        for band_name, band_data in bands.items():
            assert len(band_data) == days_len, f"Band {band_name} length mismatch"
        
        # Sample paths should exist
        assert len(chart["sample_paths"]) > 0
        
        print(f"Chart data structure verified: {days_len} data points, {len(chart['sample_paths'])} sample paths")


class TestSimpleExitSimulator:
    """Test simple exit price calculator"""
    
    def test_exit_price_simulation(self):
        """Test exit strategy with multiple target prices"""
        payload = {
            "token_amount": 1000000,
            "entry_price": 0.00042,
            "exit_prices": [0.00084, 0.00126, 0.0021, 0.0042],
            "tax_rate": 15
        }
        response = requests.post(f"{BASE_URL}/api/exit-simulator", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "investment" in data
        assert "results" in data
        assert "optimal_exit" in data
        assert len(data["results"]) == 4
        
        # Verify result structure
        for result in data["results"]:
            assert "exit_price" in result
            assert "value" in result
            assert "pnl" in result
            assert "pnl_percent" in result
            assert "tax" in result
            assert "net_pnl" in result
        
        # Highest exit price should have highest PnL
        pnls = [r["pnl"] for r in data["results"]]
        assert pnls == sorted(pnls)  # Should be ascending
        
        print(f"Exit simulation: optimal exit at ${data['optimal_exit']['exit_price']} for net PnL ${data['optimal_exit']['net_pnl']}")


class TestTokenomicsAndWallet:
    """Test tokenomics stats and wallet balance endpoints"""
    
    def test_tokenomics_stats(self):
        """Test tokenomics statistics endpoint"""
        response = requests.get(f"{BASE_URL}/api/tokenomics/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_supply" in data
        assert data["total_supply"] == 1000000000
        assert "circulating_supply" in data
        assert "burned" in data
        assert "burn_rate" in data
        assert "distribution" in data
        assert "holders" in data
        assert "price_usd" in data
        assert "market_cap" in data
        
        print(f"Tokenomics: supply={data['total_supply']}, burned={data['burned']}, holders={data['holders']}")
    
    def test_wallet_balance_invalid_address(self):
        """Test wallet balance with invalid address returns 0"""
        response = requests.get(f"{BASE_URL}/api/wallet/balance/invalid_address_123")
        assert response.status_code == 200
        
        data = response.json()
        assert "address" in data
        assert "balance_sol" in data
        # Invalid address should return 0
        assert data["balance_sol"] == 0
        print("Invalid wallet address correctly returns 0 balance")


class TestNewsletter:
    """Test newsletter subscription"""
    
    def test_newsletter_subscribe(self):
        """Test newsletter subscription"""
        unique_email = f"TEST_user_{int(time.time())}@example.com"
        payload = {"email": unique_email}
        
        response = requests.post(f"{BASE_URL}/api/newsletter/subscribe", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "status" in data
        assert data["status"] in ["success", "existing"]
        
        print(f"Newsletter subscription: {data['message']}")
    
    def test_newsletter_duplicate_subscribe(self):
        """Test duplicate subscription returns existing status"""
        email = "TEST_duplicate@example.com"
        payload = {"email": email}
        
        # First subscription
        response1 = requests.post(f"{BASE_URL}/api/newsletter/subscribe", json=payload)
        assert response1.status_code == 200
        
        # Second subscription should return existing
        response2 = requests.post(f"{BASE_URL}/api/newsletter/subscribe", json=payload)
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["status"] == "existing"
        print("Duplicate subscription correctly detected")


class TestGovernance:
    """Test governance proposals and voting"""
    
    def test_get_proposals(self):
        """Test getting governance proposals"""
        response = requests.get(f"{BASE_URL}/api/governance/proposals")
        assert response.status_code == 200
        
        data = response.json()
        assert "proposals" in data
        assert isinstance(data["proposals"], list)
        assert len(data["proposals"]) >= 1
        
        # Verify proposal structure
        proposal = data["proposals"][0]
        assert "id" in proposal
        assert "title" in proposal
        assert "description" in proposal
        assert "status" in proposal
        assert "yes_votes" in proposal
        assert "no_votes" in proposal
        
        print(f"Found {len(data['proposals'])} governance proposals")
    
    def test_cast_vote(self):
        """Test casting a vote"""
        # Get proposals first
        response = requests.get(f"{BASE_URL}/api/governance/proposals")
        proposals = response.json()["proposals"]
        
        if proposals:
            proposal_id = proposals[0]["id"]
            unique_wallet = f"TEST_voter_{int(time.time())}"
            
            payload = {
                "proposal_id": proposal_id,
                "vote": "yes",
                "wallet_address": unique_wallet
            }
            
            response = requests.post(f"{BASE_URL}/api/governance/vote", json=payload)
            assert response.status_code == 200
            
            data = response.json()
            assert "message" in data
            assert data["vote"] == "yes"
            print(f"Successfully voted on proposal {proposal_id}")


class TestProducts:
    """Test shop products endpoint"""
    
    def test_get_products(self):
        """Test getting shop products"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        
        data = response.json()
        assert "products" in data
        assert isinstance(data["products"], list)
        
        if data["products"]:
            product = data["products"][0]
            assert "id" in product
            assert "name" in product
            assert "price" in product
            assert "description" in product
            
        print(f"Found {len(data['products'])} products in shop")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
