"""
backend/services/auth_rate_limiter.py — In-memory sliding window rate limiter.
Prevents credential-stuffing, brute-force login attempts, and registration spam.
"""
import time
import threading
from typing import Dict, List
from fastapi import Request, HTTPException, status

class AuthRateLimiter:
    _lock = threading.Lock()
    _records: Dict[str, List[float]] = {}
    _enabled: bool = True

    @classmethod
    def set_enabled(cls, enabled: bool) -> None:
        with cls._lock:
            cls._enabled = enabled

    @classmethod
    def reset(cls) -> None:
        """Clears all tracking history (used in test setup/teardown)."""
        with cls._lock:
            cls._records.clear()

    @classmethod
    def check(cls, key: str, max_attempts: int, window_seconds: int) -> bool:
        """
        Returns True if the request is within allowable rate limit; False otherwise.
        """
        if not cls._enabled:
            return True

        now = time.time()
        cutoff = now - window_seconds

        with cls._lock:
            timestamps = cls._records.get(key, [])
            # Purge expired entries
            valid_timestamps = [t for t in timestamps if t > cutoff]

            if len(valid_timestamps) >= max_attempts:
                cls._records[key] = valid_timestamps
                return False

            valid_timestamps.append(now)
            cls._records[key] = valid_timestamps
            return True


def get_client_ip(request: Request) -> str:
    """Safely extracts client IP, respecting X-Forwarded-For if behind a proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def enforce_rate_limit(
    request: Request,
    endpoint: str,
    identifier: str = "",
    max_attempts: int = 10,
    window_seconds: int = 60,
    error_message: str = "Too many requests. Please try again in a few moments.",
) -> None:
    """Enforces rate limiting or raises HTTPException(429)."""
    ip = get_client_ip(request)
    composite_key = f"{endpoint}:{ip}"
    if identifier:
        composite_key += f":{identifier.lower().strip()}"

    if not AuthRateLimiter.check(composite_key, max_attempts, window_seconds):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=error_message,
        )
