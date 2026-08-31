"""Iteration 110 regression tests for Archive fixes (lore expansion 61 entries, classifier,
   daily-drop idempotency, and chatbot banned openers)."""
import os
import time
import random
import string
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cosmic-runner-hub.preview.emergentagent.com").rstrip("/")

BANNED_OPENERS = [
    "Right —", "Ah —", "Ah,", "Greetings", "Certainly", "Of course",
    "Great question", "Allow me", "Indeed", "Ah, a request",
]


def _rand(n=8):
    return "".join(random.choices(string.ascii_letters + string.digits, k=n))


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "X-Bullpug-CSRF": "1"})
    return s


# --- Fix 6: Lore expansion 27 -> 61 entries ---

class TestArchiveEntries:
    def test_entries_total_and_tier_distribution(self, session):
        r = session.get(f"{BASE_URL}/api/archive/entries", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        entries = data.get("entries", data if isinstance(data, list) else [])
        assert len(entries) == 61, f"Expected 61, got {len(entries)}"
        tiers = {}
        slugs = []
        for e in entries:
            assert "slug" in e and "tier" in e and "name" in e and "locked_desc" in e, f"Missing fields in {e}"
            tiers[e["tier"]] = tiers.get(e["tier"], 0) + 1
            slugs.append(e["slug"])
        assert tiers == {1: 16, 2: 25, 3: 20}, f"Tier distribution wrong: {tiers}"
        assert len(slugs) == len(set(slugs)), "Duplicate slugs found"

    def test_rank_totals(self, session):
        r = session.get(f"{BASE_URL}/api/archive/rank", params={"wallet": "testWallet123"}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("total") == 61, f"total={data.get('total')}"
        tp = data.get("tier_progress", {})
        # Support both shapes: {tier_1: {total:16}} or {tier_1: 16}
        def total_of(v):
            return v["total"] if isinstance(v, dict) else v
        assert total_of(tp.get("tier_1")) == 16, tp
        assert total_of(tp.get("tier_2")) == 25, tp
        assert total_of(tp.get("tier_3")) == 20, tp

    def test_entries_with_unknown_wallet_all_locked(self, session):
        w = "TestNewWallet123XXX_" + _rand()
        r = session.get(f"{BASE_URL}/api/archive/entries", params={"wallet": w}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        entries = data.get("entries", data if isinstance(data, list) else [])
        assert len(entries) == 61
        unlocked_count = sum(1 for e in entries if e.get("unlocked"))
        assert unlocked_count == 0, f"Expected 0 unlocked, got {unlocked_count}"


# --- Fix 1: Daily drop idempotency per (wallet, UTC-day) ---

class TestDailyDrop:
    def test_daily_drop_idempotent(self, session):
        wallet = f"DropTestWallet_{int(time.time())}_{_rand(4)}"
        # First call: may return drop or 503 while generating. Retry up to N times.
        drop1 = None
        for attempt in range(12):
            r = session.get(f"{BASE_URL}/api/ai/daily-drop", params={"wallet_address": wallet}, timeout=90)
            if r.status_code == 200:
                j = r.json()
                if j.get("image_base64") or (j.get("drop") and j["drop"].get("image_base64")):
                    drop1 = j
                    break
            elif r.status_code == 503:
                time.sleep(10)
                continue
            else:
                pytest.fail(f"Unexpected status {r.status_code}: {r.text[:400]}")
            time.sleep(5)
        assert drop1 is not None, "Daily drop never generated after retries"

        img1 = drop1.get("image_base64") or drop1.get("drop", {}).get("image_base64")
        assert img1, f"No image_base64 in response: {list(drop1.keys())}"

        # Second call should be cached (idempotent within UTC day)
        r2 = session.get(f"{BASE_URL}/api/ai/daily-drop", params={"wallet_address": wallet}, timeout=30)
        assert r2.status_code == 200, r2.text
        j2 = r2.json()
        img2 = j2.get("image_base64") or j2.get("drop", {}).get("image_base64")
        assert img2 == img1, "Daily drop not idempotent (different image on second call)"

        # /api/archive/drops should reflect the newly generated drop
        r3 = session.get(f"{BASE_URL}/api/archive/drops", params={"wallet": wallet, "page": 1, "limit": 5}, timeout=30)
        assert r3.status_code == 200, r3.text
        d = r3.json()
        assert d.get("total", 0) >= 1, f"Expected drops total>=1, got {d.get('total')}"
        drops = d.get("drops", [])
        assert len(drops) >= 1 and drops[0].get("image_base64"), "First drop missing image_base64"


# --- Fix 3: Classifier tightening — tangential message must NOT unlock ---

class TestClassifierNegative:
    def test_tangential_no_unlock(self, session):
        wallet = f"ClassifierNegTest_{int(time.time())}_{_rand(4)}"
        payload = {
            "wallet_address": wallet,
            "message": "hi",
            "session_id": f"sess_{_rand(6)}",
        }
        r = session.post(f"{BASE_URL}/api/ai/chat", json=payload, timeout=90)
        # Accept 200 or fallback; we care about unlocks
        assert r.status_code in (200, 201), f"chat status {r.status_code}: {r.text[:300]}"
        # Wait for async classifier to run
        time.sleep(15)
        r2 = session.get(f"{BASE_URL}/api/archive/unlocks", params={"wallet": wallet}, timeout=30)
        assert r2.status_code == 200, r2.text
        j = r2.json()
        unlocks = j.get("unlocks", j if isinstance(j, list) else [])
        # Filter out event-based auto-unlocks (Fix 1 first-drop etc.) — we only care about classifier unlocks
        classifier_unlocks = [u for u in unlocks if not str(u.get("unlock_prompt", "")).startswith("EVENT:")]
        assert len(classifier_unlocks) == 0, f"Tangential 'hi' should not classifier-unlock, got: {classifier_unlocks}"


# --- Fix 7: Chatbot canon + banned openers ---

class TestBannedOpeners:
    def test_grizzlor_response_no_banned_openers(self, session):
        wallet = f"LoreTest_{_rand(6)}"
        payload = {
            "wallet_address": wallet,
            "message": "Tell me the full story of what happened to Grizzlor",
            "session_id": f"sess_{_rand(6)}",
        }
        r = session.post(f"{BASE_URL}/api/ai/chat", json=payload, timeout=120)
        assert r.status_code == 200, r.text
        j = r.json()
        reply = j.get("response") or j.get("reply") or j.get("message", "")
        assert reply and len(reply) > 40, f"Reply too short: {reply!r}"
        low = reply.strip()
        for banned in BANNED_OPENERS:
            assert not low.startswith(banned), f"Reply starts with banned opener {banned!r}: {low[:120]!r}"
        # Should contain some lore substance — check for at least one relevant token
        assert any(tok.lower() in reply.lower() for tok in ["grizzlor", "ledger", "ember", "keeper", "chain"]), \
            f"Reply lacks lore substance: {reply[:200]}"
