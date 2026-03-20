#!/usr/bin/env python3
"""
Test Setup Script for Auto-Trade Bot
Creates test wallet settings and simulates the auto-trade flow.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient

# Test wallet address (simulated)
TEST_WALLET = "TestWallet_AutoTrade_123456789"

async def setup_test_environment():
    """Set up test auto-trade settings in the database."""
    
    # Connect to MongoDB
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME", "bullpug")
    
    if not mongo_url:
        print("ERROR: MONGO_URL not set in environment")
        return False
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print(f"Connected to MongoDB: {db_name}")
    print(f"Test wallet: {TEST_WALLET}")
    print("=" * 60)
    
    # Create/Update auto-trade settings
    settings = {
        "wallet_address": TEST_WALLET,
        "enabled": True,
        "risk_level": "both",  # Enable both safer and high-risk (including runners)
        "max_position_sol": 0.1,
        "min_position_sol": 0.05,
        "stop_loss_percent": 15.0,
        "take_profit_percent": 50.0,
        "max_daily_trades": 5,
        "auto_approve": False,
        # Auto-trade specific settings
        "auto_trade_enabled": True,
        "auto_trade_mode": "moderate",  # moderate = 0.55-0.60 confidence
        "auto_min_confidence": 0.55,  # Optimal based on backtest
        "auto_max_daily_trades": 5,
        "auto_max_position_sol": 0.05,  # Small position for testing
        "auto_cooldown_minutes": 5,  # Short cooldown for testing
        "auto_require_multiple_signals": False,  # Use combined strategy
        "auto_pause_on_loss": False,  # Don't pause for testing
        "auto_total_daily_limit_sol": 0.5,
        "auto_stop_loss_percent": 20.0,  # 20% for runners
        "auto_take_profit_percent": 100.0,  # 100% for runners
        "auto_trailing_stop_enabled": False,
        "auto_scale_in_enabled": False,
        "auto_avoid_volatile_hours": False,  # Trade anytime for testing
        "auto_profit_target_alert": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Upsert settings
    result = await db.ai_trader_settings.update_one(
        {"wallet_address": TEST_WALLET},
        {"$set": settings},
        upsert=True
    )
    
    print(f"Settings created/updated: {result.modified_count or result.upserted_id}")
    print(f"  - Mode: {settings['auto_trade_mode']}")
    print(f"  - Min Confidence: {settings['auto_min_confidence']}")
    print(f"  - Risk Level: {settings['risk_level']}")
    print(f"  - Max Position: {settings['auto_max_position_sol']} SOL")
    print("=" * 60)
    
    # Create a simulated custodial wallet (for balance check)
    custodial = {
        "user_wallet": TEST_WALLET,
        "custodial_address": "SimulatedCustodialWallet_123",
        "balance_sol": 0.05,  # Test balance
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.custodial_wallets.update_one(
        {"user_wallet": TEST_WALLET},
        {"$set": custodial},
        upsert=True
    )
    
    print(f"Custodial wallet created with 0.05 SOL balance")
    print("=" * 60)
    
    return True


async def run_test_scan():
    """Run a test auto-trade scan."""
    import httpx
    
    api_url = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001")
    
    print("\n" + "=" * 60)
    print("RUNNING AUTO-TRADE SCAN")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # First, check runners endpoint
        print("\n1. Fetching runner tokens...")
        try:
            runners_resp = await client.get(f"{api_url}/api/ai-trader/runners")
            if runners_resp.status_code == 200:
                runners_data = runners_resp.json()
                print(f"   Found {runners_data.get('count', 0)} potential runners:")
                for r in runners_data.get('runners', [])[:5]:
                    print(f"     - {r['symbol']}: ${r['price_usd']:.8f} | +{r['price_change_1h']:.1f}% 1h | Score: {r['runner_score']}")
            else:
                print(f"   Failed to fetch runners: {runners_resp.status_code}")
        except Exception as e:
            print(f"   Runner fetch error: {e}")
        
        # Test signal generation
        print("\n2. Testing signal generation for SOL...")
        try:
            signal_resp = await client.post(
                f"{api_url}/api/ai-trader/analyze/SOL",
                params={"wallet_address": TEST_WALLET}
            )
            if signal_resp.status_code == 200:
                signal_data = signal_resp.json()
                if signal_data.get("signal"):
                    sig = signal_data["signal"]
                    print(f"   Signal: {sig['signal_type'].upper()} @ {sig['confidence']*100:.0f}% confidence")
                    print(f"   Price: ${sig['entry_price']:.2f}")
                    print(f"   Strategy: {sig['strategy']}")
                    print(f"   Reasoning: {sig['reasoning'][:100]}...")
                else:
                    print(f"   No signal: {signal_data.get('message', 'Unknown')}")
            else:
                print(f"   Signal error: {signal_resp.status_code}")
        except Exception as e:
            print(f"   Signal error: {e}")
        
        # Run auto-trade scan
        print(f"\n3. Running auto-trade scan for {TEST_WALLET}...")
        try:
            scan_resp = await client.post(
                f"{api_url}/api/ai-trader/auto-trade/scan-and-execute/{TEST_WALLET}"
            )
            if scan_resp.status_code == 200:
                scan_data = scan_resp.json()
                print(f"   Success: {scan_data.get('success')}")
                print(f"   Message: {scan_data.get('message')}")
                print(f"   Runners found: {scan_data.get('runners_found', 0)}")
                
                if scan_data.get('trades'):
                    print(f"\n   TRADES EXECUTED:")
                    for t in scan_data['trades']:
                        runner_tag = " [RUNNER]" if t.get('is_runner') else ""
                        print(f"     - {t['symbol']}{runner_tag}: {t['action']} {t['amount_sol']} SOL @ ${t['entry_price']:.8f} ({t['confidence']*100:.0f}% conf)")
                
                if scan_data.get('skipped'):
                    print(f"\n   SKIPPED ({len(scan_data['skipped'])} tokens):")
                    for s in scan_data['skipped'][:5]:
                        runner_score = f" (score={s.get('runner_score')})" if s.get('runner_score') else ""
                        print(f"     - {s['symbol']}: {s['reason']}{runner_score}")
            else:
                print(f"   Scan failed: {scan_resp.status_code} - {scan_resp.text[:200]}")
        except Exception as e:
            print(f"   Scan error: {e}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


async def check_positions():
    """Check any positions created during the test."""
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME", "bullpug")
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    positions = await db.ai_trader_positions.find(
        {"wallet_address": TEST_WALLET}
    ).to_list(20)
    
    print("\n" + "=" * 60)
    print("OPEN POSITIONS")
    print("=" * 60)
    
    if positions:
        for p in positions:
            runner_tag = " [RUNNER]" if p.get("is_runner") else ""
            print(f"  {p['token_symbol']}{runner_tag}:")
            print(f"    Entry: ${p['entry_price']:.8f}")
            print(f"    Amount: {p['amount_sol']} SOL")
            print(f"    Stop Loss: ${p['stop_loss_price']:.8f}")
            print(f"    Take Profit: ${p['take_profit_price']:.8f}")
            print(f"    Confidence: {p.get('confidence', 0)*100:.0f}%")
            if p.get('runner_score'):
                print(f"    Runner Score: {p['runner_score']}")
    else:
        print("  No open positions")
    
    # Check trade logs
    logs = await db.auto_trade_logs.find(
        {"wallet_address": TEST_WALLET}
    ).sort("created_at", -1).to_list(10)
    
    print("\n" + "=" * 60)
    print("RECENT TRADE LOGS")
    print("=" * 60)
    
    if logs:
        for log in logs[:5]:
            print(f"  {log.get('created_at', '?')[:19]}: {log.get('action')} {log.get('token_symbol')} - {log.get('reason', '')[:50]}")
    else:
        print("  No trade logs")


async def cleanup_test():
    """Remove test data from database."""
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME", "bullpug")
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print("\n" + "=" * 60)
    print("CLEANING UP TEST DATA")
    print("=" * 60)
    
    # Remove test settings
    result1 = await db.ai_trader_settings.delete_many({"wallet_address": TEST_WALLET})
    print(f"  Settings removed: {result1.deleted_count}")
    
    # Remove test positions
    result2 = await db.ai_trader_positions.delete_many({"wallet_address": TEST_WALLET})
    print(f"  Positions removed: {result2.deleted_count}")
    
    # Remove test logs
    result3 = await db.auto_trade_logs.delete_many({"wallet_address": TEST_WALLET})
    print(f"  Logs removed: {result3.deleted_count}")
    
    # Remove test custodial wallet
    result4 = await db.custodial_wallets.delete_many({"user_wallet": TEST_WALLET})
    print(f"  Custodial wallets removed: {result4.deleted_count}")
    
    print("Cleanup complete!")


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto-Trade Bot Test Setup")
    parser.add_argument("--setup", action="store_true", help="Create test settings")
    parser.add_argument("--scan", action="store_true", help="Run test scan")
    parser.add_argument("--positions", action="store_true", help="Check positions")
    parser.add_argument("--cleanup", action="store_true", help="Remove test data")
    parser.add_argument("--all", action="store_true", help="Run full test (setup + scan + check)")
    
    args = parser.parse_args()
    
    if args.all or (not any([args.setup, args.scan, args.positions, args.cleanup])):
        # Default: run full test
        await setup_test_environment()
        await run_test_scan()
        await check_positions()
    else:
        if args.setup:
            await setup_test_environment()
        if args.scan:
            await run_test_scan()
        if args.positions:
            await check_positions()
        if args.cleanup:
            await cleanup_test()


if __name__ == "__main__":
    asyncio.run(main())
