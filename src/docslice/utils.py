"""Utilities shared across docslice modules."""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import httpx
from slugify import slugify

DEFAULT_USER_AGENT = (
    "docslice/0.1 (+https://github.com/sniper/docslice; documentation slicer)"
)


def normalize_url(url: str, base_url: str) -> str | None:
    raw = url.strip()
    if not raw:
        return None
    if raw.startswith("#"):
        return None

    absolute = urljoin(base_url, raw)
    parsed = urlparse(absolute)
    base = urlparse(base_url)

    if not parsed.scheme or not parsed.netloc:
        return None
    if (parsed.scheme, parsed.netloc) != (base.scheme, base.netloc):
        return None

    query_items = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.startswith("utm_")
    ]
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]

    normalized = parsed._replace(
        path=path,
        query=urlencode(query_items, doseq=True),
        fragment="",
    )
    return urlunparse(normalized)


def slugify_title(title: str | None) -> str:
    raw_title = (title or "").strip()
    slug = slugify(raw_title, separator="_", max_length=50) if raw_title else ""
    return slug or "untitled"


def create_http_client() -> httpx.Client:
    timeout = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=30.0)
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    return httpx.Client(
        follow_redirects=True,
        headers=headers,
        timeout=timeout,
    )


def polite_sleep(
    delay: float,
    *,
    sleep_fn: Callable[[float], None] = time.sleep,
    uniform_fn: Callable[[float, float], float] = random.uniform,
) -> float:
    actual_delay = max(0.1, delay + uniform_fn(0.0, 0.5 * delay))
    sleep_fn(actual_delay)
    return actual_delay

