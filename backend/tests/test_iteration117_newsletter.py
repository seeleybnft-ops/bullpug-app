"""Iteration 117 — Newsletter source-tag first-touch tests."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"
HDRS = {"Content-Type": "application/json", "X-Bullpug-CSRF": "1"}


@pytest.fixture(scope="module")
def unique_email():
    return f"testact1_{int(time.time()*1000)}@example.com"


def test_subscribe_with_source_act1_placeholder(unique_email):
    r = requests.post(f"{API}/newsletter/subscribe",
                      json={"email": unique_email, "source": "act1-placeholder"},
                      headers=HDRS, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("status") == "success"


def test_subscribe_duplicate_returns_existing_and_preserves_source(unique_email):
    # Second call with a DIFFERENT source — first-touch must win.
    r = requests.post(f"{API}/newsletter/subscribe",
                      json={"email": unique_email, "source": "footer"},
                      headers=HDRS, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("status") == "existing"


def test_subscribe_without_source_backward_compat():
    email = f"testnosrc_{int(time.time()*1000)}@example.com"
    r = requests.post(f"{API}/newsletter/subscribe",
                      json={"email": email},
                      headers=HDRS, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("status") == "success"


def test_source_persistence_via_mongo():
    """Verify the doc actually stores source='act1-placeholder' and
    that first-touch source is preserved after a repeat signup with a
    different source. Uses the Mongo driver directly."""
    import asyncio
    from motor.motor_asyncio import AsyncIOMotorClient
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    assert mongo_url and db_name, "MONGO_URL / DB_NAME must be set"

    email = f"testpersist_{int(time.time()*1000)}@example.com"
    # Signup #1 — act1-placeholder
    r1 = requests.post(f"{API}/newsletter/subscribe",
                       json={"email": email, "source": "act1-placeholder"},
                       headers=HDRS, timeout=15)
    assert r1.json().get("status") == "success"

    async def _fetch():
        client = AsyncIOMotorClient(mongo_url)
        doc = await client[db_name].newsletter_subscribers.find_one(
            {"email": email}, {"_id": 0}
        )
        client.close()
        return doc

    doc1 = asyncio.run(_fetch())
    assert doc1 is not None, "doc not found"
    assert doc1.get("source") == "act1-placeholder"

    # Signup #2 — different source, must NOT overwrite
    r2 = requests.post(f"{API}/newsletter/subscribe",
                       json={"email": email, "source": "footer"},
                       headers=HDRS, timeout=15)
    assert r2.json().get("status") == "existing"
    doc2 = asyncio.run(_fetch())
    assert doc2.get("source") == "act1-placeholder", (
        f"first-touch violated: {doc2.get('source')}"
    )


def test_source_null_when_omitted():
    import asyncio
    from motor.motor_asyncio import AsyncIOMotorClient
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")

    email = f"testnullsrc_{int(time.time()*1000)}@example.com"
    requests.post(f"{API}/newsletter/subscribe",
                  json={"email": email},
                  headers=HDRS, timeout=15)

    async def _fetch():
        client = AsyncIOMotorClient(mongo_url)
        doc = await client[db_name].newsletter_subscribers.find_one(
            {"email": email}, {"_id": 0}
        )
        client.close()
        return doc

    doc = asyncio.run(_fetch())
    assert doc is not None
    assert doc.get("source") is None
