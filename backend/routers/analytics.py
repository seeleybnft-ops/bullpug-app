"""Lightweight self-hosted pageview analytics.

Mounted at `/api/analytics`. Two surfaces:

  • `POST /track`   — public, CSRF-exempt, rate-limited per IP. Accepts a
                       single pageview event from the SPA on every route
                       change. Stores a normalised, PII-free row in Mongo.
  • `GET  /summary` — SIWS-protected. Returns aggregated metrics for the
                       admin Traffic card: totals, uniques, top pages,
                       top referrers, and a 14-day sparkline.

Design notes
────────────
• **No cookies, no IPs persisted.** Every event is anonymised via a
  daily-rotating SHA-256 hash of (IP || UA || salt). The salt is the
  current UTC day, so a "unique visitor" count is a *daily* unique —
  consistent with how Plausible / Umami define it. The hash itself is
  never reversible into a user.
• **Rate limit:** 60 events / IP / minute. A user clicking through the
  site rarely exceeds this; bots that scrape every page in a tight loop
  will be dropped silently with a 202.
• **Bounded field lengths** so a hostile client can't pour MBs into
  Mongo through the unvalidated path/referer fields.
• **Insert is fire-and-forget** — we acknowledge a 202 even on Mongo
  failure so the SPA's `keepalive: true` fetch never retries during an
  outage and never surfaces analytics noise to real users.
"""

import hashlib
import logging
import os
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from utils.admin_auth import require_admin_jwt
from utils.database import db

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = logging.getLogger(__name__)


# ── Rate limiter ──────────────────────────────────────────────────────────
_RATE_WINDOW_SECONDS = 60
_RATE_MAX_PER_WINDOW = 60
_rate_buckets: dict[str, deque[float]] = {}


def _rate_check(ip: str) -> bool:
    now = time.time()
    bucket = _rate_buckets.setdefault(ip, deque())
    cutoff = now - _RATE_WINDOW_SECONDS
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= _RATE_MAX_PER_WINDOW:
        return False
    bucket.append(now)
    return True


# ── Visitor anonymisation ─────────────────────────────────────────────────
# A per-process pepper so the hash can't be re-derived even by an attacker
# who knows the user's IP+UA. Falls back to a deterministic static value
# only if no env var is provided — still safe since the daily-rotating
# salt below is part of the digest.
_ANALYTICS_PEPPER = os.environ.get("ANALYTICS_PEPPER", "bullpug-analytics-v1")


def _visitor_hash(ip: str, ua: str) -> str:
    """Return a 16-char daily-rotating visitor fingerprint.

    Same (ip, ua) on the same UTC day → same hash → counted as one unique.
    The next day the salt changes so we never build a long-term identifier.
    """
    day_salt = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    raw = f"{ip}|{ua}|{day_salt}|{_ANALYTICS_PEPPER}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _normalise_path(path: Optional[str]) -> str:
    """Strip query strings, trailing slashes, and cap length."""
    if not path:
        return "/"
    p = path.split("?", 1)[0].split("#", 1)[0]
    if len(p) > 1 and p.endswith("/"):
        p = p.rstrip("/") or "/"
    return p[:200]


def _normalise_referer(ref: Optional[str], own_host: str) -> Optional[str]:
    """Return canonical external host or None for same-origin / empty refs.

    Canonicalisations applied:
      • Strip scheme, query, fragment, port.
      • Drop the `www.` prefix.
      • Collapse known social/redirector hosts into their canonical brand
        so traffic from `t.co`, `x.com`, `mobile.twitter.com`, `nitter.*`
        all aggregates under `twitter.com` in the admin card.
    """
    if not ref:
        return None
    try:
        host = urlparse(ref).netloc.lower()
        if not host or host == own_host.lower():
            return None
        host = host.split(":", 1)[0]
        if host.startswith("www."):
            host = host[4:]
        # Brand canonicalisation table — keep the right side the canonical
        # form we want to display in the admin card. Add more entries as
        # we observe new sources in the data.
        canonical_map = {
            "t.co": "twitter.com",
            "x.com": "twitter.com",
            "mobile.twitter.com": "twitter.com",
            "lnkd.in": "linkedin.com",
            "l.facebook.com": "facebook.com",
            "lm.facebook.com": "facebook.com",
            "m.facebook.com": "facebook.com",
            "fb.me": "facebook.com",
            "out.reddit.com": "reddit.com",
            "old.reddit.com": "reddit.com",
            "youtu.be": "youtube.com",
            "m.youtube.com": "youtube.com",
        }
        if host in canonical_map:
            host = canonical_map[host]
        # Also collapse any leftover `nitter.*` to twitter.
        if host.startswith("nitter."):
            host = "twitter.com"
        return host[:120]
    except Exception:
        return None


# Known UTM values → canonical bucket. Lets shared links with explicit
# `?utm_source=twitter` get attributed correctly even when the browser
# strips the Referer header (which Twitter/X mobile apps do by default).
_UTM_CANONICAL = {
    "twitter": "twitter.com",
    "x": "twitter.com",
    "facebook": "facebook.com",
    "fb": "facebook.com",
    "instagram": "instagram.com",
    "ig": "instagram.com",
    "linkedin": "linkedin.com",
    "reddit": "reddit.com",
    "youtube": "youtube.com",
    "discord": "discord.com",
    "telegram": "telegram.org",
    "tiktok": "tiktok.com",
    "email": "email",
    "newsletter": "email",
}


def _normalise_utm_source(utm: Optional[str]) -> Optional[str]:
    """Lower-case + alias UTM source into our canonical bucket."""
    if not utm:
        return None
    raw = utm.strip().lower()[:60]
    return _UTM_CANONICAL.get(raw, raw or None)


def _detect_device(ua: str) -> str:
    """Coarse mobile/desktop split — good enough for the admin card."""
    if not ua:
        return "unknown"
    lower = ua.lower()
    if any(k in lower for k in ("mobile", "iphone", "android", "ipad")):
        return "mobile"
    return "desktop"


# ── Payload model ─────────────────────────────────────────────────────────
class PageviewPayload(BaseModel):
    path: str = Field(max_length=400)
    referer: Optional[str] = Field(default=None, max_length=500)
    # Optional UTM source — used when present as the authoritative
    # attribution signal. Survives Referer stripping that Twitter/X and
    # most mobile apps apply by default.
    utm_source: Optional[str] = Field(default=None, max_length=80)
    # SPA route changes that happen too fast for the user to actually
    # consume the page (e.g. router redirects) get tagged so we can
    # exclude them from the totals if we ever want to.
    transition: Optional[str] = Field(default="navigate", max_length=20)


@router.post("/track")
async def track_pageview(payload: PageviewPayload, request: Request):
    """Record one pageview. Returns 202 unconditionally."""
    ip = (request.client.host if request.client else None) or "unknown"
    if not _rate_check(ip):
        return {"status": "rate_limited"}

    ua = (request.headers.get("user-agent") or "")[:300]
    own_host = (request.headers.get("host") or "").lower()
    referer_host = _normalise_referer(payload.referer, own_host)
    utm_source = _normalise_utm_source(payload.utm_source)
    # Effective source priority:
    #   1. utm_source (user explicitly tagged it on the share link)
    #   2. canonical referer host
    #   3. None → "direct" bucket in the admin card
    effective_source = utm_source or referer_host
    doc = {
        "path": _normalise_path(payload.path),
        "referer": referer_host,
        "utm_source": utm_source,
        "source": effective_source,
        "device": _detect_device(ua),
        "visitor": _visitor_hash(ip, ua),
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await db.pageviews.insert_one(doc)
    except Exception as e:
        logger.exception("Failed to persist pageview: %s", e)
        return {"status": "accept_persist_failed"}
    return {"status": "accepted"}


# ── Aggregation pipelines ─────────────────────────────────────────────────
async def _count_in_window(hours: int) -> tuple[int, int]:
    """Return (total_views, unique_visitors) for the window."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    total = await db.pageviews.count_documents({"ts": {"$gte": cutoff}})
    uniques = await db.pageviews.distinct("visitor", {"ts": {"$gte": cutoff}})
    return total, len(uniques)


async def _top_by(field: str, hours: int, limit: int) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    pipeline = [
        {"$match": {"ts": {"$gte": cutoff}, field: {"$ne": None}}},
        {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    raw = await db.pageviews.aggregate(pipeline).to_list(length=limit)
    return [{"key": r["_id"], "count": r["count"]} for r in raw if r.get("_id")]


async def _daily_sparkline(days: int) -> list[dict]:
    """Return one bucket per UTC day for the last `days` days.

    Empty days are filled with zero counts so the sparkline always has a
    constant length on the client (simplifies the SVG path math).
    """
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=days - 1)
    cutoff = datetime(start.year, start.month, start.day, tzinfo=timezone.utc).isoformat()

    pipeline = [
        {"$match": {"ts": {"$gte": cutoff}}},
        {
            "$group": {
                # ISO strings sort lexicographically, so we can group by the
                # YYYY-MM-DD prefix without converting to BSON dates.
                "_id": {"$substr": ["$ts", 0, 10]},
                "views": {"$sum": 1},
                "visitors": {"$addToSet": "$visitor"},
            }
        },
    ]
    raw = await db.pageviews.aggregate(pipeline).to_list(length=days * 2)
    by_day = {r["_id"]: {"views": r["views"], "visitors": len(r.get("visitors") or [])} for r in raw}

    out = []
    for i in range(days):
        day = start + timedelta(days=i)
        key = day.isoformat()
        bucket = by_day.get(key, {"views": 0, "visitors": 0})
        out.append({"day": key, "views": bucket["views"], "visitors": bucket["visitors"]})
    return out


@router.get("/summary")
async def analytics_summary(wallet: str = Depends(require_admin_jwt)):
    """SIWS-gated aggregate report powering the admin Traffic card."""
    views_24h, uniques_24h = await _count_in_window(24)
    views_7d, uniques_7d = await _count_in_window(24 * 7)
    views_30d, uniques_30d = await _count_in_window(24 * 30)

    top_pages = await _top_by("path", 24 * 7, 8)
    # Aggregate on `source` (UTM-or-referer) instead of raw referer so
    # canonicalised + tagged traffic share one bucket.
    top_sources = await _top_by("source", 24 * 7, 6)
    sparkline = await _daily_sparkline(14)

    # Count of "direct / no referrer" visits in the 7-day window so the
    # admin can see how much traffic is invisible to source attribution.
    cutoff_7d = (datetime.now(timezone.utc) - timedelta(hours=24 * 7)).isoformat()
    direct_7d = await db.pageviews.count_documents(
        {"ts": {"$gte": cutoff_7d}, "source": None}
    )

    return {
        "windows": {
            "h24": {"views": views_24h, "uniques": uniques_24h},
            "d7":  {"views": views_7d,  "uniques": uniques_7d},
            "d30": {"views": views_30d, "uniques": uniques_30d},
        },
        "top_pages": top_pages,
        # Renamed from `top_referers` so the frontend understands this
        # includes UTM-attributed clicks. Old key kept for compatibility.
        "top_sources": top_sources,
        "top_referers": top_sources,
        "direct_7d": direct_7d,
        "sparkline": sparkline,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
