"""
Rate Limiting Utilities
Simple in-memory rate limiter for API protection
"""
import time
from typing import Dict, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from app.core.logging_config import get_logger
from app.core.exceptions import RateLimitExceededError

logger = get_logger(__name__)


@dataclass
class RateLimitBucket:
    """
    Token bucket for rate limiting

    Uses token bucket algorithm:
    - Bucket has max capacity (max_tokens)
    - Tokens refill at constant rate (refill_rate per second)
    - Each request consumes tokens
    - Request allowed only if enough tokens available
    """
    max_tokens: int
    refill_rate: float  # tokens per second
    tokens: float = field(default=0)
    last_refill: float = field(default_factory=time.time)

    def __post_init__(self):
        """Initialize with full bucket"""
        if self.tokens == 0:
            self.tokens = self.max_tokens

    def refill(self) -> None:
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill

        # Calculate tokens to add
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
        self.last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens consumed, False if insufficient tokens
        """
        self.refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Calculate wait time until tokens available

        Args:
            tokens: Number of tokens needed

        Returns:
            Wait time in seconds (0 if tokens available)
        """
        self.refill()

        if self.tokens >= tokens:
            return 0.0

        tokens_needed = tokens - self.tokens
        wait_time = tokens_needed / self.refill_rate
        return wait_time


class RateLimiter:
    """
    In-memory rate limiter using token bucket algorithm

    Features:
    - Per-key rate limiting (e.g., per user, per IP, per company)
    - Configurable limits and time windows
    - Automatic cleanup of old buckets
    - Thread-safe
    """

    def __init__(
        self,
        max_requests: int = 100,
        time_window: int = 60,
        cleanup_interval: int = 300
    ):
        """
        Initialize rate limiter

        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds
            cleanup_interval: Interval for cleaning up old buckets (seconds)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.refill_rate = max_requests / time_window

        self.buckets: Dict[str, RateLimitBucket] = {}
        self.lock = Lock()
        self.last_cleanup = time.time()
        self.cleanup_interval = cleanup_interval

        logger.info(
            f"Initialized RateLimiter: {max_requests} requests per {time_window}s "
            f"(~{self.refill_rate:.2f} req/s)"
        )

    def check_rate_limit(
        self,
        key: str,
        tokens: int = 1,
        raise_on_limit: bool = True
    ) -> Tuple[bool, Optional[float]]:
        """
        Check if request is within rate limit

        Args:
            key: Unique identifier (user_id, IP, company_id, etc.)
            tokens: Number of tokens to consume (default: 1)
            raise_on_limit: Raise exception if rate limit exceeded

        Returns:
            Tuple of (allowed, retry_after_seconds)

        Raises:
            RateLimitExceededError: If rate limit exceeded and raise_on_limit=True
        """
        with self.lock:
            # Cleanup old buckets periodically
            self._cleanup_if_needed()

            # Get or create bucket for key
            if key not in self.buckets:
                self.buckets[key] = RateLimitBucket(
                    max_tokens=self.max_requests,
                    refill_rate=self.refill_rate
                )

            bucket = self.buckets[key]

            # Try to consume tokens
            allowed = bucket.consume(tokens)

            if allowed:
                logger.debug(
                    f"Rate limit OK for {key}: {bucket.tokens:.2f}/{self.max_requests} tokens remaining"
                )
                return True, None

            # Calculate retry after
            retry_after = bucket.get_wait_time(tokens)
            logger.warning(
                f"Rate limit exceeded for {key}: retry after {retry_after:.2f}s"
            )

            if raise_on_limit:
                raise RateLimitExceededError(
                    f"Rate limit exceeded. Try again in {retry_after:.1f} seconds",
                    {
                        "key": key,
                        "retry_after": retry_after,
                        "limit": self.max_requests,
                        "window": self.time_window
                    }
                )

            return False, retry_after

    def reset(self, key: str) -> None:
        """
        Reset rate limit for a specific key

        Args:
            key: Key to reset
        """
        with self.lock:
            if key in self.buckets:
                del self.buckets[key]
                logger.info(f"Reset rate limit for {key}")

    def get_remaining(self, key: str) -> int:
        """
        Get remaining requests for a key

        Args:
            key: Key to check

        Returns:
            Number of remaining requests
        """
        with self.lock:
            if key not in self.buckets:
                return self.max_requests

            bucket = self.buckets[key]
            bucket.refill()
            return int(bucket.tokens)

    def _cleanup_if_needed(self) -> None:
        """Clean up old buckets if cleanup interval has passed"""
        now = time.time()

        if now - self.last_cleanup < self.cleanup_interval:
            return

        # Remove buckets that are full (inactive for long time)
        keys_to_remove = [
            key
            for key, bucket in self.buckets.items()
            if bucket.tokens >= self.max_requests and
               (now - bucket.last_refill) > self.cleanup_interval
        ]

        for key in keys_to_remove:
            del self.buckets[key]

        if keys_to_remove:
            logger.info(f"Cleaned up {len(keys_to_remove)} inactive rate limit buckets")

        self.last_cleanup = now


class CompositeLimiter:
    """
    Composite rate limiter with multiple limits

    Example: Both per-user and global limits
    - User: 100 requests/minute
    - Global: 10000 requests/minute
    """

    def __init__(self, limiters: Dict[str, RateLimiter]):
        """
        Initialize composite limiter

        Args:
            limiters: Dict of limiter_name -> RateLimiter
        """
        self.limiters = limiters
        logger.info(f"Initialized CompositeLimiter with {len(limiters)} limiters")

    def check_rate_limit(
        self,
        keys: Dict[str, str],
        tokens: int = 1,
        raise_on_limit: bool = True
    ) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Check all rate limits

        Args:
            keys: Dict of limiter_name -> key
            tokens: Number of tokens to consume
            raise_on_limit: Raise exception if any limit exceeded

        Returns:
            Tuple of (allowed, limiter_name, retry_after)

        Raises:
            RateLimitExceededError: If any rate limit exceeded and raise_on_limit=True
        """
        for limiter_name, limiter in self.limiters.items():
            key = keys.get(limiter_name)
            if key is None:
                continue

            allowed, retry_after = limiter.check_rate_limit(
                key=key,
                tokens=tokens,
                raise_on_limit=raise_on_limit
            )

            if not allowed:
                return False, limiter_name, retry_after

        return True, None, None


# Global rate limiters (can be imported and reused)
# These are initialized with default values and can be configured via settings

# API rate limiter: 60 requests per minute per user
api_limiter = RateLimiter(
    max_requests=60,
    time_window=60,
    cleanup_interval=300
)

# Knowledge upload limiter: 5 uploads per hour per company
knowledge_upload_limiter = RateLimiter(
    max_requests=5,
    time_window=3600,
    cleanup_interval=1800
)

# Call initiation limiter: 100 calls per hour per company
call_limiter = RateLimiter(
    max_requests=100,
    time_window=3600,
    cleanup_interval=1800
)


# Export public classes and instances
__all__ = [
    "RateLimiter",
    "CompositeLimiter",
    "api_limiter",
    "knowledge_upload_limiter",
    "call_limiter"
]
