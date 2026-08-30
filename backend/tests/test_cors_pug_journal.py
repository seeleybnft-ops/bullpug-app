"""CORS regression test for adding https://pug-journal-2.emergent.host to CORS_ORIGINS."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cosmic-runner-hub.preview.emergentagent.com").rstrip("/")

NEW_ORIGIN = "https://pug-journal-2.emergent.host"
BULLPUG_ORIGIN = "https://bullpug.com"
PREVIEW_ORIGIN = "https://cosmic-runner-hub.preview.emergentagent.com"
BOGUS_ORIGIN = "https://not-allowed.example.com"

ALLOWED_ORIGINS = [NEW_ORIGIN, BULLPUG_ORIGIN, PREVIEW_ORIGIN]


def _acao_ok(resp, origin):
    acao = resp.headers.get("Access-Control-Allow-Origin", "")
    return acao == "*" or acao == origin


# ---- .env / process env verification ----
def test_env_contains_new_origin():
    with open("/app/backend/.env") as f:
        content = f.read()
    assert NEW_ORIGIN in content
    assert BULLPUG_ORIGIN in content
    assert PREVIEW_ORIGIN in content


# ---- Preflight OPTIONS ----
@pytest.mark.parametrize("origin", ALLOWED_ORIGINS)
@pytest.mark.parametrize("path", [
    "/api/archive/entries",
    "/api/archive/rank",
    "/api/archive/drops",
    "/api/archive/share",
])
def test_preflight_options(origin, path):
    resp = requests.options(
        f"{BASE_URL}{path}",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET" if path != "/api/archive/share" else "POST",
            "Access-Control-Request-Headers": "content-type,x-bullpug-csrf",
        },
        timeout=15,
    )
    assert resp.status_code in (200, 204), f"{path} preflight got {resp.status_code}"
    assert _acao_ok(resp, origin), f"ACAO header wrong for {origin} @ {path}: {resp.headers.get('Access-Control-Allow-Origin')}"


# ---- GET /api/archive/entries with new origin ----
def test_archive_entries_new_origin():
    resp = requests.get(
        f"{BASE_URL}/api/archive/entries",
        headers={"Origin": NEW_ORIGIN},
        timeout=15,
    )
    assert resp.status_code == 200
    assert _acao_ok(resp, NEW_ORIGIN)
    data = resp.json()
    # Response could be a list or dict with entries key
    entries = data if isinstance(data, list) else data.get("entries", data.get("data", []))
    assert isinstance(entries, list)
    assert len(entries) == 27, f"Expected 27 entries, got {len(entries)}"


def test_archive_rank_new_origin():
    resp = requests.get(
        f"{BASE_URL}/api/archive/rank",
        params={"wallet": "TEST123"},
        headers={"Origin": NEW_ORIGIN},
        timeout=15,
    )
    assert resp.status_code == 200
    assert _acao_ok(resp, NEW_ORIGIN)


def test_archive_drops_new_origin():
    resp = requests.get(
        f"{BASE_URL}/api/archive/drops",
        params={"wallet": "TEST123", "page": 1, "limit": 5},
        headers={"Origin": NEW_ORIGIN},
        timeout=15,
    )
    assert resp.status_code == 200
    assert _acao_ok(resp, NEW_ORIGIN)


def test_archive_share_post_new_origin():
    resp = requests.post(
        f"{BASE_URL}/api/archive/share",
        json={"wallet": "TEST123"},
        headers={
            "Origin": NEW_ORIGIN,
            "X-Bullpug-CSRF": "1",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    assert resp.status_code == 200, f"Body: {resp.text[:300]}"
    assert _acao_ok(resp, NEW_ORIGIN)
    data = resp.json()
    assert "image_base64" in data, f"Missing image_base64 in response: {list(data.keys())}"
    assert isinstance(data["image_base64"], str) and len(data["image_base64"]) > 0


# ---- Regression: previously-allowed origins still work ----
@pytest.mark.parametrize("origin", [BULLPUG_ORIGIN, PREVIEW_ORIGIN])
def test_archive_entries_previously_allowed_origins(origin):
    resp = requests.get(
        f"{BASE_URL}/api/archive/entries",
        headers={"Origin": origin},
        timeout=15,
    )
    assert resp.status_code == 200
    assert _acao_ok(resp, origin)


# ---- Bogus origin: request should still succeed (CORS enforced by browser),
#      but Access-Control-Allow-Origin must NOT echo the bogus origin.
def test_bogus_origin_not_reflected():
    resp = requests.get(
        f"{BASE_URL}/api/archive/entries",
        headers={"Origin": BOGUS_ORIGIN},
        timeout=15,
    )
    acao = resp.headers.get("Access-Control-Allow-Origin", "")
    # It must not equal the bogus origin. '*' is acceptable (ingress-level) but not the bogus echo.
    assert acao != BOGUS_ORIGIN, f"Bogus origin was reflected in ACAO: {acao}"
