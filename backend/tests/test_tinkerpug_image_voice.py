"""Regression retest for Tinkerpug /image voice guardrail (iter 103)."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")

FORBIDDEN = [
    "fresh from the pugchain canvas",
    "i don't have sketches",
    "let me compile",
    "while we wait",
    "hold on while i prepare",
    "i'll generate",
    "generate an image",
    "ai image",
    "let me create",
]

EXPECTED_HINTS = ["archive", "vault", "keeper", "ledger", "on file", "record", "direct from"]


def _post_chat(message, session_id):
    return requests.post(
        f"{BASE_URL}/api/ai/chat",
        json={
            "message": message,
            "session_id": session_id,
            "active_tab": "dashboard",
            "chat_history": [],
        },
        headers={"Content-Type": "application/json", "X-Bullpug-CSRF": "1"},
        timeout=120,
    )


@pytest.mark.parametrize("sid", ["voice-retest-1", "voice-retest-2", "voice-retest-3"])
def test_tinkerpug_image_voice_regression(sid):
    r = _post_chat("/image bullpug at Newpug City rooftop", sid)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:400]}"
    data = r.json()
    text = (data.get("response") or "")
    lower = text.lower()
    print(f"\n[{sid}] response: {text[:600]}")
    assert text, f"Empty response field: {data}"
    for phrase in FORBIDDEN:
        assert phrase not in lower, f"FORBIDDEN phrase '{phrase}' present in: {text}"
    has_hint = any(h in lower for h in EXPECTED_HINTS)
    assert has_hint, f"No archive/vault hint present in: {text}"
