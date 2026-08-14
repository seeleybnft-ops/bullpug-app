"""Iter 106 — Bullpug vs Tinkerpug disambiguation tests.

Verifies:
1. Bullpug image asks return image_base64 with archive-voice caption.
2. Tinkerpug image asks return image_base64 (new capability).
3. Source-code verification of intent-detection routing helpers.
4. Prose appearance for Bullpug no longer contains Tinkerpug's cybernetic
   augments and no banned mystical vocabulary.
"""
import os
import re
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
HEADERS = {"Content-Type": "application/json", "X-Bullpug-CSRF": "1"}
AI_CHAT = f"{BASE_URL}/api/ai/chat"
AI_SRC = "/app/backend/routers/ai_chat.py"

ARCHIVE_VOICE_HINTS = [
    "archive", "vault", "ledger", "record", "keeper", "genesis",
]

BANNED_MYSTICAL = [
    "luminous", "ethereal", "aglow", "radiant", "translucent",
    "shimmering",
]

TINKERPUG_AUGMENTS = [
    "cybernetic tail", "armoured foreleg", "armored foreleg",
    "techno collar", "segmented tail",
]


def _post(message, sid):
    return requests.post(
        AI_CHAT,
        json={
            "message": message,
            "session_id": sid,
            "active_tab": "dashboard",
            "chat_history": [],
        },
        headers=HEADERS,
        timeout=180,
    )


# ---------- Image routing: Bullpug ----------
@pytest.mark.parametrize(
    "message,sid",
    [
        ("show me bullpug", "disamb-bullpug-1"),
        ("let me see bullpug at Newpug City", "disamb-bullpug-2"),
        ("/image bullpug on a rooftop", "disamb-bullpug-3"),
    ],
)
def test_bullpug_image_routing(message, sid):
    r = _post(message, sid)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:300]}"
    data = r.json()
    img = data.get("image_base64") or ""
    text = (data.get("response") or "").lower()
    assert img, f"Missing image_base64 for '{message}'. Response: {data}"
    assert len(img) > 100, f"image_base64 too short ({len(img)} chars)"
    # Archive-voice hint (at least one)
    has_voice = any(h in text for h in ARCHIVE_VOICE_HINTS)
    print(f"[{sid}] img_len={len(img)} voice={has_voice} text={text[:200]}")
    assert has_voice, f"No archive-voice hints in response: {text[:300]}"


# ---------- Image routing: Tinkerpug ----------
@pytest.mark.parametrize(
    "message,sid",
    [
        ("show me tinkerpug", "disamb-tinkerpug-1"),
        ("let me see tinkerpug in his workshop", "disamb-tinkerpug-2"),
        ("/image tinkerpug at his workbench", "disamb-tinkerpug-3"),
    ],
)
def test_tinkerpug_image_routing(message, sid):
    r = _post(message, sid)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:300]}"
    data = r.json()
    img = data.get("image_base64") or ""
    assert img, f"Missing image_base64 for '{message}'. Response keys: {list(data.keys())}"
    assert len(img) > 100, f"image_base64 too short ({len(img)} chars)"
    print(f"[{sid}] img_len={len(img)}")


# ---------- Source code verification ----------
def test_source_code_disambiguation():
    with open(AI_SRC, "r") as f:
        src = f.read()

    # (a) _IMAGE_BULLPUG_PATTERN includes tinkerpug alternative
    assert "tinkerpug(?:\\s+.+)?|bullpug(?:\\s+.+)?" in src, \
        "Regex must include tinkerpug|bullpug alternatives"

    # (b) _tag_character helper exists and emits both headers
    assert "def _tag_character(prompt" in src, "_tag_character helper missing"
    assert "SUBJECT: TINKERPUG" in src, "TINKERPUG subject header missing"
    assert "SUBJECT: BULLPUG" in src, "BULLPUG subject header missing"

    # (c) _detect_image_prompt calls _tag_character on both match paths
    detect_block = re.search(
        r"def _detect_image_prompt.*?(?=\ndef )", src, re.DOTALL
    )
    assert detect_block, "_detect_image_prompt not found"
    tag_calls = detect_block.group(0).count("_tag_character(")
    assert tag_calls >= 2, f"_tag_character called only {tag_calls} times in _detect_image_prompt"

    # (d) _BULLPUG_IMAGE_STYLE contains CHARACTER DISAMBIGUATION + rule
    style_block = re.search(
        r"_BULLPUG_IMAGE_STYLE\s*=\s*\((.*?)\)\s*\n", src, re.DOTALL
    )
    assert style_block, "_BULLPUG_IMAGE_STYLE not found"
    style_txt = style_block.group(1)
    assert "CHARACTER DISAMBIGUATION" in style_txt
    assert "Bullpug has NO cybernetic parts" in style_txt
    assert "Tinkerpug" in style_txt and "cybernetic tail" in style_txt

    # (e) _generate_image_response system_message contains the same
    gen_block = re.search(
        r"async def _generate_image_response.*?(?=\nasync def |\ndef )",
        src, re.DOTALL,
    )
    assert gen_block, "_generate_image_response not found"
    gen_txt = gen_block.group(0)
    assert "CHARACTER DISAMBIGUATION" in gen_txt
    assert "Bullpug has NO cybernetic" in gen_txt


# ---------- Prose appearance: Bullpug no cybernetics/no mystical ----------
def test_bullpug_appearance_prose_no_augments_no_mystical():
    message = "what does bullpug look like?"
    max_tries = 3
    attempts = []
    for i in range(1, max_tries + 1):
        sid = f"appearance-post-disamb-{i}"
        r = _post(message, sid)
        assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:300]}"
        text = (r.json().get("response") or "")
        lower = text.lower()
        augment_hits = [a for a in TINKERPUG_AUGMENTS if a in lower]
        banned_hits = [b for b in BANNED_MYSTICAL if b in lower]
        has_fawn = "fawn" in lower
        has_pug = "pug" in lower
        has_horns = "bull horns" in lower or "horns" in lower
        attempts.append({
            "sid": sid, "augments": augment_hits, "banned": banned_hits,
            "fawn": has_fawn, "pug": has_pug, "horns": has_horns,
            "text": text,
        })
        print(f"[{sid}] augments={augment_hits} banned={banned_hits} "
              f"fawn={has_fawn} pug={has_pug} horns={has_horns} "
              f"text={text[:300]}")
        if (not augment_hits and not banned_hits
                and has_fawn and has_pug and has_horns):
            return
        time.sleep(1)

    # Give detailed failure info
    print("\n=== FULL TRANSCRIPTS ===")
    for a in attempts:
        print(f"--- {a['sid']} ---\n{a['text']}\n")
    pytest.fail(
        f"After {max_tries} tries: no clean+canonical response. "
        f"attempts={[{k: v for k, v in a.items() if k != 'text'} for a in attempts]}"
    )
