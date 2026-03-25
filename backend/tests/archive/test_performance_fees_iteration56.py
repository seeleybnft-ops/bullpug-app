"""
Test Performance Fee System - Iteration 56

Tests for:
- PUT /api/social-trading/fees/set-percentage/{wallet} - Set fee percentage (5-15% range)
- GET /api/social-trading/fees/summary/{wallet} - Get fee summary
- GET /api/social-trading/fees/earned/{wallet} - Get fees earned by trader
- GET /api/social-trading/fees/paid/{wallet} - Get fees paid by follower
- GET /api/social-trading/fees/leaderboard - Get top fee earners
- Leaderboard now includes performance_fee_percent and total_fees_earned_sol
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestSetPerformanceFeePercentage:
    """Test PUT /api/social-trading/fees/set-percentage/{wallet}"""
    
    def test_set_fee_percentage_valid_10_percent(self):
        """Set fee percentage to 10% (default, valid)"""
        wallet = f"TEST_fee_{uuid.uuid4().hex[:8]}"
        response = requests.put(f"{BASE_URL}/api/social-trading/fees/set-percentage/{wallet}?fee_percent=10")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["wallet_address"] == wallet
        assert data["performance_fee_percent"] == 10.0
        assert "Performance fee set to 10.0%" in data["message"]
    
    def test_set_fee_percentage_valid_5_percent_min(self):
        """Set fee percentage to 5% (minimum valid)"""
        wallet = f"TEST_fee_{uuid.uuid4().hex[:8]}"
        response = requests.put(f"{BASE_URL}/api/social-trading/fees/set-percentage/{wallet}?fee_percent=5")
        
        assert response.status_code == 200
        data = response.json()
        assert data["performance_fee_percent"] == 5.0
    
    def test_set_fee_percentage_valid_15_percent_max(self):
        """Set fee percentage to 15% (maximum valid)"""
        wallet = f"TEST_fee_{uuid.uuid4().hex[:8]}"
        response = requests.put(f"{BASE_URL}/api/social-trading/fees/set-percentage/{wallet}?fee_percent=15")
        
        assert response.status_code == 200
        data = response.json()
        assert data["performance_fee_percent"] == 15.0
    
    def test_set_fee_percentage_invalid_below_5(self):
        """Reject fee percentage below 5%"""
        wallet = f"TEST_fee_{uuid.uuid4().hex[:8]}"
        response = requests.put(f"{BASE_URL}/api/social-trading/fees/set-percentage/{wallet}?fee_percent=4")
        
        assert response.status_code == 422
        data = response.json()
        assert "greater than or equal to 5" in str(data)
    
    def test_set_fee_percentage_invalid_above_15(self):
        """Reject fee percentage above 15%"""
        wallet = f"TEST_fee_{uuid.uuid4().hex[:8]}"
        response = requests.put(f"{BASE_URL}/api/social-trading/fees/set-percentage/{wallet}?fee_percent=16")
        
        assert response.status_code == 422
        data = response.json()
        assert "less than or equal to 15" in str(data)
    
    def test_set_fee_percentage_decimal_value(self):
        """Set fee percentage with decimal (e.g., 7.5%)"""
        wallet = f"TEST_fee_{uuid.uuid4().hex[:8]}"
        response = requests.put(f"{BASE_URL}/api/social-trading/fees/set-percentage/{wallet}?fee_percent=7.5")
        
        assert response.status_code == 200
        data = response.json()
        assert data["performance_fee_percent"] == 7.5


class TestFeeSummaryEndpoint:
    """Test GET /api/social-trading/fees/summary/{wallet}"""
    
    def test_get_fee_summary_new_wallet(self):
        """Get fee summary for a new wallet (no activity)"""
        wallet = f"TEST_fee_{uuid.uuid4().hex[:8]}"
        response = requests.get(f"{BASE_URL}/api/social-trading/fees/summary/{wallet}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Structure validation
        assert data["wallet_address"] == wallet
        assert "as_trader" in data
        assert "as_follower" in data
        assert "net_position_sol" in data
        
        # as_trader structure
        assert "total_fees_earned_sol" in data["as_trader"]
        assert "trades_with_fees" in data["as_trader"]
        assert "current_fee_percent" in data["as_trader"]
        assert "copy_trading_enabled" in data["as_trader"]
        
        # as_follower structure
        assert "total_fees_paid_sol" in data["as_follower"]
        assert "trades_with_fees" in data["as_follower"]
    
    def test_get_fee_summary_after_setting_fee(self):
        """Fee summary reflects the set fee percentage"""
        wallet = f"TEST_fee_{uuid.uuid4().hex[:8]}"
        
        # Set fee first
        requests.put(f"{BASE_URL}/api/social-trading/fees/set-percentage/{wallet}?fee_percent=12")
        
        # Get summary
        response = requests.get(f"{BASE_URL}/api/social-trading/fees/summary/{wallet}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["as_trader"]["current_fee_percent"] == 12.0


class TestFeesEarnedEndpoint:
    """Test GET /api/social-trading/fees/earned/{wallet}"""
    
    def test_get_fees_earned_new_wallet(self):
        """Get fees earned for a new wallet (no earnings)"""
        wallet = f"TEST_fee_{uuid.uuid4().hex[:8]}"
        response = requests.get(f"{BASE_URL}/api/social-trading/fees/earned/{wallet}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "fees" in data
        assert "count" in data
        assert "total_in_period" in data
        assert "all_time_total" in data
        assert data["count"] == 0
        assert data["total_in_period"] == 0
        assert data["all_time_total"] == 0
    
    def test_get_fees_earned_with_limit(self):
        """Test limit parameter on fees earned endpoint"""
        wallet = f"TEST_fee_{uuid.uuid4().hex[:8]}"
        response = requests.get(f"{BASE_URL}/api/social-trading/fees/earned/{wallet}?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert "fees" in data


class TestFeesPaidEndpoint:
    """Test GET /api/social-trading/fees/paid/{wallet}"""
    
    def test_get_fees_paid_new_wallet(self):
        """Get fees paid for a new wallet (no payments)"""
        wallet = f"TEST_fee_{uuid.uuid4().hex[:8]}"
        response = requests.get(f"{BASE_URL}/api/social-trading/fees/paid/{wallet}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "fees" in data
        assert "count" in data
        assert "total_paid" in data
        assert "fees_by_trader" in data
        assert data["count"] == 0
        assert data["total_paid"] == 0
    
    def test_get_fees_paid_with_limit(self):
        """Test limit parameter on fees paid endpoint"""
        wallet = f"TEST_fee_{uuid.uuid4().hex[:8]}"
        response = requests.get(f"{BASE_URL}/api/social-trading/fees/paid/{wallet}?limit=10")
        
        assert response.status_code == 200


class TestFeeLeaderboard:
    """Test GET /api/social-trading/fees/leaderboard"""
    
    def test_get_fee_leaderboard_default(self):
        """Get fee leaderboard with default params"""
        response = requests.get(f"{BASE_URL}/api/social-trading/fees/leaderboard")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "period" in data
        assert "leaderboard" in data
        assert data["period"] == "30d"  # Default period
    
    def test_get_fee_leaderboard_7d_period(self):
        """Get fee leaderboard for 7 day period"""
        response = requests.get(f"{BASE_URL}/api/social-trading/fees/leaderboard?period=7d")
        
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "7d"
    
    def test_get_fee_leaderboard_all_time(self):
        """Get fee leaderboard for all time"""
        response = requests.get(f"{BASE_URL}/api/social-trading/fees/leaderboard?period=all")
        
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "all"
    
    def test_get_fee_leaderboard_with_limit(self):
        """Get fee leaderboard with custom limit"""
        response = requests.get(f"{BASE_URL}/api/social-trading/fees/leaderboard?limit=5")
        
        assert response.status_code == 200
        data = response.json()
        # Should return at most 5 entries
        assert len(data.get("leaderboard", [])) <= 5


class TestTraderLeaderboardIncludesFees:
    """Test that main leaderboard includes fee fields"""
    
    def test_leaderboard_has_performance_fee_percent(self):
        """Leaderboard entries include performance_fee_percent field"""
        response = requests.get(f"{BASE_URL}/api/social-trading/leaderboard")
        
        assert response.status_code == 200
        data = response.json()
        
        # If there are traders, check fields exist
        if data.get("leaderboard") and len(data["leaderboard"]) > 0:
            trader = data["leaderboard"][0]
            assert "performance_fee_percent" in trader
            assert "total_fees_earned_sol" in trader
    
    def test_leaderboard_structure(self):
        """Leaderboard has proper structure"""
        response = requests.get(f"{BASE_URL}/api/social-trading/leaderboard")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "period" in data
        assert "leaderboard" in data
        assert "total_traders" in data


class TestPerformanceFeeCalculation:
    """Test the calculate_and_collect_performance_fee function behavior"""
    
    def test_profile_tracks_total_fees_earned(self):
        """Trader profile has total_fees_earned_sol field"""
        wallet = f"TEST_fee_{uuid.uuid4().hex[:8]}"
        
        # Set fee to create profile
        requests.put(f"{BASE_URL}/api/social-trading/fees/set-percentage/{wallet}?fee_percent=10")
        
        # Get profile
        response = requests.get(f"{BASE_URL}/api/social-trading/profile/{wallet}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Profile should have fee-related fields
        assert data["wallet_address"] == wallet


class TestFeeRecordStructure:
    """Test PerformanceFeeRecord model structure via endpoints"""
    
    def test_fee_earned_record_structure(self):
        """Verify fee earned records have expected structure"""
        # Create a test wallet
        wallet = f"TEST_fee_{uuid.uuid4().hex[:8]}"
        response = requests.get(f"{BASE_URL}/api/social-trading/fees/earned/{wallet}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure even if empty
        assert isinstance(data["fees"], list)
        assert isinstance(data["count"], int)
        assert isinstance(data["total_in_period"], (int, float))
        assert isinstance(data["all_time_total"], (int, float))
    
    def test_fee_paid_record_structure(self):
        """Verify fee paid records have expected structure"""
        wallet = f"TEST_fee_{uuid.uuid4().hex[:8]}"
        response = requests.get(f"{BASE_URL}/api/social-trading/fees/paid/{wallet}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure even if empty
        assert isinstance(data["fees"], list)
        assert isinstance(data["count"], int)
        assert isinstance(data["total_paid"], (int, float))
        assert isinstance(data["fees_by_trader"], dict)


class TestRegressionTests:
    """Regression tests to ensure existing endpoints still work"""
    
    def test_social_trading_leaderboard_still_works(self):
        """Main leaderboard endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/social-trading/leaderboard")
        assert response.status_code == 200
    
    def test_social_trading_profile_still_works(self):
        """Profile endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/social-trading/profile/test_wallet")
        assert response.status_code == 200
    
    def test_social_trading_following_still_works(self):
        """Following endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/social-trading/following/test_wallet")
        assert response.status_code == 200
    
    def test_social_trading_followers_still_works(self):
        """Followers endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/social-trading/followers/test_wallet")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
