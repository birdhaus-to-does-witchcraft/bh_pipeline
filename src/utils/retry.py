"""
Retry and rate limiting utilities for API requests.

This module provides decorators and utilities for handling retries with exponential
backoff and rate limiting to respect API quotas.
"""

import time
from functools import wraps
from typing import Callable, Type, Tuple

from pyrate_limiter import Duration, Limiter, Rate
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    after_log
)
import logging
import requests


logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Simple rate limiter using timestamps to track API call frequency.

    This provides a fallback implementation that doesn't require external dependencies
    beyond basic Python, though pyrate_limiter is preferred for production use.
    """

    def __init__(self, max_calls: int, period: int):
        """
        Initialize rate limiter.

        Args:
            max_calls: Maximum number of calls allowed in the time period
            period: Time period in seconds
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = []

    def __call__(self, func: Callable) -> Callable:
        """
        Decorator to apply rate limiting to a function.

        Args:
            func: Function to rate limit

        Returns:
            Wrapped function with rate limiting
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()

            # Remove calls outside the time window
            self.calls = [call for call in self.calls if call > now - self.period]

            if len(self.calls) >= self.max_calls:
                # Need to wait until we can make another call
                sleep_time = self.period - (now - self.calls[0])
                if sleep_time > 0:
                    logger.debug(f"Rate limit reached. Sleeping for {sleep_time:.2f}s")
                    time.sleep(sleep_time)
                # Remove oldest call
                self.calls = self.calls[1:]

            # Record this call
            self.calls.append(time.time())
            return func(*args, **kwargs)

        return wrapper


class PyRateLimiter:
    """
    Rate limiter using pyrate-limiter library (production-grade).

    This is the recommended rate limiter for production use.
    """

    def __init__(self, max_calls: int, period: int):
        """
        Initialize rate limiter with pyrate-limiter.

        Args:
            max_calls: Maximum number of calls allowed in the time period
            period: Time period in seconds
        """
        self.rate = Rate(max_calls, period * Duration.SECOND)
        self.limiter = Limiter(self.rate)

    def __call__(self, func: Callable) -> Callable:
        """
        Decorator to apply rate limiting to a function.

        Args:
            func: Function to rate limit

        Returns:
            Wrapped function with rate limiting
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Acquire rate limit token (blocks until available)
            self.limiter.try_acquire("wix_api")
            return func(*args, **kwargs)

        return wrapper


def create_rate_limiter(max_calls: int = 100, period: int = 60, use_pyrate: bool = True):
    """
    Factory function to create a rate limiter.

    Args:
        max_calls: Maximum calls per period (default: 100)
        period: Period in seconds (default: 60)
        use_pyrate: Use pyrate_limiter if True, otherwise use simple implementation

    Returns:
        Rate limiter instance

    Example:
        >>> limiter = create_rate_limiter(max_calls=100, period=60)
        >>> @limiter
        ... def api_call():
        ...     # Make API request
        ...     pass
    """
    if use_pyrate:
        return PyRateLimiter(max_calls, period)
    else:
        return RateLimiter(max_calls, period)


def create_retry_decorator(
    max_attempts: int = 3,
    min_wait: int = 4,
    max_wait: int = 10,
    retry_exceptions: Tuple[Type[Exception], ...] = (
        requests.exceptions.RequestException,
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
    )
):
    """
    Create a retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time in seconds between retries
        max_wait: Maximum wait time in seconds between retries
        retry_exceptions: Tuple of exception types to retry on

    Returns:
        Configured retry decorator

    Example:
        >>> retry_decorator = create_retry_decorator(max_attempts=3)
        >>> @retry_decorator
        ... def api_call():
        ...     # Make API request
        ...     pass
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(retry_exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.DEBUG)
    )


class RetryableError(Exception):
    """Base exception for errors that should trigger a retry."""
    pass


class RateLimitError(RetryableError):
    """Exception raised when rate limit is exceeded."""
    pass


class APIError(Exception):
    """Base exception for API errors."""
    pass


class AuthenticationError(APIError):
    """Exception raised for authentication failures."""
    pass


def should_retry_request(response: requests.Response) -> bool:
    """
    Determine if a request should be retried based on response status.

    Args:
        response: HTTP response object

    Returns:
        True if request should be retried, False otherwise

    Example:
        >>> response = requests.get("https://api.example.com")
        >>> if should_retry_request(response):
        ...     # Retry logic
        ...     pass
    """
    # Retry on specific status codes
    retryable_status_codes = {
        429,  # Too Many Requests (rate limit)
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
    }

    return response.status_code in retryable_status_codes


def handle_rate_limit_response(response: requests.Response) -> None:
    """
    Handle rate limit response by waiting if necessary.

    Args:
        response: HTTP response object

    Raises:
        RateLimitError: If rate limit is exceeded

    Example:
        >>> response = requests.get("https://api.example.com")
        >>> try:
        ...     handle_rate_limit_response(response)
        ... except RateLimitError:
        ...     # Handle rate limit
        ...     pass
    """
    if response.status_code == 429:
        # Check for Retry-After header
        retry_after = response.headers.get('Retry-After')
        if retry_after:
            try:
                wait_time = int(retry_after)
                logger.warning(f"Rate limit exceeded. Waiting {wait_time}s as per Retry-After header")
                time.sleep(wait_time)
            except ValueError:
                # Retry-After might be a date, fallback to default wait
                logger.warning("Rate limit exceeded. Waiting 60s (default)")
                time.sleep(60)
        else:
            logger.warning("Rate limit exceeded. Waiting 60s (no Retry-After header)")
            time.sleep(60)

        raise RateLimitError("API rate limit exceeded")
