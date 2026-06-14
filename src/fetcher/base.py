"""Base fetcher with retry, cache, and rate-limiting utilities."""

import time
import pickle
import hashlib
import functools
import signal
from pathlib import Path
from datetime import datetime, timedelta
from typing import Callable, Any
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import CACHE_DIR, CACHE_TTL_HOURS, MAX_RETRIES, RETRY_BACKOFF_SECONDS, REQUEST_TIMEOUT

# Set default timeout for all HTTP requests to prevent hanging on cloud
try:
    import requests
    _original_request = requests.Session.request
    def _patched_request(self, method, url, **kwargs):
        if 'timeout' not in kwargs:
            kwargs['timeout'] = REQUEST_TIMEOUT
        return _original_request(self, method, url, **kwargs)
    requests.Session.request = _patched_request
except ImportError:
    pass


def cache_key(func_name: str, *args, **kwargs) -> str:
    """Generate a unique cache key from function name and arguments."""
    raw = f"{func_name}:{args}:{sorted(kwargs.items())}"
    return hashlib.md5(raw.encode()).hexdigest()


def with_cache(func: Callable) -> Callable:
    """Decorator that caches function results to disk (pickle)."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        force_refresh = kwargs.pop("force_refresh", False)
        if not force_refresh:
            key = cache_key(func.__name__, *args, **kwargs)
            cache_path = CACHE_DIR / f"{key}.pkl"
            if cache_path.exists():
                age = time.time() - cache_path.stat().st_mtime
                if age < CACHE_TTL_HOURS * 3600:
                    try:
                        with open(cache_path, "rb") as f:
                            return pickle.load(f)
                    except (pickle.UnpicklingError, EOFError):
                        pass  # Cache corrupted, re-fetch
        result = func(*args, **kwargs)
        # Store in cache
        key = cache_key(func.__name__, *args, **kwargs)
        cache_path = CACHE_DIR / f"{key}.pkl"
        try:
            with open(cache_path, "wb") as f:
                pickle.dump(result, f)
        except Exception:
            pass  # Non-critical if caching fails
        return result
    return wrapper


def with_retry(func: Callable) -> Callable:
    """Decorator that retries function calls with exponential backoff."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF_SECONDS[min(attempt, len(RETRY_BACKOFF_SECONDS) - 1)]
                    print(f"  [Retry] {func.__name__} attempt {attempt + 1}/{MAX_RETRIES} failed: {e}. "
                          f"Waiting {wait}s...")
                    time.sleep(wait)
        raise last_error
    return wrapper


class BaseFetcher:
    """Base class for all data fetchers."""

    def __init__(self):
        self._last_request_time = 0
        self._min_interval = 0.5  # Minimum seconds between requests

    def _rate_limit(self):
        """Ensure minimum interval between API requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    @staticmethod
    def safe_float(val, default=None):
        """Safely convert a value to float."""
        if val is None:
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default
