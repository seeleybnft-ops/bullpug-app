"""
Backend test suite for critical AI Trader trading paths.
Tests API endpoints, data integrity, and key business logic.
Run with: cd /app/backend && python -m pytest tests/ -v
"""
import pytest
import httpx
import os

API_URL = os.environ.get("REACT_APP_BACKEND_URL") or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].strip().split("\n")[0].strip()
API = f"{API_URL}/api"
WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
CUSTODIAL_WALLET = "B2ykf4kaFpvHJPT6XRoBeEnjaTqLSzo3n9eZSNRVuMVC"


@pytest.fixture
def client():
    return httpx.Client(timeout=30)


# ========================
# Health & Core Endpoints
# ========================

class TestCoreEndpoints:
    def test_runners_endpoint(self, client):
        r = client.get(f"{API}/ai-trader/runners")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, (list, dict))

    def test_disclaimer(self, client):
        r = client.get(f"{API}/ai-trader/disclaimer")
        assert r.status_code == 200

    def test_available_tokens(self, client):
        r = client.get(f"{API}/ai-trader/tokens")
        assert r.status_code == 200


# ========================
# Position Management
# ========================

class TestPositions:
    def test_get_open_positions(self, client):
        r = client.get(f"{API}/ai-trader/positions/{WALLET}")
        assert r.status_code == 200
        data = r.json()
        assert "positions" in data
        assert isinstance(data["positions"], list)

    def test_positions_have_required_fields(self, client):
        r = client.get(f"{API}/ai-trader/positions/{WALLET}")
        data = r.json()
        for pos in data["positions"]:
            assert "token_symbol" in pos
            assert "status" in pos
            # Verify no raw ObjectId leak
            assert "_id" not in pos

    def test_positions_active_statuses(self, client):
        """Positions endpoint should include pending_stop_loss and pending_take_profit."""
        r = client.get(f"{API}/ai-trader/positions/{WALLET}")
        data = r.json()
        for pos in data["positions"]:
            assert pos["status"] in ["open", "pending_stop_loss", "pending_take_profit"], \
                f"Unexpected status '{pos['status']}' in open positions"


# ========================
# Trade History & Stats
# ========================

class TestTradeHistory:
    def test_trade_history(self, client):
        r = client.get(f"{API}/ai-trader/history/{WALLET}")
        assert r.status_code == 200
        data = r.json()
        assert "trades" in data
        assert "stats" in data
        assert isinstance(data["stats"], dict)

    def test_stats_have_key_fields(self, client):
        r = client.get(f"{API}/ai-trader/history/{WALLET}")
        stats = r.json()["stats"]
        for key in ["win_rate", "total_pnl_sol", "total_trades"]:
            assert key in stats, f"Missing stat: {key}"

    def test_history_no_objectid_leak(self, client):
        r = client.get(f"{API}/ai-trader/history/{WALLET}")
        data = r.json()
        for trade in data["trades"]:
            assert "_id" not in trade


# ========================
# Auto-Trade System
# ========================

class TestAutoTrade:
    def test_auto_trade_status(self, client):
        r = client.get(f"{API}/ai-trader/auto-trade/status/{WALLET}")
        assert r.status_code == 200
        data = r.json()
        assert "enabled" in data or "auto_trade_enabled" in data

    def test_auto_trade_logs(self, client):
        r = client.get(f"{API}/ai-trader/auto-trade/logs/{WALLET}")
        assert r.status_code == 200
        data = r.json()
        assert "logs" in data
        assert isinstance(data["logs"], list)

    def test_scan_and_execute_respects_cooldown(self, client):
        """Scan should either execute or report cooldown — never crash."""
        r = client.post(f"{API}/ai-trader/auto-trade/scan-and-execute/{WALLET}")
        assert r.status_code == 200
        data = r.json()
        # Should have message (cooldown or result)
        assert "message" in data or "status" in data or "actions" in data


# ========================
# Custodial Wallet
# ========================

class TestCustodialWallet:
    def test_custodial_wallet_info(self, client):
        r = client.get(f"{API}/custodial-wallet/info/{WALLET}")
        assert r.status_code == 200
        data = r.json()
        assert "custodial_address" in data or "wallet_address" in data

    def test_custodial_wallet_balance(self, client):
        r = client.get(f"{API}/custodial-wallet/info/{WALLET}")
        data = r.json()
        if "balance_sol" in data:
            assert isinstance(data["balance_sol"], (int, float))
            assert data["balance_sol"] >= 0


# ========================
# PugBurn SOL Reclaim
# ========================

class TestPugBurn:
    def test_pugburn_scan(self, client):
        r = client.get(f"{API}/pugburn/scan/{WALLET}")
        assert r.status_code == 200
        data = r.json()
        assert "total_accounts" in data or "accounts" in data or "vacant_accounts" in data


# ========================
# Price Alerts
# ========================

class TestAlerts:
    def test_get_alerts(self, client):
        r = client.get(f"{API}/ai-trader/alerts/{WALLET}")
        assert r.status_code == 200
        data = r.json()
        assert "alerts" in data
        assert isinstance(data["alerts"], list)


# ========================
# Settings
# ========================

class TestSettings:
    def test_get_settings(self, client):
        r = client.get(f"{API}/ai-trader/settings/{WALLET}")
        assert r.status_code == 200

    def test_save_settings(self, client):
        r = client.post(f"{API}/ai-trader/settings", json={
            "wallet_address": WALLET,
            "risk_level": "safer",
            "max_position_sol": 0.5,
            "stop_loss_percent": 15,
            "take_profit_percent": 25,
            "max_daily_trades": 5
        })
        assert r.status_code == 200


# ========================
# Structural: Auto-burn integration
# ========================

class TestAutoBurnIntegration:
    def test_auto_burn_function_exists_in_ai_trader(self):
        """Verify ensure_sufficient_sol_for_trade is defined."""
        import ast
        filepath = os.path.join(os.path.dirname(__file__), "..", "routers", "ai_trader.py")
        with open(filepath) as f:
            tree = ast.parse(f.read())
        func_names = [
            node.name for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        assert "ensure_sufficient_sol_for_trade" in func_names

    def test_auto_burn_called_in_scan_execute(self):
        """Verify auto-burn is called inside auto_trade_scan_and_execute."""
        import ast
        filepath = os.path.join(os.path.dirname(__file__), "..", "routers", "ai_trader.py")
        with open(filepath) as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "auto_trade_scan_and_execute":
                calls = []
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name):
                            calls.append(child.func.id)
                        elif isinstance(child.func, ast.Attribute):
                            calls.append(child.func.attr)
                assert "ensure_sufficient_sol_for_trade" in calls, \
                    "ensure_sufficient_sol_for_trade not called in auto_trade_scan_and_execute"
                return
        pytest.fail("auto_trade_scan_and_execute function not found")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
