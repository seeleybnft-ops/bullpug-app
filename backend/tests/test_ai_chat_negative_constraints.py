"""Regression test for reciprocal negative constraints in _tag_character.

Verifies:
  1. Source-code substrings for tinkerpug and bullpug branches.
  2. Generic (else) branch returns prompt unchanged.
  3. End-to-end /api/ai/chat still returns an image (non-empty image_base64)
     with archive-voice text for both "show me bullpug" and "show me tinkerpug".
"""
import os
import re
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cosmic-runner-hub.preview.emergentagent.com").rstrip("/")
AI_CHAT_URL = f"{BASE_URL}/api/ai/chat"
HEADERS = {"Content-Type": "application/json", "X-Bullpug-CSRF": "1"}

AI_CHAT_SRC = "/app/backend/routers/ai_chat.py"


# --- Source-code verification (runtime output of _tag_character) ------------
import sys
sys.path.insert(0, "/app/backend")
from routers.ai_chat import _tag_character  # noqa: E402


class TestSourceCode:
    def test_tinkerpug_branch_substrings(self):
        out = _tag_character("tinkerpug at his workbench")
        required = [
            "NO galaxy cape",
            "NO cosmic medallion",
            "NO nebula background",
            "cybernetic segmented tail",
            "armoured left foreleg",
            "neon city",
            "workshop",
        ]
        missing = [s for s in required if s not in out]
        assert not missing, f"Tinkerpug branch missing: {missing}\nOutput: {out}"
        assert out.endswith("tinkerpug at his workbench"), "Scene prompt not appended"

    def test_bullpug_branch_substrings(self):
        out = _tag_character("bullpug in the nebula")
        required = [
            "NO cybernetic tail",
            "NO armoured foreleg",
            "NO techno collar",
            "NO workshop tools",
            "flowing galaxy cape",
            "swirling cosmic medallion",
            "deep space",
            "nebula",
        ]
        missing = [s for s in required if s not in out]
        assert not missing, f"Bullpug branch missing: {missing}\nOutput: {out}"
        assert out.endswith("bullpug in the nebula"), "Scene prompt not appended"

    def test_generic_else_branch_unmodified(self):
        prompt = "a bullpughan warrior on a mountain"
        out = _tag_character(prompt)
        # Generic branch must return prompt unchanged (no header/constraints).
        assert out == prompt, f"Generic branch should return prompt unchanged, got: {out}"
        for banned in ["NO galaxy cape", "NO cybernetic tail", "NEGATIVE CONSTRAINTS", "SUBJECT:"]:
            assert banned not in out, f"else branch unexpectedly contains {banned!r}"


# --- End-to-end routing -----------------------------------------------------
def _post_with_retry(payload, attempts=2):
    last = None
    for i in range(attempts):
        try:
            r = requests.post(AI_CHAT_URL, json=payload, headers=HEADERS, timeout=180)
            last = r
            if r.status_code == 200 and r.json().get("image_base64"):
                return r
        except Exception as e:
            last = e
        time.sleep(2)
    return last


ARCHIVE_TOKENS = ["archive", "vault", "ledger", "keeper", "record", "direct from"]


class TestEndToEnd:
    def test_bullpug_image_path(self):
        payload = {
            "message": "show me bullpug",
            "session_id": "neg-bullpug-1",
            "active_tab": "dashboard",
            "chat_history": [],
        }
        r = _post_with_retry(payload)
        assert isinstance(r, requests.Response), f"Request failed: {r}"
        assert r.status_code == 200, f"status={r.status_code} body={r.text[:400]}"
        data = r.json()
        img = data.get("image_base64") or ""
        assert len(img) > 50000, f"image_base64 too small: {len(img)}"
        text = (data.get("response") or data.get("message") or "").lower()
        assert any(t in text for t in ARCHIVE_TOKENS), f"archive-voice tokens absent in: {text[:300]}"

    def test_tinkerpug_image_path(self):
        payload = {
            "message": "show me tinkerpug",
            "session_id": "neg-tinkerpug-1",
            "active_tab": "dashboard",
            "chat_history": [],
        }
        r = _post_with_retry(payload)
        assert isinstance(r, requests.Response), f"Request failed: {r}"
        assert r.status_code == 200, f"status={r.status_code} body={r.text[:400]}"
        data = r.json()
        img = data.get("image_base64") or ""
        assert len(img) > 50000, f"image_base64 too small: {len(img)}"
        text = (data.get("response") or data.get("message") or "").lower()
        assert any(t in text for t in ARCHIVE_TOKENS), f"archive-voice tokens absent in: {text[:300]}"
