"""Versioned cache-key namespace for product search results.

Rather than tracking which cached search pages reference which product
(unbounded, error-prone), every cached search response is stored under a
key that includes a version number. Any Product or Inventory write bumps
that version, which instantly makes every previously cached page
unreachable — a form of invalidation-by-abandonment that's O(1) and
correct by construction. See openspec design.md Decision 4.
"""

import hashlib

from django.core.cache import cache

_VERSION_KEY = "search:cache-version"


def _get_version() -> int:
    version = cache.get(_VERSION_KEY)
    if version is None:
        version = 1
        cache.set(_VERSION_KEY, version, timeout=None)
    return version


def bump_search_cache_version() -> None:
    try:
        cache.incr(_VERSION_KEY)
    except ValueError:
        cache.set(_VERSION_KEY, 1, timeout=None)


def build_search_cache_key(query_params: dict) -> str:
    normalized = "&".join(f"{k}={v}" for k, v in sorted(query_params.items()))
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"search:v{_get_version()}:{digest}"
