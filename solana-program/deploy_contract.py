#!/usr/bin/env python3
"""
Bullpug Solana Smart Contract Deployment Script

This script deploys the Bullpug P2P Betting smart contract to Solana devnet/mainnet.
It can be run either in the Emergent environment or locally.

Requirements:
    pip install solana solders base58

Usage:
    # Deploy to devnet
    python deploy_contract.py --network devnet
    
    # Deploy to mainnet (requires funded wallet)
    python deploy_contract.py --network mainnet

The script will:
1. Check if the program is already deployed
2. If not, deploy the pre-built program binary
3. Verify the deployment
4. Output the program ID for frontend configuration
"""

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

try:
    from solana.rpc.api import Client
    from solana.rpc.commitment import Confirmed
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    import base58
except ImportError:
    print("Error: Required packages not installed.")
    print("Install with: pip install solana solders base58")
    sys.exit(1)

# Configuration
PROGRAM_ID = "H8GBfrx5drPZkAQXw1ueGtBrKD5QBwbh2DE4EcP2DCFm"
PROGRAM_KEYPAIR_PATH = Path(__file__).parent / "target" / "deploy" / "bullpug_betting-keypair.json"
PROGRAM_SO_PATH = Path(__file__).parent / "target" / "deploy" / "bullpug_betting.so"

NETWORKS = {
    "devnet": "https://api.devnet.solana.com",
    "mainnet": "https://api.mainnet-beta.solana.com",
    "testnet": "https://api.testnet.solana.com",
}


def load_keypair(path: Path) -> Keypair:
    """Load a keypair from a JSON file."""
    with open(path) as f:
        secret_key = json.load(f)
    return Keypair.from_bytes(bytes(secret_key))


def check_program_deployed(client: Client, program_id: str) -> bool:
    """Check if a program is already deployed."""
    try:
        pubkey = Pubkey.from_string(program_id)
        response = client.get_account_info(pubkey)
        if response.value:
            print(f"✓ Program {program_id} is already deployed")
            print(f"  Executable: {response.value.executable}")
            print(f"  Owner: {response.value.owner}")
            return True
        return False
    except Exception as e:
        print(f"✗ Error checking program: {e}")
        return False


def get_balance(client: Client, pubkey: Pubkey) -> float:
    """Get SOL balance for a public key."""
    response = client.get_balance(pubkey)
    return response.value / 1_000_000_000  # lamports to SOL


def deploy_program(client: Client, payer: Keypair, program_keypair: Keypair, program_path: Path):
    """
    Deploy a Solana program.
    
    Note: This is a simplified deployment. For production, use the Solana CLI
    which handles chunking large programs properly.
    """
    print(f"\n📦 Deploying program from {program_path}")
    
    # Check program binary exists
    if not program_path.exists():
        print(f"✗ Program binary not found at {program_path}")
        print("\nTo build the program:")
        print("  1. Install Anchor CLI: cargo install --git https://github.com/coral-xyz/anchor avm --locked")
        print("  2. Run: anchor build")
        return False
    
    program_size = program_path.stat().st_size
    print(f"  Program size: {program_size:,} bytes")
    
    # For large programs, we need to use BPF Loader
    # This requires the Solana CLI for proper chunked deployment
    print("\n⚠️  Large program deployment requires Solana CLI")
    print("   Please use the following commands:")
    print(f"\n   solana config set --url {client._provider.endpoint_uri}")
    print(f"   solana program deploy {program_path}")
    print(f"\n   Or use Anchor:")
    print(f"   anchor deploy --provider.cluster {client._provider.endpoint_uri}")
    
    return False


def main():
    parser = argparse.ArgumentParser(description="Deploy Bullpug Solana Smart Contract")
    parser.add_argument(
        "--network", 
        choices=["devnet", "mainnet", "testnet"], 
        default="devnet",
        help="Network to deploy to (default: devnet)"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check if program is deployed, don't deploy"
    )
    args = parser.parse_args()
    
    print("=" * 60)
    print("🐕 BULLPUG P2P BETTING - SOLANA DEPLOYMENT")
    print("=" * 60)
    
    # Connect to network
    rpc_url = NETWORKS[args.network]
    print(f"\n🌐 Connecting to {args.network}: {rpc_url}")
    client = Client(rpc_url)
    
    # Verify connection
    try:
        slot = client.get_slot().value
        print(f"✓ Connected! Current slot: {slot}")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        sys.exit(1)
    
    # Check if program is already deployed
    print(f"\n🔍 Checking program: {PROGRAM_ID}")
    is_deployed = check_program_deployed(client, PROGRAM_ID)
    
    if args.check_only:
        if is_deployed:
            print("\n✅ Program is deployed and ready!")
        else:
            print("\n❌ Program is NOT deployed")
        return
    
    if is_deployed:
        print("\n✅ Program already deployed! No action needed.")
        print("\n📝 Frontend Configuration:")
        print(f"   PROGRAM_ID = '{PROGRAM_ID}'")
        print(f"   NETWORK = '{args.network}'")
        return
    
    # Load keypairs
    print("\n🔑 Loading keypairs...")
    
    if not PROGRAM_KEYPAIR_PATH.exists():
        print(f"✗ Program keypair not found at {PROGRAM_KEYPAIR_PATH}")
        sys.exit(1)
    
    program_keypair = load_keypair(PROGRAM_KEYPAIR_PATH)
    print(f"✓ Program keypair loaded: {program_keypair.pubkey()}")
    
    # Check payer wallet
    payer_path = Path.home() / ".config" / "solana" / "id.json"
    if not payer_path.exists():
        print(f"\n⚠️  No payer wallet found at {payer_path}")
        print("   Create one with: solana-keygen new")
        print(f"   Then fund it with: solana airdrop 2 --url {args.network}")
        sys.exit(1)
    
    payer = load_keypair(payer_path)
    balance = get_balance(client, payer.pubkey())
    print(f"✓ Payer wallet: {payer.pubkey()}")
    print(f"  Balance: {balance:.4f} SOL")
    
    if balance < 0.5:
        print(f"\n⚠️  Low balance! Need at least 0.5 SOL to deploy")
        if args.network == "devnet":
            print(f"   Get devnet SOL: solana airdrop 2 --url devnet")
        sys.exit(1)
    
    # Deploy
    deploy_program(client, payer, program_keypair, PROGRAM_SO_PATH)
    
    print("\n" + "=" * 60)
    print("📋 DEPLOYMENT INSTRUCTIONS")
    print("=" * 60)
    print("""
To deploy the Bullpug smart contract:

1. Install Solana CLI (if not installed):
   sh -c "$(curl -sSfL https://release.solana.com/stable/install)"

2. Install Anchor CLI:
   cargo install --git https://github.com/coral-xyz/anchor avm --locked
   avm install latest
   avm use latest

3. Configure Solana for your network:
   solana config set --url devnet  # or mainnet-beta

4. Create/fund your wallet:
   solana-keygen new  # Creates ~/.config/solana/id.json
   solana airdrop 2   # For devnet only

5. Navigate to the solana-program directory and build:
   cd /app/solana-program
   anchor build

6. Deploy:
   anchor deploy --provider.cluster devnet

7. Verify deployment:
   python deploy_contract.py --network devnet --check-only

After deployment, update the frontend configuration at:
   /app/frontend/src/config/solana.js
""")


if __name__ == "__main__":
    main()
