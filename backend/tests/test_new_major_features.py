"""
Test suite for Bullpug Major Feature Update:
1. Admin Panel APIs (admin check, dashboard, challenges, cancel)
2. Escrow System (deposit, wallet endpoint)
3. Direct Messaging (send, conversations, get messages)
4. Notifications (get, mark as read)
5. Trading Journal Cloud Backup (create, list, restore, delete)
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Admin wallet addresses for testing
ADMIN_WALLET_1 = "we2wLezPyv4Z9AmN5vJyWsE1ZNVBqvhTxaoZh9MhuoT"
ADMIN_WALLET_2 = "qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs"
NON_ADMIN_WALLET = "TEST_NonAdminWallet123456789012345678901234567"

# Test wallets for messaging
TEST_WALLET_1 = "TEST_Wallet1_" + str(uuid.uuid4())[:20]
TEST_WALLET_2 = "TEST_Wallet2_" + str(uuid.uuid4())[:20]

@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestAdminCheckAPI:
    """Test Admin Check endpoint"""
    
    def test_admin_check_returns_true_for_admin_wallet_1(self, api_client):
        """Admin wallet 1 should be recognized as admin"""
        response = api_client.get(f"{BASE_URL}/api/admin/check/{ADMIN_WALLET_1}")
        assert response.status_code == 200
        data = response.json()
        assert "is_admin" in data
        assert data["is_admin"] == True
        print(f"PASS: Admin wallet 1 recognized as admin")
    
    def test_admin_check_returns_true_for_admin_wallet_2(self, api_client):
        """Admin wallet 2 should be recognized as admin"""
        response = api_client.get(f"{BASE_URL}/api/admin/check/{ADMIN_WALLET_2}")
        assert response.status_code == 200
        data = response.json()
        assert "is_admin" in data
        assert data["is_admin"] == True
        print(f"PASS: Admin wallet 2 recognized as admin")
    
    def test_admin_check_returns_false_for_non_admin(self, api_client):
        """Non-admin wallet should return is_admin=false"""
        response = api_client.get(f"{BASE_URL}/api/admin/check/{NON_ADMIN_WALLET}")
        assert response.status_code == 200
        data = response.json()
        assert "is_admin" in data
        assert data["is_admin"] == False
        print(f"PASS: Non-admin wallet correctly rejected")


class TestAdminDashboardAPI:
    """Test Admin Dashboard endpoint"""
    
    def test_admin_dashboard_returns_stats(self, api_client):
        """Admin dashboard should return statistics"""
        response = api_client.get(f"{BASE_URL}/api/admin/dashboard?admin_wallet={ADMIN_WALLET_1}")
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "total_bets" in data
        assert "total_challenges" in data
        assert "open_challenges" in data
        assert "completed_challenges" in data
        assert "current_pot" in data
        assert "distribution_wallet" in data
        
        # Validate distribution wallet
        assert data["distribution_wallet"] == ADMIN_WALLET_1
        print(f"PASS: Admin dashboard returns all stats - total_bets: {data['total_bets']}, challenges: {data['total_challenges']}")
    
    def test_admin_dashboard_includes_current_pot(self, api_client):
        """Admin dashboard should include current pot info"""
        response = api_client.get(f"{BASE_URL}/api/admin/dashboard?admin_wallet={ADMIN_WALLET_1}")
        assert response.status_code == 200
        data = response.json()
        
        pot = data["current_pot"]
        assert "total_amount_sol" in pot
        assert "entry_count" in pot
        assert "status" in pot
        print(f"PASS: Current pot info included - amount: {pot['total_amount_sol']} SOL, entries: {pot['entry_count']}")
    
    def test_admin_dashboard_rejects_non_admin(self, api_client):
        """Non-admin should be rejected from dashboard"""
        response = api_client.get(f"{BASE_URL}/api/admin/dashboard?admin_wallet={NON_ADMIN_WALLET}")
        assert response.status_code == 403
        print(f"PASS: Non-admin correctly rejected from dashboard (403)")


class TestAdminChallengesAPI:
    """Test Admin Challenges management"""
    
    def test_admin_get_challenges_list(self, api_client):
        """Admin can get list of challenges"""
        response = api_client.get(f"{BASE_URL}/api/admin/challenges?admin_wallet={ADMIN_WALLET_1}&limit=20")
        assert response.status_code == 200
        data = response.json()
        assert "challenges" in data
        assert isinstance(data["challenges"], list)
        print(f"PASS: Admin can list challenges - count: {len(data['challenges'])}")
    
    def test_admin_get_challenges_with_status_filter(self, api_client):
        """Admin can filter challenges by status"""
        response = api_client.get(f"{BASE_URL}/api/admin/challenges?admin_wallet={ADMIN_WALLET_1}&status=open")
        assert response.status_code == 200
        data = response.json()
        assert "challenges" in data
        # All returned challenges should have status=open
        for challenge in data["challenges"]:
            assert challenge.get("status") == "open"
        print(f"PASS: Admin can filter challenges by status - open count: {len(data['challenges'])}")
    
    def test_admin_challenges_rejects_non_admin(self, api_client):
        """Non-admin should be rejected from challenges list"""
        response = api_client.get(f"{BASE_URL}/api/admin/challenges?admin_wallet={NON_ADMIN_WALLET}")
        assert response.status_code == 403
        print(f"PASS: Non-admin correctly rejected from challenges list (403)")


class TestAdminCancelChallenge:
    """Test Admin Cancel Challenge endpoint"""
    
    def test_admin_cancel_challenge_creates_then_cancels(self, api_client):
        """Admin can cancel an open challenge"""
        # First create a challenge to cancel
        challenge_data = {
            "bet_amount_sol": 0.05,
            "choice": "heads",
            "wallet_address": "TEST_Creator_" + str(uuid.uuid4())[:20],
            "display_name": "TEST_Cancel"
        }
        create_resp = api_client.post(f"{BASE_URL}/api/betting/challenge/create", json=challenge_data)
        assert create_resp.status_code == 200
        challenge_id = create_resp.json()["challenge_id"]
        
        # Now cancel it as admin
        cancel_data = {
            "admin_wallet": ADMIN_WALLET_1,
            "challenge_id": challenge_id,
            "action": "cancel"
        }
        cancel_resp = api_client.post(f"{BASE_URL}/api/admin/challenge/cancel", json=cancel_data)
        assert cancel_resp.status_code == 200
        assert "message" in cancel_resp.json()
        print(f"PASS: Admin cancelled challenge {challenge_id}")
    
    def test_admin_cancel_non_admin_rejected(self, api_client):
        """Non-admin should be rejected from cancelling"""
        cancel_data = {
            "admin_wallet": NON_ADMIN_WALLET,
            "challenge_id": "fake-id",
            "action": "cancel"
        }
        response = api_client.post(f"{BASE_URL}/api/admin/challenge/cancel", json=cancel_data)
        assert response.status_code == 403
        print(f"PASS: Non-admin correctly rejected from cancelling (403)")


class TestEscrowWalletAPI:
    """Test Escrow Wallet endpoint"""
    
    def test_escrow_wallet_returns_correct_address(self, api_client):
        """Escrow wallet endpoint returns the correct address"""
        response = api_client.get(f"{BASE_URL}/api/escrow/wallet")
        assert response.status_code == 200
        data = response.json()
        
        assert "escrow_wallet" in data
        assert data["escrow_wallet"] == ADMIN_WALLET_1  # Distribution wallet is used as escrow
        assert "message" in data
        print(f"PASS: Escrow wallet endpoint returns correct address: {data['escrow_wallet']}")


class TestEscrowDepositAPI:
    """Test Escrow Deposit recording"""
    
    def test_escrow_deposit_records_transaction(self, api_client):
        """Escrow deposit recording works"""
        deposit_data = {
            "wallet_address": "TEST_Deposit_" + str(uuid.uuid4())[:20],
            "amount_sol": 0.1,
            "tx_signature": "TEST_TX_" + str(uuid.uuid4())[:40],
            "purpose": "challenge",
            "reference_id": str(uuid.uuid4())
        }
        
        response = api_client.post(f"{BASE_URL}/api/escrow/deposit", json=deposit_data)
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "deposit_id" in data
        print(f"PASS: Escrow deposit recorded - deposit_id: {data['deposit_id']}")


class TestMessagesAPI:
    """Test Direct Messaging endpoints"""
    
    def test_send_message_works(self, api_client):
        """Can send a direct message"""
        message_data = {
            "to_wallet": TEST_WALLET_2,
            "content": "TEST_Hello from test!",
            "from_wallet": TEST_WALLET_1,
            "from_name": "TEST_User1"
        }
        
        response = api_client.post(f"{BASE_URL}/api/messages/send", json=message_data)
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "message_id" in data
        print(f"PASS: Message sent - message_id: {data['message_id']}")
    
    def test_send_message_empty_content_rejected(self, api_client):
        """Empty message content should be rejected"""
        message_data = {
            "to_wallet": TEST_WALLET_2,
            "content": "   ",
            "from_wallet": TEST_WALLET_1,
            "from_name": "TEST_User1"
        }
        
        response = api_client.post(f"{BASE_URL}/api/messages/send", json=message_data)
        assert response.status_code == 400
        print(f"PASS: Empty message correctly rejected (400)")
    
    def test_send_message_to_self_rejected(self, api_client):
        """Sending message to yourself should be rejected"""
        message_data = {
            "to_wallet": TEST_WALLET_1,
            "content": "TEST_Hello myself",
            "from_wallet": TEST_WALLET_1,
            "from_name": "TEST_User1"
        }
        
        response = api_client.post(f"{BASE_URL}/api/messages/send", json=message_data)
        assert response.status_code == 400
        print(f"PASS: Self-message correctly rejected (400)")
    
    def test_get_conversations_works(self, api_client):
        """Can get conversations list"""
        # First send a message to create a conversation
        message_data = {
            "to_wallet": "TEST_ConvPartner_" + str(uuid.uuid4())[:15],
            "content": "TEST_Conversation starter",
            "from_wallet": TEST_WALLET_1,
            "from_name": "TEST_User1"
        }
        api_client.post(f"{BASE_URL}/api/messages/send", json=message_data)
        
        # Get conversations
        response = api_client.get(f"{BASE_URL}/api/messages/conversations/{TEST_WALLET_1}")
        assert response.status_code == 200
        data = response.json()
        
        assert "conversations" in data
        assert isinstance(data["conversations"], list)
        print(f"PASS: Conversations retrieved - count: {len(data['conversations'])}")
    
    def test_get_conversation_messages_works(self, api_client):
        """Can get messages between two wallets"""
        unique_partner = "TEST_MsgPartner_" + str(uuid.uuid4())[:15]
        
        # Send a message
        message_data = {
            "to_wallet": unique_partner,
            "content": "TEST_Get messages test",
            "from_wallet": TEST_WALLET_1,
            "from_name": "TEST_User1"
        }
        api_client.post(f"{BASE_URL}/api/messages/send", json=message_data)
        
        # Get messages
        response = api_client.get(f"{BASE_URL}/api/messages/conversation/{TEST_WALLET_1}/{unique_partner}")
        assert response.status_code == 200
        data = response.json()
        
        assert "messages" in data
        assert isinstance(data["messages"], list)
        print(f"PASS: Conversation messages retrieved - count: {len(data['messages'])}")


class TestNotificationsAPI:
    """Test Notifications endpoints"""
    
    def test_get_notifications_works(self, api_client):
        """Can get notifications for a wallet"""
        response = api_client.get(f"{BASE_URL}/api/notifications/{TEST_WALLET_1}")
        assert response.status_code == 200
        data = response.json()
        
        assert "notifications" in data
        assert "unread_count" in data
        assert isinstance(data["notifications"], list)
        print(f"PASS: Notifications retrieved - count: {len(data['notifications'])}, unread: {data['unread_count']}")
    
    def test_mark_all_notifications_read(self, api_client):
        """Can mark all notifications as read"""
        response = api_client.post(f"{BASE_URL}/api/notifications/read-all/{TEST_WALLET_1}")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"PASS: All notifications marked as read")


class TestTradingJournalBackupAPI:
    """Test Trading Journal Cloud Backup endpoints"""
    
    def test_create_backup_works(self, api_client):
        """Can create a trading journal backup"""
        backup_data = {
            "wallet_address": TEST_WALLET_1
        }
        
        response = api_client.post(f"{BASE_URL}/api/journal/backup", json=backup_data)
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "backup_id" in data
        assert "trade_count" in data
        print(f"PASS: Backup created - backup_id: {data['backup_id']}, trades: {data['trade_count']}")
        return data["backup_id"]
    
    def test_list_backups_works(self, api_client):
        """Can list backups for a wallet"""
        # Create a backup first
        backup_data = {"wallet_address": TEST_WALLET_1}
        api_client.post(f"{BASE_URL}/api/journal/backup", json=backup_data)
        
        # List backups
        response = api_client.get(f"{BASE_URL}/api/journal/backups/{TEST_WALLET_1}")
        assert response.status_code == 200
        data = response.json()
        
        assert "backups" in data
        assert isinstance(data["backups"], list)
        print(f"PASS: Backups listed - count: {len(data['backups'])}")
    
    def test_restore_backup_works(self, api_client):
        """Can restore trades from a backup"""
        # Create a backup first
        backup_data = {"wallet_address": TEST_WALLET_1}
        create_resp = api_client.post(f"{BASE_URL}/api/journal/backup", json=backup_data)
        backup_id = create_resp.json()["backup_id"]
        
        # Restore from backup
        response = api_client.post(
            f"{BASE_URL}/api/journal/restore/{backup_id}?wallet_address={TEST_WALLET_1}"
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "restored_count" in data
        print(f"PASS: Backup restored - restored_count: {data['restored_count']}")
    
    def test_delete_backup_works(self, api_client):
        """Can delete a backup"""
        # Create a backup first
        backup_data = {"wallet_address": TEST_WALLET_1}
        create_resp = api_client.post(f"{BASE_URL}/api/journal/backup", json=backup_data)
        backup_id = create_resp.json()["backup_id"]
        
        # Delete backup
        response = api_client.delete(
            f"{BASE_URL}/api/journal/backup/{backup_id}?wallet_address={TEST_WALLET_1}"
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        print(f"PASS: Backup deleted - backup_id: {backup_id}")


class TestAdminBetsAPI:
    """Test Admin Bets endpoint"""
    
    def test_admin_get_bets_list(self, api_client):
        """Admin can get list of bets"""
        response = api_client.get(f"{BASE_URL}/api/admin/bets?admin_wallet={ADMIN_WALLET_1}")
        assert response.status_code == 200
        data = response.json()
        assert "bets" in data
        assert isinstance(data["bets"], list)
        print(f"PASS: Admin can list bets - count: {len(data['bets'])}")


class TestAdminEscrowAPI:
    """Test Admin Escrow Statistics endpoint"""
    
    def test_admin_get_escrow_stats(self, api_client):
        """Admin can get escrow statistics"""
        response = api_client.get(f"{BASE_URL}/api/admin/escrow?admin_wallet={ADMIN_WALLET_1}")
        assert response.status_code == 200
        data = response.json()
        
        assert "total_deposited_sol" in data
        assert "total_withdrawn_sol" in data
        assert "escrow_balance_sol" in data
        assert "recent_deposits" in data
        print(f"PASS: Admin can view escrow stats - balance: {data['escrow_balance_sol']} SOL")


class TestExistingFeaturesStillWork:
    """Ensure existing features (P2P Arena, Forum) still work"""
    
    def test_p2p_arena_betting_config(self, api_client):
        """P2P Arena betting config still works"""
        response = api_client.get(f"{BASE_URL}/api/betting/config")
        assert response.status_code == 200
        data = response.json()
        assert data["rake_percent"] == 2.5
        assert data["distribution_wallet"] == ADMIN_WALLET_1
        print(f"PASS: P2P Arena betting config works - rake: {data['rake_percent']}%")
    
    def test_p2p_arena_pot_status(self, api_client):
        """P2P Arena pot status still works"""
        response = api_client.get(f"{BASE_URL}/api/betting/pot")
        assert response.status_code == 200
        data = response.json()
        assert "total_amount_sol" in data
        assert "status" in data
        print(f"PASS: P2P Arena pot status works - pot: {data['total_amount_sol']} SOL")
    
    def test_forum_categories(self, api_client):
        """Forum categories still work"""
        response = api_client.get(f"{BASE_URL}/api/forum/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) == 6
        print(f"PASS: Forum categories work - count: {len(data['categories'])}")
    
    def test_forum_posts(self, api_client):
        """Forum posts still work"""
        response = api_client.get(f"{BASE_URL}/api/forum/posts")
        assert response.status_code == 200
        data = response.json()
        assert "posts" in data
        print(f"PASS: Forum posts work - count: {len(data['posts'])}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
