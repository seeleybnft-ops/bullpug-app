"""Iter 105 - Targeted regression retest:
Appearance prose must not contain banned mystical vocabulary EVEN in negation.
Retries each phrasing up to 3 times with unique session_ids (LLM stochasticity).
"""
import os
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
HEADERS = {"Content-Type": "application/json", "X-Bullpug-CSRF": "1"}

BANNED_APPEARANCE = [
    "luminous", "ethereal", "aglow", "radiant", "translucent",
    "shimmering", "bathed in starlight", "celestial figure",
    "constellation of stardust",
]

CANON_PRIMARY = ["fawn", "pug"]
CANON_SECONDARY = [
    "bull horns", "cybernetic", "tail", "armoured", "armored", "techno collar",
]


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


def _evaluate(text):
    """Return (clean, has_canon, banned_hits, reasons)."""
    lower = text.lower()
    banned_hits = [b for b in BANNED_APPEARANCE if b in lower]
    has_primary = any(p in lower for p in CANON_PRIMARY)
    has_secondary = any(s in lower for s in CANON_SECONDARY)
    clean = len(banned_hits) == 0
    has_canon = has_primary and has_secondary
    reasons = []
    if banned_hits:
        reasons.append(f"banned={banned_hits}")
    if not has_primary:
        reasons.append("missing_primary(fawn/pug)")
    if not has_secondary:
        reasons.append("missing_secondary(horns/cyber/tail/armoured/collar)")
    return clean, has_canon, banned_hits, reasons


@pytest.mark.parametrize(
    "message,sid_prefix",
    [
        ("describe bullpug", "appearance-retest-a"),
        ("what does bullpug look like?", "appearance-retest-b"),
        ("tell me what bullpug looks like", "appearance-retest-c"),
    ],
)
def test_appearance_no_banned_even_in_negation(message, sid_prefix):
    max_tries = 3
    attempts = []
    clean_and_canonical = False

    for i in range(1, max_tries + 1):
        sid = f"{sid_prefix}-{i}"
        r = _post_chat(message, sid)
        assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:400]}"
        text = (r.json().get("response") or "")
        clean, has_canon, banned_hits, reasons = _evaluate(text)
        attempts.append({
            "sid": sid, "clean": clean, "has_canon": has_canon,
            "banned": banned_hits, "reasons": reasons, "text": text,
        })
        print(f"\n[{sid}] message='{message}' clean={clean} canon={has_canon} "
              f"banned={banned_hits} text={text[:500]}")
        if clean and has_canon:
            clean_and_canonical = True
            break
        time.sleep(1)

    # Print full transcript for debugging
    if not clean_and_canonical:
        print(f"\n=== FAIL DETAIL for '{message}' ===")
        for a in attempts:
            print(f"--- {a['sid']} reasons={a['reasons']} ---")
            print(a["text"])
            print()

    # Primary requirement: at least one clean (no banned words) AND canonical response
    assert clean_and_canonical, (
        f"After {max_tries} tries for '{message}', no response was both clean and canonical. "
        f"Reasons per attempt: {[a['reasons'] for a in attempts]}"
    )
