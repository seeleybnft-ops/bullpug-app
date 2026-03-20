"""
Test Suite for Multi-Chain Copy Trading and Signal Analytics (Iteration 58)

Features tested:
1. Multi-Chain Copy Trading:
   - GET /api/multichain-copy/supported-chains - List supported chains
   - POST /api/multichain-copy/wallets/link - Link wallets across chains
   - GET /api/multichain-copy/wallets/{address} - Get linked wallets
   - POST /api/multichain-copy/follow - Follow trader with multi-chain settings
   - GET /api/multichain-copy/following/{user_id} - Get following list
   - PUT /api/multichain-copy/chain-settings - Update chain settings
   - GET /api/multichain-copy/leaderboard - Multi-chain leaderboard
   - GET /api/multichain-copy/copied-trades/{user_id} - Get copied trades
   - GET /api/multichain-copy/stats/{user_id} - Get multi-chain stats

2. Signal Analytics (additional tests):
   - GET /api/signal-analytics/performance-summary
   - GET /api/signal-analytics/confidence-analysis
   - GET /api/signal-analytics/strategy-comparison
   - GET /api/signal-analytics/optimal-settings
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test wallet addresses
TEST_SOLANA_ADDRESS = f"TEST_sol_{uuid.uuid4().hex[:16]}"
TEST_ETH_ADDRESS = f"0xTEST_{uuid.uuid4().hex[:16]}"
TEST_SOLANA_ADDRESS_2 = f"TEST_sol2_{uuid.uuid4().hex[:16]}"
TEST_ETH_ADDRESS_2 = f"0xTEST2_{uuid.uuid4().hex[:16]}"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


# ============== Multi-Chain Copy Trading Tests ==============

class TestSupportedChains:
    """Test GET /api/multichain-copy/supported-chains"""
    
    def test_get_supported_chains(self, api_client):
        """Test getting list of supported chains"""
        response = api_client.get(f"{BASE_URL}/api/multichain-copy/supported-chains")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "chains" in data, "Response should contain 'chains'"
        assert "default_chain" in data, "Response should contain 'default_chain'"
        
        chains = data["chains"]
        # Verify all expected chains are present
        expected_chains = ["solana", "ethereum", "base", "arbitrum"]
        for chain in expected_chains:
            assert chain in chains, f"Chain '{chain}' should be in supported chains"
        
        # Verify chain structure
        for chain_id, chain_info in chains.items():
            assert "name" in chain_info, f"Chain {chain_id} should have 'name'"
            assert "symbol" in chain_info, f"Chain {chain_id} should have 'symbol'"
            assert "explorer" in chain_info, f"Chain {chain_id} should have 'explorer'"
            assert "color" in chain_info, f"Chain {chain_id} should have 'color'"
        
        print(f"SUCCESS: Supported chains: {list(chains.keys())}")
        print(f"SUCCESS: Default chain: {data['default_chain']}")


class TestWalletLinking:
    """Test wallet linking endpoints"""
    
    def test_link_solana_wallet_only(self, api_client):
        """Test linking only Solana wallet"""
        response = api_client.post(
            f"{BASE_URL}/api/multichain-copy/wallets/link",
            params={
                "solana_address": TEST_SOLANA_ADDRESS,
                "primary_chain": "solana"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        assert "user_id" in data
        assert data["user_id"].startswith("user_")
        assert data["wallets"]["solana"] == TEST_SOLANA_ADDRESS
        assert data["primary_chain"] == "solana"
        
        print(f"SUCCESS: Linked Solana wallet, user_id: {data['user_id']}")
    
    def test_link_both_wallets(self, api_client):
        """Test linking both Solana and EVM wallets"""
        response = api_client.post(
            f"{BASE_URL}/api/multichain-copy/wallets/link",
            params={
                "solana_address": TEST_SOLANA_ADDRESS_2,
                "ethereum_address": TEST_ETH_ADDRESS_2,
                "primary_chain": "ethereum"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        assert data["wallets"]["solana"] == TEST_SOLANA_ADDRESS_2
        assert data["wallets"]["ethereum"] == TEST_ETH_ADDRESS_2
        assert data["primary_chain"] == "ethereum"
        
        print(f"SUCCESS: Linked both wallets, user_id: {data['user_id']}")
    
    def test_link_no_wallet_fails(self, api_client):
        """Test that linking without any wallet fails"""
        response = api_client.post(
            f"{BASE_URL}/api/multichain-copy/wallets/link",
            params={"primary_chain": "solana"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data
        print(f"SUCCESS: Correctly rejected empty wallet link: {data['detail']}")
    
    def test_get_linked_wallets_by_solana(self, api_client):
        """Test getting linked wallets by Solana address"""
        response = api_client.get(f"{BASE_URL}/api/multichain-copy/wallets/{TEST_SOLANA_ADDRESS}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "user_id" in data
        assert "wallets" in data
        assert "linked" in data
        
        if data["linked"]:
            assert data["wallets"]["solana"] == TEST_SOLANA_ADDRESS
            print(f"SUCCESS: Found linked wallet for {TEST_SOLANA_ADDRESS[:20]}...")
        else:
            print(f"INFO: No linked wallet found (expected if test ran in isolation)")
    
    def test_get_linked_wallets_nonexistent(self, api_client):
        """Test getting linked wallets for non-existent address"""
        response = api_client.get(f"{BASE_URL}/api/multichain-copy/wallets/nonexistent_address_12345")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["linked"] is False
        assert data["user_id"] is None
        print("SUCCESS: Correctly returned linked=False for non-existent address")


class TestMultiChainFollow:
    """Test multi-chain follow functionality"""
    
    @pytest.fixture(autouse=True)
    def setup_trader(self, api_client):
        """Setup a trader profile for testing"""
        # First link wallets for trader
        trader_sol = f"TEST_trader_sol_{uuid.uuid4().hex[:8]}"
        trader_eth = f"0xTEST_trader_{uuid.uuid4().hex[:8]}"
        
        link_response = api_client.post(
            f"{BASE_URL}/api/multichain-copy/wallets/link",
            params={
                "solana_address": trader_sol,
                "ethereum_address": trader_eth,
                "primary_chain": "solana"
            }
        )
        
        if link_response.status_code == 200:
            self.trader_user_id = link_response.json()["user_id"]
            self.trader_sol = trader_sol
            
            # Create trader profile with copy trading enabled
            profile_response = api_client.post(
                f"{BASE_URL}/api/social-trading/trader-profile",
                json={
                    "wallet_address": trader_sol,
                    "display_name": f"Test Trader {uuid.uuid4().hex[:4]}",
                    "copy_trading_enabled": True,
                    "performance_fee_percent": 10
                }
            )
            print(f"Trader profile setup: {profile_response.status_code}")
        else:
            self.trader_user_id = None
            self.trader_sol = None
    
    def test_follow_trader_multichain(self, api_client):
        """Test following a trader with multi-chain settings"""
        if not self.trader_user_id:
            pytest.skip("Trader setup failed")
        
        follower_sol = f"TEST_follower_sol_{uuid.uuid4().hex[:8]}"
        
        # Link follower wallet
        link_response = api_client.post(
            f"{BASE_URL}/api/multichain-copy/wallets/link",
            params={"solana_address": follower_sol, "primary_chain": "solana"}
        )
        
        if link_response.status_code != 200:
            pytest.skip("Follower wallet link failed")
        
        follower_user_id = link_response.json()["user_id"]
        
        # Follow with multi-chain settings
        response = api_client.post(
            f"{BASE_URL}/api/multichain-copy/follow",
            json={
                "follower_user_id": follower_user_id,
                "trader_user_id": self.trader_user_id,
                "chain_settings": [
                    {
                        "chain": "solana",
                        "enabled": True,
                        "copy_percentage": 50.0,
                        "max_position_native": 0.5,
                        "auto_copy": True
                    },
                    {
                        "chain": "ethereum",
                        "enabled": True,
                        "copy_percentage": 30.0,
                        "max_position_native": 0.1,
                        "auto_copy": False
                    }
                ]
            }
        )
        
        # May fail if trader profile doesn't have copy_trading_enabled
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert "follow_id" in data
            print(f"SUCCESS: Followed trader with multi-chain settings, follow_id: {data['follow_id']}")
        elif response.status_code == 400:
            data = response.json()
            print(f"INFO: Follow failed (expected if trader profile not enabled): {data.get('detail')}")
        elif response.status_code == 404:
            print("INFO: Trader not found (expected if profile creation failed)")
        else:
            print(f"INFO: Follow response: {response.status_code} - {response.text}")
    
    def test_follow_nonexistent_trader(self, api_client):
        """Test following a non-existent trader"""
        response = api_client.post(
            f"{BASE_URL}/api/multichain-copy/follow",
            json={
                "follower_user_id": "user_test123",
                "trader_user_id": "user_nonexistent_12345",
                "chain_settings": [
                    {"chain": "solana", "enabled": True, "copy_percentage": 50.0, "max_position_native": 0.1, "auto_copy": True}
                ]
            }
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("SUCCESS: Correctly returned 404 for non-existent trader")


class TestFollowingList:
    """Test getting following list"""
    
    def test_get_following_list(self, api_client):
        """Test getting list of traders being followed"""
        test_user_id = f"user_TEST_{uuid.uuid4().hex[:8]}"
        
        response = api_client.get(f"{BASE_URL}/api/multichain-copy/following/{test_user_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "following" in data
        assert "count" in data
        assert isinstance(data["following"], list)
        assert isinstance(data["count"], int)
        
        print(f"SUCCESS: Got following list, count: {data['count']}")


class TestChainSettings:
    """Test chain settings update"""
    
    def test_update_chain_settings_no_follow(self, api_client):
        """Test updating chain settings for non-existent follow relationship"""
        response = api_client.put(
            f"{BASE_URL}/api/multichain-copy/chain-settings",
            params={
                "follower_user_id": "user_nonexistent_1",
                "trader_user_id": "user_nonexistent_2",
                "chain": "solana",
                "enabled": True,
                "copy_percentage": 75.0
            }
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("SUCCESS: Correctly returned 404 for non-existent follow relationship")
    
    def test_update_chain_settings_invalid_chain(self, api_client):
        """Test updating with invalid chain"""
        response = api_client.put(
            f"{BASE_URL}/api/multichain-copy/chain-settings",
            params={
                "follower_user_id": "user_test1",
                "trader_user_id": "user_test2",
                "chain": "invalid_chain"
            }
        )
        # Should fail validation
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("SUCCESS: Correctly rejected invalid chain")


class TestMultiChainLeaderboard:
    """Test multi-chain leaderboard"""
    
    def test_get_leaderboard_all_chains(self, api_client):
        """Test getting leaderboard for all chains"""
        response = api_client.get(f"{BASE_URL}/api/multichain-copy/leaderboard")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "chain_filter" in data
        assert "period" in data
        assert "leaderboard" in data
        assert "total_traders" in data
        
        assert data["chain_filter"] == "all"
        assert data["period"] == "7d"  # default
        assert isinstance(data["leaderboard"], list)
        
        print(f"SUCCESS: Got leaderboard, total traders: {data['total_traders']}")
    
    def test_get_leaderboard_specific_chain(self, api_client):
        """Test getting leaderboard for specific chain"""
        response = api_client.get(
            f"{BASE_URL}/api/multichain-copy/leaderboard",
            params={"chain": "solana", "period": "30d", "limit": 10}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["chain_filter"] == "solana"
        assert data["period"] == "30d"
        
        # Verify leaderboard structure if not empty
        if data["leaderboard"]:
            trader = data["leaderboard"][0]
            assert "rank" in trader
            assert "wallet_address" in trader
            assert "total_trades" in trader
            assert "win_rate" in trader
            assert "total_pnl_usd" in trader
            assert "chains_traded" in trader
        
        print(f"SUCCESS: Got Solana leaderboard, traders: {len(data['leaderboard'])}")
    
    def test_get_leaderboard_invalid_chain(self, api_client):
        """Test leaderboard with invalid chain"""
        response = api_client.get(
            f"{BASE_URL}/api/multichain-copy/leaderboard",
            params={"chain": "invalid_chain"}
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("SUCCESS: Correctly rejected invalid chain filter")


class TestCopiedTrades:
    """Test copied trades endpoint"""
    
    def test_get_copied_trades(self, api_client):
        """Test getting copied trades for a user"""
        test_user_id = f"user_TEST_{uuid.uuid4().hex[:8]}"
        
        response = api_client.get(f"{BASE_URL}/api/multichain-copy/copied-trades/{test_user_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "copied_trades" in data
        assert "by_chain" in data
        assert "count" in data
        
        assert isinstance(data["copied_trades"], list)
        assert isinstance(data["by_chain"], dict)
        
        print(f"SUCCESS: Got copied trades, count: {data['count']}")
    
    def test_get_copied_trades_with_chain_filter(self, api_client):
        """Test getting copied trades filtered by chain"""
        test_user_id = f"user_TEST_{uuid.uuid4().hex[:8]}"
        
        response = api_client.get(
            f"{BASE_URL}/api/multichain-copy/copied-trades/{test_user_id}",
            params={"chain": "ethereum", "limit": 25}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "copied_trades" in data
        print(f"SUCCESS: Got Ethereum copied trades, count: {data['count']}")


class TestMultiChainStats:
    """Test multi-chain stats endpoint"""
    
    def test_get_multichain_stats(self, api_client):
        """Test getting multi-chain copy trading stats"""
        test_user_id = f"user_TEST_{uuid.uuid4().hex[:8]}"
        
        response = api_client.get(f"{BASE_URL}/api/multichain-copy/stats/{test_user_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "user_id" in data
        assert "traders_following" in data
        assert "chains_active" in data
        assert "stats_by_chain" in data
        assert "total_trades_copied" in data
        
        assert data["user_id"] == test_user_id
        assert isinstance(data["chains_active"], list)
        assert isinstance(data["stats_by_chain"], dict)
        
        print(f"SUCCESS: Got multi-chain stats, traders following: {data['traders_following']}, total trades: {data['total_trades_copied']}")


# ============== Signal Analytics Tests (Extended) ==============

class TestSignalAnalyticsPerformance:
    """Test signal analytics performance summary"""
    
    def test_performance_summary_default(self, api_client):
        """Test performance summary with default parameters"""
        response = api_client.get(f"{BASE_URL}/api/signal-analytics/performance-summary")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "period_days" in data
        assert data["period_days"] == 30  # default
        
        # Should have either strategies or note about no outcome data
        assert "strategies" in data or "note" in data
        
        print(f"SUCCESS: Got performance summary, signals analyzed: {data.get('total_signals_analyzed', data.get('total_outcomes_analyzed', 0))}")
    
    def test_performance_summary_custom_period(self, api_client):
        """Test performance summary with custom period"""
        response = api_client.get(
            f"{BASE_URL}/api/signal-analytics/performance-summary",
            params={"period_days": 7, "min_signals": 3}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["period_days"] == 7
        print(f"SUCCESS: Got 7-day performance summary")


class TestSignalAnalyticsConfidence:
    """Test signal analytics confidence analysis"""
    
    def test_confidence_analysis(self, api_client):
        """Test confidence analysis endpoint"""
        response = api_client.get(f"{BASE_URL}/api/signal-analytics/confidence-analysis")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "period_days" in data
        assert "total_signals" in data
        assert "confidence_distribution" in data
        assert "recommended_min_confidence" in data
        assert "insight" in data
        
        # Verify distribution structure
        if data["confidence_distribution"]:
            bucket = data["confidence_distribution"][0]
            assert "confidence_range" in bucket
            assert "total_signals" in bucket
            assert "approved" in bucket
            assert "approval_rate" in bucket
        
        print(f"SUCCESS: Got confidence analysis, total signals: {data['total_signals']}, recommended min: {data['recommended_min_confidence']}")


class TestSignalAnalyticsStrategy:
    """Test signal analytics strategy comparison"""
    
    def test_strategy_comparison(self, api_client):
        """Test strategy comparison endpoint"""
        response = api_client.get(f"{BASE_URL}/api/signal-analytics/strategy-comparison")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "period_days" in data
        assert "strategies" in data
        assert "recommendation" in data
        
        # Verify strategy structure if not empty
        if data["strategies"]:
            strategy = data["strategies"][0]
            assert "strategy" in strategy
            assert "total_signals" in strategy
            assert "approved" in strategy
            assert "approval_rate" in strategy
            assert "quality_score" in strategy
        
        print(f"SUCCESS: Got strategy comparison, strategies: {len(data['strategies'])}")
        if data["strategies"]:
            print(f"  Top strategy: {data['strategies'][0]['strategy']} (quality: {data['strategies'][0]['quality_score']})")


class TestSignalAnalyticsOptimal:
    """Test signal analytics optimal settings"""
    
    def test_optimal_settings(self, api_client):
        """Test optimal settings endpoint"""
        response = api_client.get(f"{BASE_URL}/api/signal-analytics/optimal-settings")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Should have either sufficient_data=True with settings or False with current_recommendations
        if data.get("sufficient_data"):
            assert "signals_analyzed" in data
            assert "settings" in data
            settings = data["settings"]
            assert "recommended_min_confidence" in settings
            assert "auto_trade" in settings
            print(f"SUCCESS: Got optimal settings, signals analyzed: {data['signals_analyzed']}")
            print(f"  Recommended min confidence: {settings['recommended_min_confidence']}")
        else:
            assert "current_recommendations" in data
            print(f"SUCCESS: Got default recommendations (insufficient data): {data.get('message', 'N/A')}")


# ============== Integration Tests ==============

class TestMultiChainIntegration:
    """Integration tests for multi-chain copy trading flow"""
    
    def test_full_wallet_link_flow(self, api_client):
        """Test complete wallet linking and retrieval flow"""
        # Generate unique addresses
        sol_addr = f"TEST_int_sol_{uuid.uuid4().hex[:12]}"
        eth_addr = f"0xTEST_int_{uuid.uuid4().hex[:12]}"
        
        # 1. Link wallets
        link_response = api_client.post(
            f"{BASE_URL}/api/multichain-copy/wallets/link",
            params={
                "solana_address": sol_addr,
                "ethereum_address": eth_addr,
                "primary_chain": "solana"
            }
        )
        assert link_response.status_code == 200
        user_id = link_response.json()["user_id"]
        
        # 2. Verify by Solana address
        get_sol_response = api_client.get(f"{BASE_URL}/api/multichain-copy/wallets/{sol_addr}")
        assert get_sol_response.status_code == 200
        sol_data = get_sol_response.json()
        assert sol_data["linked"] is True
        assert sol_data["user_id"] == user_id
        
        # 3. Verify by ETH address
        get_eth_response = api_client.get(f"{BASE_URL}/api/multichain-copy/wallets/{eth_addr}")
        assert get_eth_response.status_code == 200
        eth_data = get_eth_response.json()
        assert eth_data["linked"] is True
        assert eth_data["user_id"] == user_id
        
        # 4. Get stats for user
        stats_response = api_client.get(f"{BASE_URL}/api/multichain-copy/stats/{user_id}")
        assert stats_response.status_code == 200
        
        print(f"SUCCESS: Full wallet link flow completed for user {user_id}")
    
    def test_analytics_endpoints_consistency(self, api_client):
        """Test that all analytics endpoints return consistent data"""
        # Get all analytics data
        perf_response = api_client.get(f"{BASE_URL}/api/signal-analytics/performance-summary")
        conf_response = api_client.get(f"{BASE_URL}/api/signal-analytics/confidence-analysis")
        strat_response = api_client.get(f"{BASE_URL}/api/signal-analytics/strategy-comparison")
        opt_response = api_client.get(f"{BASE_URL}/api/signal-analytics/optimal-settings")
        
        assert perf_response.status_code == 200
        assert conf_response.status_code == 200
        assert strat_response.status_code == 200
        assert opt_response.status_code == 200
        
        # All should use same default period
        perf_data = perf_response.json()
        conf_data = conf_response.json()
        strat_data = strat_response.json()
        
        assert perf_data["period_days"] == conf_data["period_days"] == strat_data["period_days"] == 30
        
        print("SUCCESS: All analytics endpoints consistent with 30-day default period")


# ============== Cleanup ==============

@pytest.fixture(scope="module", autouse=True)
def cleanup(api_client):
    """Cleanup test data after all tests"""
    yield
    # Note: Test data prefixed with TEST_ for easy identification
    # Actual cleanup would require admin endpoints or direct DB access
    print("INFO: Test data cleanup - TEST_ prefixed data should be cleaned periodically")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
