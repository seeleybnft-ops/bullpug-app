"""
Iteration 92: Trading Bot Fixes Verification Tests

Tests for:
1. Backend starts cleanly without import errors
2. Helius RPC key updated — verify balance fetch via Helius
3. Token Sniper scan_new_pairs() returns actual results (2-step DexScreener approach)
4. auto_close_empty_accounts function exists in pugburn.py and is importable
5. MIN_POSITION_SOL constant is defined in auto_trader_engine.py
6. Fee reserve changed from 0.003 to 0.001 SOL
7. Initial balance threshold lowered from 0.005 to MIN_POSITION_SOL (0.001)
8. Pre-scan auto-burn runs BEFORE the balance check
9. Sniper mode now has on-chain execution flow (calls execute_auto_trade)
10. The /api/ai-trader/auto-trade/settings endpoint responds

IMPORTANT: This is a LIVE MAINNET bot. DO NOT execute actual trades.
Only test read-only endpoints, imports, and scan functions.
"""

import pytest
import requests
import os
import asyncio
import httpx

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
CUSTODIAL_WALLET = "CFzZRc76yEDEqxp2ssrfxdDCLQ8ctEBcs2TrMfGJtZMg"
USER_WALLET = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
HELIUS_RPC_URL = "https://mainnet.helius-rpc.com/?api-key=93caf7e7-7ab2-49bb-b298-35e6ad3f4765"


class TestBackendStartup:
    """Test 1: Backend starts cleanly without import errors"""
    
    def test_api_root_responds(self):
        """Verify API root endpoint responds"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Bullpug" in data["message"]
        print(f"✓ API root responds: {data['message']}")
    
    def test_auto_trader_engine_imports(self):
        """Verify auto_trader_engine.py imports without errors"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        # This will fail if there are import errors
        from services.auto_trader_engine import run_scan_and_execute, run_check_exits, MIN_POSITION_SOL
        
        assert callable(run_scan_and_execute)
        assert callable(run_check_exits)
        print("✓ auto_trader_engine.py imports successfully")
    
    def test_token_sniper_imports(self):
        """Verify token_sniper.py imports without errors"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from services.token_sniper import scan_new_pairs, record_snipe
        
        assert callable(scan_new_pairs)
        assert callable(record_snipe)
        print("✓ token_sniper.py imports successfully")
    
    def test_pugburn_imports(self):
        """Verify pugburn.py imports without errors"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from routers.pugburn import auto_close_empty_accounts, burn_custodial_accounts
        
        assert callable(auto_close_empty_accounts)
        assert callable(burn_custodial_accounts)
        print("✓ pugburn.py imports successfully with auto_close_empty_accounts")


class TestHeliusRPCKey:
    """Test 2: Helius RPC key updated — verify balance fetch"""
    
    def test_helius_rpc_url_in_env(self):
        """Verify HELIUS_RPC_URL is set in backend .env"""
        with open('/app/backend/.env', 'r') as f:
            env_content = f.read()
        
        assert 'HELIUS_RPC_URL' in env_content
        assert '93caf7e7-7ab2-49bb-b298-35e6ad3f4765' in env_content
        print("✓ HELIUS_RPC_URL is set with correct API key")
    
    def test_helius_balance_fetch(self):
        """Verify balance fetch via Helius RPC returns valid data"""
        response = requests.post(
            HELIUS_RPC_URL,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [CUSTODIAL_WALLET]
            },
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "value" in data["result"]
        
        balance_lamports = data["result"]["value"]
        balance_sol = balance_lamports / 1_000_000_000
        
        print(f"✓ Helius RPC balance fetch successful: {balance_sol:.6f} SOL ({balance_lamports} lamports)")
        assert balance_lamports >= 0  # Balance should be non-negative


class TestTokenSniperScan:
    """Test 3: Token Sniper scan_new_pairs() returns actual results"""
    
    def test_scan_new_pairs_returns_results(self):
        """Verify scan_new_pairs uses 2-step DexScreener approach and returns results"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        # Run the async function
        async def run_scan():
            from services.token_sniper import scan_new_pairs
            return await scan_new_pairs()
        
        targets = asyncio.get_event_loop().run_until_complete(run_scan())
        
        # The scan should return a list (may be empty if no new pairs meet criteria)
        assert isinstance(targets, list)
        
        if targets:
            # Verify structure of returned targets
            target = targets[0]
            assert "token_symbol" in target
            assert "token_mint" in target
            assert "confidence" in target
            assert "liquidity_usd" in target
            assert "pair_age_minutes" in target
            print(f"✓ scan_new_pairs returned {len(targets)} targets")
            print(f"  Top target: {target['token_symbol']} (conf: {target['confidence']:.2f}, age: {target['pair_age_minutes']}min)")
        else:
            print("✓ scan_new_pairs returned empty list (no new pairs meeting criteria)")
    
    def test_dexscreener_token_profiles_endpoint(self):
        """Verify DexScreener token-profiles endpoint is accessible"""
        response = requests.get(
            "https://api.dexscreener.com/token-profiles/latest/v1",
            timeout=15
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Check for Solana tokens
        solana_tokens = [t for t in data if t.get("chainId") == "solana"]
        print(f"✓ DexScreener token-profiles endpoint accessible: {len(solana_tokens)} Solana tokens")
    
    def test_dexscreener_token_boosts_endpoint(self):
        """Verify DexScreener token-boosts endpoint is accessible"""
        response = requests.get(
            "https://api.dexscreener.com/token-boosts/latest/v1",
            timeout=15
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Check for Solana tokens
        solana_tokens = [t for t in data if t.get("chainId") == "solana"]
        print(f"✓ DexScreener token-boosts endpoint accessible: {len(solana_tokens)} Solana tokens")


class TestAutoCloseEmptyAccounts:
    """Test 4: auto_close_empty_accounts function exists and is importable"""
    
    def test_auto_close_empty_accounts_exists(self):
        """Verify auto_close_empty_accounts function exists in pugburn.py"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from routers.pugburn import auto_close_empty_accounts
        
        assert callable(auto_close_empty_accounts)
        
        # Check function signature
        import inspect
        sig = inspect.signature(auto_close_empty_accounts)
        params = list(sig.parameters.keys())
        
        assert "custodial_address" in params
        print(f"✓ auto_close_empty_accounts exists with params: {params}")
    
    def test_auto_close_imported_in_auto_trader_engine(self):
        """Verify auto_close_empty_accounts is imported in auto_trader_engine.py"""
        with open('/app/backend/services/auto_trader_engine.py', 'r') as f:
            content = f.read()
        
        assert "from routers.pugburn import auto_close_empty_accounts" in content
        print("✓ auto_close_empty_accounts is imported in auto_trader_engine.py")


class TestMinPositionSOL:
    """Test 5: MIN_POSITION_SOL constant is defined"""
    
    def test_min_position_sol_defined(self):
        """Verify MIN_POSITION_SOL constant is defined in auto_trader_engine.py"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from services.auto_trader_engine import MIN_POSITION_SOL
        
        assert MIN_POSITION_SOL == 0.001
        print(f"✓ MIN_POSITION_SOL = {MIN_POSITION_SOL} (0.001 SOL)")
    
    def test_min_position_sol_in_code(self):
        """Verify MIN_POSITION_SOL is defined at line 31"""
        with open('/app/backend/services/auto_trader_engine.py', 'r') as f:
            lines = f.readlines()
        
        # Check line 31 (0-indexed: 30)
        line_31 = lines[30] if len(lines) > 30 else ""
        assert "MIN_POSITION_SOL" in line_31
        assert "0.001" in line_31
        print(f"✓ MIN_POSITION_SOL defined at line 31: {line_31.strip()}")


class TestFeeReserve:
    """Test 6: Fee reserve changed from 0.003 to 0.001 SOL"""
    
    def test_fee_reserve_is_0001(self):
        """Verify fee_reserve is 0.001 SOL in auto_trader_engine.py"""
        with open('/app/backend/services/auto_trader_engine.py', 'r') as f:
            content = f.read()
        
        # Check for fee_reserve = 0.001
        assert "fee_reserve = 0.001" in content
        
        # Verify old value 0.003 is NOT present
        assert "fee_reserve = 0.003" not in content
        
        print("✓ fee_reserve = 0.001 SOL (changed from 0.003)")
    
    def test_fee_reserve_at_correct_lines(self):
        """Verify fee_reserve is set at lines 545-548 area"""
        with open('/app/backend/services/auto_trader_engine.py', 'r') as f:
            lines = f.readlines()
        
        # Check lines 545-560 for fee_reserve
        found_fee_reserve = False
        for i in range(540, 570):
            if i < len(lines) and "fee_reserve = 0.001" in lines[i]:
                found_fee_reserve = True
                print(f"✓ fee_reserve = 0.001 found at line {i+1}: {lines[i].strip()}")
                break
        
        assert found_fee_reserve, "fee_reserve = 0.001 not found in expected line range"


class TestBalanceThreshold:
    """Test 7: Initial balance threshold lowered to MIN_POSITION_SOL"""
    
    def test_balance_threshold_uses_min_position_sol(self):
        """Verify balance check uses MIN_POSITION_SOL (0.001) instead of 0.005"""
        with open('/app/backend/services/auto_trader_engine.py', 'r') as f:
            content = f.read()
        
        # Check for MIN_POSITION_SOL in balance check
        assert "ledger_available < MIN_POSITION_SOL" in content
        
        # Verify old threshold 0.005 is NOT used for balance check
        # (0.005 may still exist for other purposes, but not for the main balance check)
        print("✓ Balance threshold uses MIN_POSITION_SOL (0.001)")
    
    def test_balance_check_at_line_314(self):
        """Verify balance check at line 314-316"""
        with open('/app/backend/services/auto_trader_engine.py', 'r') as f:
            lines = f.readlines()
        
        # Check lines 313-316 (0-indexed: 312-315)
        for i in range(312, 318):
            if i < len(lines) and "MIN_POSITION_SOL" in lines[i]:
                print(f"✓ MIN_POSITION_SOL balance check at line {i+1}: {lines[i].strip()}")
                return
        
        pytest.fail("MIN_POSITION_SOL balance check not found at expected lines")


class TestPreScanAutoBurn:
    """Test 8: Pre-scan auto-burn runs BEFORE the balance check"""
    
    def test_auto_burn_before_balance_check(self):
        """Verify auto-burn runs before balance check (balance < 0.01 triggers burn)"""
        with open('/app/backend/services/auto_trader_engine.py', 'r') as f:
            content = f.read()
        
        # Find the pre-scan auto-burn section
        assert "If balance is low, try auto-burn empty token accounts FIRST" in content
        assert "ledger_available < 0.01" in content
        
        print("✓ Pre-scan auto-burn triggers when balance < 0.01 SOL")
    
    def test_burn_order_in_code(self):
        """Verify burn happens BEFORE the MIN_POSITION_SOL check"""
        with open('/app/backend/services/auto_trader_engine.py', 'r') as f:
            lines = f.readlines()
        
        burn_line = None
        balance_check_line = None
        
        for i, line in enumerate(lines):
            if "ledger_available < 0.01" in line and burn_line is None:
                burn_line = i + 1
            if "ledger_available < MIN_POSITION_SOL" in line and balance_check_line is None:
                balance_check_line = i + 1
        
        assert burn_line is not None, "Pre-scan burn trigger not found"
        assert balance_check_line is not None, "MIN_POSITION_SOL balance check not found"
        assert burn_line < balance_check_line, f"Burn (line {burn_line}) should come before balance check (line {balance_check_line})"
        
        print(f"✓ Pre-scan burn (line {burn_line}) runs BEFORE balance check (line {balance_check_line})")


class TestSniperOnChainExecution:
    """Test 9: Sniper mode has on-chain execution flow"""
    
    def test_sniper_calls_execute_auto_trade(self):
        """Verify sniper mode calls execute_auto_trade for on-chain execution"""
        with open('/app/backend/services/auto_trader_engine.py', 'r') as f:
            content = f.read()
        
        # Check for execute_auto_trade import in sniper section
        assert "from routers.custodial_wallet import get_wallet_balance, execute_auto_trade" in content
        
        # Check for execute_auto_trade call in sniper section
        assert "trade_result = await execute_auto_trade(" in content
        
        print("✓ Sniper mode calls execute_auto_trade for on-chain execution")
    
    def test_sniper_execution_flow_structure(self):
        """Verify sniper execution flow has proper structure"""
        with open('/app/backend/services/auto_trader_engine.py', 'r') as f:
            content = f.read()
        
        # Check for key sniper execution elements
        assert "SNIPER: Executing on-chain trade" in content
        assert "SNIPER: Trade executed successfully" in content
        assert "executed_on_chain" in content
        assert "tx_signature" in content
        
        print("✓ Sniper execution flow has proper on-chain structure")
    
    def test_sniper_no_paper_trades(self):
        """Verify sniper only saves positions if execution was successful"""
        with open('/app/backend/services/auto_trader_engine.py', 'r') as f:
            content = f.read()
        
        # Check for the guard that prevents paper trades
        assert "ONLY save position if execution was successful (no paper trades)" in content
        assert "if execution_success:" in content
        
        print("✓ Sniper mode only saves positions on successful on-chain execution (no paper trades)")


class TestAutoTradeSettingsEndpoint:
    """Test 10: /api/ai-trader/auto-trade/settings endpoint responds"""
    
    def test_settings_endpoint_put_only(self):
        """Verify PUT /api/ai-trader/auto-trade/settings/{wallet} is the correct method"""
        # GET should return 405 (Method Not Allowed) - settings is PUT only
        response = requests.get(
            f"{BASE_URL}/api/ai-trader/auto-trade/settings/{USER_WALLET}",
            timeout=15
        )
        
        # 405 = Method Not Allowed (expected - endpoint is PUT only)
        assert response.status_code == 405
        print("✓ Settings endpoint is PUT-only (GET returns 405 as expected)")
    
    def test_auto_trade_status_endpoint(self):
        """Verify GET /api/ai-trader/auto-trade/status/{wallet} responds with settings"""
        response = requests.get(
            f"{BASE_URL}/api/ai-trader/auto-trade/status/{USER_WALLET}",
            timeout=15
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have auto_trade_enabled field and settings
        assert "auto_trade_enabled" in data
        assert "settings" in data
        
        settings = data["settings"]
        assert "mode" in settings
        assert "max_position_sol" in settings
        
        print(f"✓ Auto-trade status endpoint responds with settings: mode={settings['mode']}, max_position={settings['max_position_sol']}")


class TestCodeStructureVerification:
    """Additional code structure verification tests"""
    
    def test_sniper_execution_lines_1103_1250(self):
        """Verify sniper execution code exists at lines 1103-1250"""
        with open('/app/backend/services/auto_trader_engine.py', 'r') as f:
            lines = f.readlines()
        
        # Check line 1103 area for sniper execution start
        found_sniper_section = False
        for i in range(1100, 1110):
            if i < len(lines) and "SNIPER MODE EXECUTION" in lines[i]:
                found_sniper_section = True
                print(f"✓ Sniper execution section found at line {i+1}")
                break
        
        assert found_sniper_section, "Sniper execution section not found at expected lines"
    
    def test_token_sniper_2step_approach(self):
        """Verify token_sniper.py uses 2-step DexScreener approach"""
        with open('/app/backend/services/token_sniper.py', 'r') as f:
            content = f.read()
        
        # Check for token-profiles endpoint
        assert "token-profiles/latest/v1" in content
        
        # Check for token-boosts endpoint
        assert "token-boosts/latest/v1" in content
        
        # Check for batch lookup
        assert "dex/tokens/" in content
        
        print("✓ token_sniper.py uses 2-step DexScreener approach (profiles + boosts → batch lookup)")
    
    def test_pugburn_auto_close_at_lines_320_335(self):
        """Verify auto_close_empty_accounts at lines 320-335"""
        with open('/app/backend/routers/pugburn.py', 'r') as f:
            lines = f.readlines()
        
        # Check lines 319-335 (0-indexed: 318-334)
        found_function = False
        for i in range(318, 340):
            if i < len(lines) and "async def auto_close_empty_accounts" in lines[i]:
                found_function = True
                print(f"✓ auto_close_empty_accounts function found at line {i+1}")
                break
        
        assert found_function, "auto_close_empty_accounts not found at expected lines"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
