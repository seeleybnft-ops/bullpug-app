"""Iter 104 - Tinkerpug fixes:
  1) Short-form image intent detection (routes to _generate_image_response)
  2) Image caption voice (no mystical openers)
  3) Canon appearance in text-only replies
  4) Voice: no banned openers on greetings
"""
import os
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
HEADERS = {"Content-Type": "application/json", "X-Bullpug-CSRF": "1"}

# Forbidden phrases across contexts
BANNED_VOICE = [
    "greetings", "seeker", "traveler", "wanderer", "chosen one", "young one",
    "dear friend", "behold", "verily", "ah, a request", "ah, an inquiry",
    "allow me to",
]

BANNED_IMAGE_EXTRA = [
    "in the spirit of bullpug", "hero shot", "essence of his cosmic origin",
    "luminous", "aglow with starlight", "aglow with", "radiant", "ethereal",
    "translucent starlight", "while we wait", "let me compile",
    "i don't have sketches", "i'll generate",
]

BANNED_APPEARANCE = [
    "luminous", "aglow with starlight", "aglow with", "radiant", "ethereal",
    "translucent", "shimmering with cosmic light", "bathed in starlight",
]

ARCHIVE_HINTS = ["archive", "vault", "ledger", "keeper", "record", "on file", "direct from"]

CANON_PRIMARY = ["fawn", "pug"]
CANON_SECONDARY = ["bull horns", "cybernetic", "tail", "armoured", "armored", "techno collar"]


def _post_chat(message, session_id):
    return requests.post(
        f"{BASE_URL}/api/ai/chat",
        json={
            "message": message,
            "session_id": session_id,
            "active_tab": "dashboard",
            "chat_history": [],
        },
        headers=HEADERS,
        timeout=120,
    )


def _post_with_retry_for_image(message, session_id_base, max_tries=2):
    """Retry once with different session_id if no image_base64 (LLM flakiness)."""
    last_data = None
    last_text = ""
    for attempt in range(max_tries):
        sid = f"{session_id_base}-try{attempt}"
        r = _post_chat(message, sid)
        assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:400]}"
        data = r.json()
        img = data.get("image_base64") or ""
        last_data = data
        last_text = data.get("response") or ""
        if img and img.startswith("data:image/"):
            return data
        time.sleep(1)
    return last_data  # will fail assertion in caller


# ------------------------------- Test 1 & 2 -------------------------------
@pytest.mark.parametrize(
    "message,sid_base",
    [
        ("show me bullpug", "intent-1"),
        ("let me see bullpug at Newpug City", "intent-2"),
        ("can I see bullpug", "intent-3"),
    ],
)
def test_short_form_image_intent_and_voice(message, sid_base):
    data = _post_with_retry_for_image(message, sid_base)
    img = data.get("image_base64") or ""
    text = (data.get("response") or "")
    lower = text.lower()

    print(f"\n[{sid_base}] message='{message}' img_present={bool(img)} text={text[:400]}")

    # (1) IMAGE INTENT DETECTION
    assert img, f"No image_base64 returned for '{message}'. Text-only response: {text[:300]}"
    assert img.startswith("data:image/"), f"image_base64 not a data URL: {img[:60]}"

    # (2) IMAGE VOICE - no banned phrases
    for phrase in BANNED_VOICE + BANNED_IMAGE_EXTRA:
        assert phrase not in lower, f"FORBIDDEN phrase '{phrase}' present in caption: {text}"

    # Should hint archive/vault framing
    assert any(h in lower for h in ARCHIVE_HINTS), (
        f"No archive/vault/ledger framing in caption for '{message}': {text}"
    )


# ------------------------------- Test 3 -------------------------------
@pytest.mark.parametrize(
    "message,sid",
    [
        ("what does bullpug look like?", "appearance-1"),
        ("describe bullpug", "appearance-2"),
    ],
)
def test_canon_appearance(message, sid):
    r = _post_chat(message, sid)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:400]}"
    data = r.json()
    text = data.get("response") or ""
    lower = text.lower()

    print(f"\n[{sid}] message='{message}' text={text[:600]}")
    assert text, f"Empty response: {data}"

    # (a) No mystical vocab
    for phrase in BANNED_APPEARANCE:
        assert phrase not in lower, f"BANNED mystical phrase '{phrase}' in appearance response: {text}"

    # (b) Should reference canonical elements
    has_primary = any(p in lower for p in CANON_PRIMARY)
    has_secondary = any(s in lower for s in CANON_SECONDARY)
    assert has_primary, f"Missing canonical primary ('fawn'/'pug') in: {text}"
    assert has_secondary, f"Missing canonical secondary elements (bull horns/cybernetic/tail/armoured/techno collar) in: {text}"


# ------------------------------- Test 4 -------------------------------
@pytest.mark.parametrize(
    "message,sid",
    [
        ("hi tinkerpug", "voice-a"),
        ("what's up", "voice-b"),
        ("hello", "voice-c"),
    ],
)
def test_no_banned_openers(message, sid):
    r = _post_chat(message, sid)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:400]}"
    data = r.json()
    text = data.get("response") or ""
    lower = text.lower()

    print(f"\n[{sid}] message='{message}' text={text[:400]}")
    assert text, f"Empty response: {data}"

    for phrase in BANNED_VOICE:
        assert phrase not in lower, f"BANNED opener/phrase '{phrase}' present for '{message}': {text}"
