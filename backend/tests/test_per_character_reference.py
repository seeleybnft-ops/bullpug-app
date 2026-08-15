"""Iteration 108 — Per-character reference image wiring tests.

Verifies:
  1. Source-code layout in daily_drop.py (constants, cache, helpers).
  2. Source-code layout in ai_chat.py (_generate_image_response branching).
  3. Runtime cache independence (loader returns different + cached b64).
  4. End-to-end regression via /api/ai/chat for both characters.
"""

import os
import re
import sys
import asyncio
import pathlib
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
BACKEND_DIR = pathlib.Path("/app/backend")
sys.path.insert(0, str(BACKEND_DIR))

DAILY_DROP = (BACKEND_DIR / "services/daily_drop.py").read_text()
AI_CHAT = (BACKEND_DIR / "routers/ai_chat.py").read_text()


# ── Source code verification — daily_drop.py ──────────────────────────
class TestDailyDropSource:
    def test_bullpug_reference_url_constant(self):
        assert "_BULLPUG_REFERENCE_URL = \"https://i.imgur.com/XC7pHKW.jpeg\"" in DAILY_DROP

    def test_tinkerpug_reference_url_constant(self):
        assert "_TINKERPUG_REFERENCE_URL = \"https://i.imgur.com/hXukVoJ.jpeg\"" in DAILY_DROP

    def test_reference_cache_is_dict_with_both_urls(self):
        from services import daily_drop as dd
        assert isinstance(dd._reference_cache, dict)
        assert dd._BULLPUG_REFERENCE_URL in dd._reference_cache
        assert dd._TINKERPUG_REFERENCE_URL in dd._reference_cache

    def test_load_reference_b64_signature(self):
        from services import daily_drop as dd
        assert callable(dd._load_reference_b64)
        # takes url param
        assert "async def _load_reference_b64(url: str)" in DAILY_DROP
        # browser-UA still present
        assert "Mozilla/5.0" in DAILY_DROP
        # only cache on success — assignment inside try block after b64 encode
        assert "_reference_cache[url] = b64" in DAILY_DROP

    def test_pick_reference_for_scene_tinkerpug(self):
        from services import daily_drop as dd
        assert dd._pick_reference_for_scene("Tinkerpug's workshop", "scene") == dd._TINKERPUG_REFERENCE_URL
        assert dd._pick_reference_for_scene("", "a tinkerpug moment") == dd._TINKERPUG_REFERENCE_URL

    def test_pick_reference_for_scene_bullpug_default(self):
        from services import daily_drop as dd
        assert dd._pick_reference_for_scene("Cometside Vigil", "Guardian Bullpug rides a comet") == dd._BULLPUG_REFERENCE_URL
        # unnamed defaults to Bullpug
        assert dd._pick_reference_for_scene("some theme", "a scene without char") == dd._BULLPUG_REFERENCE_URL

    def test_get_drop_for_user_calls_pick_and_load(self):
        # Ensure the wiring is present textually in get_drop_for_user
        assert "_pick_reference_for_scene(theme, scene)" in DAILY_DROP
        assert "_load_reference_b64(ref_url)" in DAILY_DROP


# ── Source code verification — ai_chat.py ─────────────────────────────
class TestAiChatSource:
    def test_imports_from_daily_drop(self):
        # The function imports both URLs + mime + loader
        assert "_BULLPUG_REFERENCE_URL" in AI_CHAT
        assert "_TINKERPUG_REFERENCE_URL" in AI_CHAT
        assert "_REFERENCE_MIME" in AI_CHAT
        assert "_load_reference_b64" in AI_CHAT
        assert "from services.daily_drop import" in AI_CHAT

    def test_branches_on_subject_prefix(self):
        assert "prompt.startswith(\"SUBJECT: TINKERPUG\")" in AI_CHAT
        assert "prompt.startswith(\"SUBJECT: BULLPUG\")" in AI_CHAT

    def test_user_message_carries_file_contents(self):
        assert re.search(
            r"UserMessage\(text=full_prompt,\s*file_contents=file_contents\)",
            AI_CHAT,
        ), "UserMessage must be called with text=full_prompt, file_contents=file_contents"


# ── Runtime cache independence ────────────────────────────────────────
class TestReferenceCacheRuntime:
    def test_loaders_return_different_and_are_cached(self):
        from services import daily_drop as dd

        # Reset both slots to ensure fresh fetch
        dd._reference_cache[dd._BULLPUG_REFERENCE_URL] = None
        dd._reference_cache[dd._TINKERPUG_REFERENCE_URL] = None

        async def run():
            b = await dd._load_reference_b64(dd._BULLPUG_REFERENCE_URL)
            t = await dd._load_reference_b64(dd._TINKERPUG_REFERENCE_URL)
            return b, t

        b, t = asyncio.run(run())
        if not b or not t:
            pytest.skip(f"Imgur fetch failed (network) — b_len={len(b or '')}, t_len={len(t or '')}")

        # Non-empty
        assert len(b) > 1000
        assert len(t) > 1000
        # Different content — independent cache slots
        assert b != t, "Bullpug and Tinkerpug refs must be distinct base64 blobs"
        # Cached — second call returns immediately with same value
        async def again():
            return (
                await dd._load_reference_b64(dd._BULLPUG_REFERENCE_URL),
                await dd._load_reference_b64(dd._TINKERPUG_REFERENCE_URL),
            )
        b2, t2 = asyncio.run(again())
        assert b2 == b
        assert t2 == t


# ── End-to-end regression via /api/ai/chat ────────────────────────────
class TestImageEndpointRegression:
    HEADERS = {"Content-Type": "application/json", "X-Bullpug-CSRF": "1"}

    def _post_image(self, message: str, session_id: str) -> dict:
        payload = {
            "message": message,
            "session_id": session_id,
            "active_tab": "dashboard",
            "chat_history": [],
        }
        # One retry for LLM flakiness
        last = None
        for attempt in range(2):
            r = requests.post(
                f"{BASE_URL}/api/ai/chat",
                json=payload,
                headers=self.HEADERS,
                timeout=90,
            )
            last = r
            if r.status_code == 200:
                data = r.json()
                if data.get("image_base64") and len(data["image_base64"]) > 50000:
                    return data
        assert False, f"No image returned after 2 attempts. status={last.status_code} body={last.text[:500]}"

    def test_bullpug_image_regression(self):
        data = self._post_image("show me bullpug", "per-char-b-1")
        assert data.get("kind") == "image"
        assert len(data["image_base64"]) > 50000

    def test_tinkerpug_image_regression(self):
        data = self._post_image("show me tinkerpug", "per-char-t-1")
        assert data.get("kind") == "image"
        assert len(data["image_base64"]) > 50000
