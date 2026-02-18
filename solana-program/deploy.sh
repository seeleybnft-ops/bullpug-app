#!/bin/bash
# Bullpug Smart Contract Deployment Script
# Run this on a machine with Solana CLI and Anchor CLI installed

set -e

echo "============================================"
echo "Bullpug P2P Betting Contract Deployment"
echo "============================================"

# Check prerequisites
if ! command -v solana &> /dev/null; then
    echo "Error: Solana CLI not found. Install with:"
    echo "  sh -c \"\$(curl -sSfL https://release.solana.com/stable/install)\""
    exit 1
fi

if ! command -v anchor &> /dev/null; then
    echo "Error: Anchor CLI not found. Install with:"
    echo "  cargo install --git https://github.com/coral-xyz/anchor anchor-cli"
    exit 1
fi

# Configuration
CLUSTER="${1:-devnet}"  # devnet or mainnet-beta
VANITY_PREFIX="PUG"
PROGRAM_DIR="$(dirname "$0")"

echo ""
echo "Target Cluster: $CLUSTER"
echo "Program Directory: $PROGRAM_DIR"
echo ""

# Step 1: Generate Vanity Address
echo "Step 1: Generating vanity address starting with '$VANITY_PREFIX'..."
echo "This may take a few minutes..."

cd "$PROGRAM_DIR"

# Use solana-keygen grind to find a vanity address
KEYPAIR_FILE="target/deploy/bullpug_betting-keypair.json"
mkdir -p target/deploy

if [ ! -f "$KEYPAIR_FILE" ]; then
    echo "Generating vanity keypair..."
    solana-keygen grind --starts-with "${VANITY_PREFIX}:1" --ignore-case > /tmp/vanity_output.txt 2>&1 &
    GRIND_PID=$!
    
    # Wait up to 5 minutes
    TIMEOUT=300
    ELAPSED=0
    while [ $ELAPSED -lt $TIMEOUT ]; do
        if grep -q "Wrote keypair" /tmp/vanity_output.txt 2>/dev/null; then
            GENERATED_FILE=$(grep "Wrote keypair" /tmp/vanity_output.txt | awk '{print $NF}')
            mv "$GENERATED_FILE" "$KEYPAIR_FILE"
            kill $GRIND_PID 2>/dev/null || true
            break
        fi
        sleep 5
        ELAPSED=$((ELAPSED + 5))
        echo "  Still searching... ($ELAPSED seconds)"
    done
    
    if [ ! -f "$KEYPAIR_FILE" ]; then
        kill $GRIND_PID 2>/dev/null || true
        echo "Vanity address generation timed out. Using random address..."
        solana-keygen new -o "$KEYPAIR_FILE" --no-bip39-passphrase
    fi
else
    echo "Using existing keypair: $KEYPAIR_FILE"
fi

PROGRAM_ID=$(solana-keygen pubkey "$KEYPAIR_FILE")
echo "Program ID: $PROGRAM_ID"
echo ""

# Step 2: Update Anchor.toml and lib.rs with actual program ID
echo "Step 2: Updating program ID in source files..."

# Update Anchor.toml
sed -i "s/bullpug_betting = \".*\"/bullpug_betting = \"$PROGRAM_ID\"/" Anchor.toml

# Update lib.rs declare_id!
sed -i "s/declare_id!(\".*\")/declare_id!(\"$PROGRAM_ID\")/" programs/bullpug-betting/src/lib.rs

echo "Updated Anchor.toml and lib.rs with program ID"
echo ""

# Step 3: Build the program
echo "Step 3: Building Anchor program..."
anchor build

echo ""
echo "Build successful!"
echo ""

# Step 4: Configure Solana CLI for target cluster
echo "Step 4: Configuring Solana CLI for $CLUSTER..."
solana config set --url https://api.$CLUSTER.solana.com
solana config set --keypair ~/.config/solana/id.json

# Check wallet balance
BALANCE=$(solana balance | awk '{print $1}')
echo "Deployer wallet balance: $BALANCE SOL"

if (( $(echo "$BALANCE < 2" | bc -l) )); then
    if [ "$CLUSTER" = "devnet" ]; then
        echo "Requesting airdrop..."
        solana airdrop 2
        sleep 5
    else
        echo "Warning: Low balance for mainnet deployment. Need ~2-5 SOL."
        echo "Fund your wallet and re-run this script."
        exit 1
    fi
fi

# Step 5: Deploy
echo ""
echo "Step 5: Deploying to $CLUSTER..."
anchor deploy --provider.cluster $CLUSTER

echo ""
echo "============================================"
echo "DEPLOYMENT SUCCESSFUL!"
echo "============================================"
echo ""
echo "Program ID: $PROGRAM_ID"
echo "Cluster: $CLUSTER"
echo ""
echo "Next steps:"
echo "1. Update frontend with program ID: $PROGRAM_ID"
echo "2. Update /app/frontend/src/config/solana.js"
echo "3. Test the contract using the TypeScript client"
echo ""
echo "View on explorer:"
echo "https://explorer.solana.com/address/$PROGRAM_ID?cluster=$CLUSTER"
echo ""
