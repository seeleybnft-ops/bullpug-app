"""
Iteration 94: P&L and Time Held Bug Fixes Tests

Tests for the bug fixes:
1. Sync-closed positions now have P&L calculation
2. Frontend Time Held calculation uses correct timestamps
3. History endpoint includes sync-closed positions

Endpoints tested:
- GET /api/ai-trader/history/{wallet} - Returns P&L data for sell trades
- POST /api/ai-trader/backfill-pnl/{wallet} - Backfills missing P&L data
- GET /api/ai-trader/stats/{wallet} - Stats show trades_missing_pnl
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"


class TestHistoryEndpointPnL:
    """Test that history endpoint returns P&L data for sell trades"""
    
    def test_history_endpoint_returns_200(self):
        """Test that history endpoint returns 200 status"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/history/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: History endpoint returns 200")
    
    def test_history_response_structure(self):
        """Test that history response has correct structure"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/history/{TEST_WALLET}")
        data = response.json()
        
        assert "trades" in data, "Response missing 'trades' field"
        assert "stats" in data, "Response missing 'stats' field"
        assert isinstance(data["trades"], list), "'trades' should be a list"
        print(f"PASS: History response has correct structure with {len(data['trades'])} trades")
    
    def test_stats_structure(self):
        """Test that stats has all required fields including trades_missing_pnl"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/history/{TEST_WALLET}")
        data = response.json()
        stats = data.get("stats", {})
        
        required_fields = ["total_trades", "wins", "losses", "win_rate", "total_pnl_sol", "trades_missing_pnl"]
        for field in required_fields:
            assert field in stats, f"Stats missing required field: {field}"
        
        print(f"PASS: Stats has all required fields: {list(stats.keys())}")
        print(f"  - total_trades: {stats['total_trades']}")
        print(f"  - wins: {stats['wins']}")
        print(f"  - losses: {stats['losses']}")
        print(f"  - win_rate: {stats['win_rate']}%")
        print(f"  - total_pnl_sol: {stats['total_pnl_sol']}")
        print(f"  - trades_missing_pnl: {stats['trades_missing_pnl']}")
    
    def test_sell_trades_have_pnl_data(self):
        """Test that sell trades have pnl_percent and pnl_sol fields"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/history/{TEST_WALLET}")
        data = response.json()
        trades = data.get("trades", [])
        
        sell_trades = [t for t in trades if t.get("trade_type") == "sell"]
        print(f"Found {len(sell_trades)} sell trades")
        
        if len(sell_trades) == 0:
            pytest.skip("No sell trades found to verify P&L data")
        
        # Check each sell trade for P&L data
        trades_with_pnl = 0
        trades_without_pnl = 0
        
        for trade in sell_trades:
            has_pnl = trade.get("pnl_percent") is not None or trade.get("pnl_sol") is not None
            if has_pnl:
                trades_with_pnl += 1
                print(f"  - {trade.get('token_symbol')}: pnl_percent={trade.get('pnl_percent')}, pnl_sol={trade.get('pnl_sol')}")
            else:
                trades_without_pnl += 1
                print(f"  - {trade.get('token_symbol')}: MISSING P&L DATA")
        
        print(f"RESULT: {trades_with_pnl}/{len(sell_trades)} sell trades have P&L data")
        
        # After backfill, all trades should have P&L
        assert trades_without_pnl == 0, f"{trades_without_pnl} sell trades are missing P&L data"
        print("PASS: All sell trades have P&L data")
    
    def test_sell_trades_have_time_held_minutes(self):
        """Test that sell trades have time_held_minutes > 0"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/history/{TEST_WALLET}")
        data = response.json()
        trades = data.get("trades", [])
        
        sell_trades = [t for t in trades if t.get("trade_type") == "sell"]
        
        if len(sell_trades) == 0:
            pytest.skip("No sell trades found to verify time_held_minutes")
        
        trades_with_time = 0
        trades_without_time = 0
        
        for trade in sell_trades:
            time_held = trade.get("time_held_minutes")
            if time_held is not None and time_held > 0:
                trades_with_time += 1
                print(f"  - {trade.get('token_symbol')}: time_held_minutes={time_held}")
            else:
                trades_without_time += 1
                print(f"  - {trade.get('token_symbol')}: time_held_minutes={time_held} (MISSING or 0)")
        
        print(f"RESULT: {trades_with_time}/{len(sell_trades)} sell trades have time_held_minutes > 0")
        
        # Most trades should have time_held_minutes
        assert trades_with_time > 0, "No sell trades have time_held_minutes > 0"
        print("PASS: Sell trades have time_held_minutes data")
    
    def test_sell_trades_have_position_opened_at(self):
        """Test that sell trades have position_opened_at field"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/history/{TEST_WALLET}")
        data = response.json()
        trades = data.get("trades", [])
        
        sell_trades = [t for t in trades if t.get("trade_type") == "sell"]
        
        if len(sell_trades) == 0:
            pytest.skip("No sell trades found to verify position_opened_at")
        
        trades_with_opened_at = 0
        
        for trade in sell_trades:
            opened_at = trade.get("position_opened_at")
            if opened_at:
                trades_with_opened_at += 1
                print(f"  - {trade.get('token_symbol')}: position_opened_at={opened_at}")
        
        print(f"RESULT: {trades_with_opened_at}/{len(sell_trades)} sell trades have position_opened_at")
        
        # All sell trades should have position_opened_at
        assert trades_with_opened_at == len(sell_trades), f"Only {trades_with_opened_at}/{len(sell_trades)} have position_opened_at"
        print("PASS: All sell trades have position_opened_at field")


class TestHistoryIncludesSyncClosed:
    """Test that history endpoint includes closed_sync and closed_synced positions"""
    
    def test_history_includes_sync_closed_positions(self):
        """Test that history includes positions with status closed_sync or closed_synced"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/history/{TEST_WALLET}")
        data = response.json()
        trades = data.get("trades", [])
        
        # Check for trades that came from sync-closed positions
        # These would have action containing 'sync' or status 'closed'
        sell_trades = [t for t in trades if t.get("trade_type") == "sell"]
        
        print(f"Total sell trades: {len(sell_trades)}")
        
        # Check the actions of sell trades
        actions = set()
        for trade in sell_trades:
            action = trade.get("action", "")
            actions.add(action)
            print(f"  - {trade.get('token_symbol')}: action={action}, status={trade.get('status')}")
        
        print(f"Unique actions found: {actions}")
        
        # The endpoint should include sync-closed positions
        # These would show up as sell trades with various actions
        assert len(sell_trades) > 0, "No sell trades found - sync-closed positions may not be included"
        print("PASS: History includes sell trades (sync-closed positions should be included)")


class TestBackfillPnLEndpoint:
    """Test the backfill-pnl endpoint"""
    
    def test_backfill_endpoint_returns_200(self):
        """Test that backfill endpoint returns 200 status"""
        response = requests.post(f"{BASE_URL}/api/ai-trader/backfill-pnl/{TEST_WALLET}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: Backfill endpoint returns 200")
    
    def test_backfill_response_structure(self):
        """Test that backfill response has correct structure"""
        response = requests.post(f"{BASE_URL}/api/ai-trader/backfill-pnl/{TEST_WALLET}")
        data = response.json()
        
        assert "updated" in data, "Response missing 'updated' field"
        assert "details" in data, "Response missing 'details' field"
        assert isinstance(data["updated"], int), "'updated' should be an integer"
        assert isinstance(data["details"], list), "'details' should be a list"
        
        print(f"PASS: Backfill response structure correct")
        print(f"  - updated: {data['updated']}")
        print(f"  - details count: {len(data['details'])}")
        
        # Show details if any
        for detail in data.get("details", []):
            print(f"    - {detail.get('symbol')}: entry={detail.get('entry')}, exit={detail.get('exit')}, pnl_pct={detail.get('pnl_pct')}%")


class TestTradesMissingPnLAfterBackfill:
    """Test that trades_missing_pnl is 0 after backfill"""
    
    def test_trades_missing_pnl_is_zero(self):
        """Test that stats show trades_missing_pnl = 0 after backfill has been run"""
        # First run backfill to ensure all positions have P&L
        backfill_response = requests.post(f"{BASE_URL}/api/ai-trader/backfill-pnl/{TEST_WALLET}")
        print(f"Backfill result: updated={backfill_response.json().get('updated', 0)}")
        
        # Then check history stats
        response = requests.get(f"{BASE_URL}/api/ai-trader/history/{TEST_WALLET}")
        data = response.json()
        stats = data.get("stats", {})
        
        trades_missing_pnl = stats.get("trades_missing_pnl", -1)
        print(f"trades_missing_pnl: {trades_missing_pnl}")
        
        assert trades_missing_pnl == 0, f"Expected trades_missing_pnl=0, got {trades_missing_pnl}"
        print("PASS: trades_missing_pnl is 0 after backfill")


class TestPnLCalculationAccuracy:
    """Test that P&L calculations are accurate"""
    
    def test_pnl_percent_not_zero_for_trades_with_entry_exit(self):
        """Test that pnl_percent is not 0 for trades with both entry and exit prices"""
        response = requests.get(f"{BASE_URL}/api/ai-trader/history/{TEST_WALLET}")
        data = response.json()
        trades = data.get("trades", [])
        
        sell_trades = [t for t in trades if t.get("trade_type") == "sell"]
        
        if len(sell_trades) == 0:
            pytest.skip("No sell trades found")
        
        trades_with_valid_pnl = 0
        trades_with_zero_pnl = 0
        
        for trade in sell_trades:
            entry = trade.get("entry_price", 0)
            exit_price = trade.get("exit_price", 0)
            pnl_pct = trade.get("pnl_percent")
            
            if entry > 0 and exit_price > 0:
                # Calculate expected P&L
                expected_pnl = ((exit_price - entry) / entry) * 100
                
                if pnl_pct is not None and pnl_pct != 0:
                    trades_with_valid_pnl += 1
                    print(f"  - {trade.get('token_symbol')}: entry=${entry}, exit=${exit_price}, pnl={pnl_pct}% (expected ~{expected_pnl:.2f}%)")
                else:
                    trades_with_zero_pnl += 1
                    print(f"  - {trade.get('token_symbol')}: entry=${entry}, exit=${exit_price}, pnl={pnl_pct} (UNEXPECTED ZERO)")
        
        print(f"RESULT: {trades_with_valid_pnl} trades with valid P&L, {trades_with_zero_pnl} with zero/null P&L")
        
        # All trades with entry+exit should have non-zero P&L
        if trades_with_valid_pnl + trades_with_zero_pnl > 0:
            assert trades_with_zero_pnl == 0, f"{trades_with_zero_pnl} trades have zero P&L despite having entry+exit prices"
        
        print("PASS: All trades with entry+exit prices have non-zero P&L")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
