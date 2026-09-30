"""
Rate Limiting Module for FastAPI
Implements a thread-safe sliding window rate limiter to protect sensitive endpoints
(e.g., login, password reset, registration) from brute-force and credential stuffing attacks.
"""

import time
import asyncio
from collections import defaultdict, deque
from typing import Dict, Deque, Optional
from fastapi import Request, HTTPException, status


class SlidingWindowRateLimiter:
    """
    In-memory sliding window rate limiter.
    Stores timestamps of recent requests per key and purges expired entries.
    """

    def __init__(self, requests_limit: int, window_seconds: int, name: str = "default"):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.name = name
        self.hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    def get_client_ip(self, request: Request) -> str:
        """
        Extract the client's real IP address, prioritizing proxy headers.
        """
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # First IP in X-Forwarded-For is the client's original IP
            return forwarded_for.split(",")[0].strip()
        
        cf_connecting_ip = request.headers.get("CF-Connecting-IP")
        if cf_connecting_ip:
            return cf_connecting_ip.strip()

        if request.client and request.client.host:
            return request.client.host

        return "127.0.0.1"

    async def check(self, request: Request, key_override: Optional[str] = None):
        """
        Enforce rate limit for the current request.
        Raises HTTP 429 if the limit is exceeded.
        """
        ip = key_override or self.get_client_ip(request)
        key = f"{self.name}:{ip}"
        now = time.time()
        window_start = now - self.window_seconds

        async with self._lock:
            timestamps = self.hits[key]
            
            # Remove timestamps outside the current window
            while timestamps and timestamps[0] <= window_start:
                timestamps.popleft()

            if len(timestamps) >= self.requests_limit:
                # Calculate time until earliest request expires
                oldest = timestamps[0]
                retry_after = max(1, int(oldest + self.window_seconds - now))
                
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many requests. Please try again in {retry_after} seconds.",
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(self.requests_limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(oldest + self.window_seconds)),
                    }
                )

            # Record this request
            timestamps.append(now)


def rate_limit(requests_limit: int, window_seconds: int, name: str = "rate_limit"):
    """
    FastAPI dependency factory for rate limiting.
    Usage:
        @router.post("/login", dependencies=[Depends(rate_limit(5, 60, "login"))])
    """
    limiter = SlidingWindowRateLimiter(requests_limit, window_seconds, name=name)

    async def dependency(request: Request):
        await limiter.check(request)

    return dependency
