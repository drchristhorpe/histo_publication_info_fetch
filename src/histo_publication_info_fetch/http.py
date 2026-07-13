import hashlib
import json
from pathlib import Path

import requests


def get_cache_key(url: str) -> str:
    """Generate a hex cache key from a URL."""
    return hashlib.sha256(url.encode()).hexdigest()


def cached_get(
    url: str, cache_dir: Path, refresh: bool = False, timeout: int = 30
) -> str:
    """
    Fetch URL with disk caching.

    Args:
        url: URL to fetch.
        cache_dir: Directory for cached responses.
        refresh: If True, bypass cache and re-fetch.
        timeout: Request timeout in seconds.

    Returns:
        Response text.

    Raises:
        requests.RequestException: If the request fails.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = get_cache_key(url)
    cache_file = cache_dir / cache_key

    if not refresh and cache_file.exists():
        return cache_file.read_text(encoding="utf-8")

    headers = {
        "User-Agent": "histo-publication-info-fetch/0.1.0 (+https://github.com/drchristhorpe/histo_publication_info_fetch)"
    }
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    text = response.text
    cache_file.write_text(text, encoding="utf-8")
    return text
