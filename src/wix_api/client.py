"""
Wix API Client - Core HTTP client for interacting with Wix REST APIs.

This module provides the base client class for making authenticated requests to
Wix APIs with rate limiting, retry logic, and error handling.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.config import PipelineConfig, WixAPIConfig
from utils.retry import (
    create_rate_limiter,
    create_retry_decorator,
    handle_rate_limit_response,
    should_retry_request,
    APIError,
    AuthenticationError,
    RateLimitError
)


logger = logging.getLogger(__name__)


class WixAPIClient:
    """
    Core client for making authenticated requests to Wix REST APIs.

    This class handles:
    - Authentication with API keys
    - Rate limiting to respect API quotas
    - Automatic retries with exponential backoff
    - Error handling and logging
    - Session management with connection pooling

    Example:
        >>> client = WixAPIClient.from_env()
        >>> events = client.get("/v3/events/query", json={"query": {}})
    """

    def __init__(
        self,
        api_key: str,
        account_id: Optional[str] = None,
        site_id: Optional[str] = None,
        base_url: str = "https://www.wixapis.com",
        max_calls: int = 100,
        period: int = 60,
        max_retries: int = 3
    ):
        """
        Initialize Wix API client.

        Args:
            api_key: Wix API key for authentication
            account_id: Optional Wix account ID
            site_id: Optional Wix site ID
            base_url: Base URL for Wix API (default: https://www.wixapis.com)
            max_calls: Maximum API calls per period for rate limiting
            period: Time period in seconds for rate limiting
            max_retries: Maximum number of retry attempts
        """
        self.api_key = api_key
        self.account_id = account_id
        self.site_id = site_id
        self.base_url = base_url.rstrip('/')

        # Create session with connection pooling
        self.session = requests.Session()

        # Configure session with retry strategy for connection errors
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        # Set standard headers for all requests
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # Add optional context headers
        if account_id:
            headers["wix-account-id"] = account_id
        if site_id:
            headers["wix-site-id"] = site_id

        self.session.headers.update(headers)

        # Set up rate limiting
        self.rate_limiter = create_rate_limiter(max_calls=max_calls, period=period)

        # Set up retry decorator
        self.retry_decorator = create_retry_decorator(max_attempts=max_retries)

        logger.info(f"Initialized Wix API client (base_url={base_url})")

    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "WixAPIClient":
        """
        Create client from environment variables.

        Args:
            env_file: Path to .env file (optional)

        Returns:
            WixAPIClient instance

        Example:
            >>> client = WixAPIClient.from_env()
            >>> # Or with custom env file
            >>> client = WixAPIClient.from_env(".env.production")
        """
        config = PipelineConfig.from_env(env_file)
        return cls.from_config(config)

    @classmethod
    def from_config(cls, config: PipelineConfig) -> "WixAPIClient":
        """
        Create client from configuration object.

        Args:
            config: PipelineConfig instance

        Returns:
            WixAPIClient instance

        Example:
            >>> config = PipelineConfig.from_env()
            >>> client = WixAPIClient.from_config(config)
        """
        return cls(
            api_key=config.wix_api.api_key,
            account_id=config.wix_api.account_id,
            site_id=config.wix_api.site_id,
            base_url=config.wix_api.base_url,
            max_calls=config.rate_limit.max_calls,
            period=config.rate_limit.period,
            max_retries=config.retry.max_attempts
        )

    def _build_url(self, endpoint: str) -> str:
        """
        Build full URL from endpoint path.

        Args:
            endpoint: API endpoint path (e.g., "/v3/events/query")

        Returns:
            Full URL string
        """
        # Ensure endpoint starts with /
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint

        return f"{self.base_url}{endpoint}"

    @create_retry_decorator(max_attempts=3, min_wait=4, max_wait=10)
    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make authenticated HTTP request with rate limiting and error handling.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint path
            **kwargs: Additional arguments to pass to requests (json, params, etc.)

        Returns:
            JSON response as dictionary

        Raises:
            AuthenticationError: If authentication fails
            RateLimitError: If rate limit is exceeded and retry fails
            APIError: For other API errors
        """
        # Apply rate limiting
        # Note: We're not using the decorator pattern here to have more control
        # self.rate_limiter would need to be applied at method level

        url = self._build_url(endpoint)

        logger.debug(f"Making {method} request to {endpoint}")

        try:
            response = self.session.request(method, url, **kwargs)

            # Check for authentication errors
            if response.status_code == 401:
                logger.error("Authentication failed - check API key")
                raise AuthenticationError("Invalid API key or authentication failed")

            # Handle rate limiting
            if response.status_code == 429:
                handle_rate_limit_response(response)
                # This will raise RateLimitError which triggers retry

            # Check if we should retry
            if should_retry_request(response):
                logger.warning(f"Received {response.status_code} status, will retry")
                response.raise_for_status()

            # Raise for other HTTP errors
            response.raise_for_status()

            # Parse JSON response
            try:
                data = response.json()
                logger.debug(f"Successfully received response from {endpoint}")
                return data
            except ValueError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                raise APIError(f"Invalid JSON response: {e}")

        except requests.exceptions.HTTPError as e:
            # Log response body for debugging
            try:
                error_body = e.response.text
                logger.error(f"Request failed for {endpoint}: {e}")
                logger.error(f"Response body: {error_body}")
            except:
                logger.error(f"Request failed for {endpoint}: {e}")
            raise APIError(f"Request failed: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {endpoint}: {e}")
            raise APIError(f"Request failed: {e}")

    def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make GET request.

        Args:
            endpoint: API endpoint path
            **kwargs: Additional request parameters

        Returns:
            JSON response as dictionary
        """
        return self._request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make POST request.

        Args:
            endpoint: API endpoint path
            **kwargs: Additional request parameters (typically json={...})

        Returns:
            JSON response as dictionary
        """
        return self._request("POST", endpoint, **kwargs)

    def patch(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make PATCH request.

        Args:
            endpoint: API endpoint path
            **kwargs: Additional request parameters

        Returns:
            JSON response as dictionary
        """
        return self._request("PATCH", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make DELETE request.

        Args:
            endpoint: API endpoint path
            **kwargs: Additional request parameters

        Returns:
            JSON response as dictionary
        """
        return self._request("DELETE", endpoint, **kwargs)

    def close(self):
        """Close the session and clean up resources."""
        self.session.close()
        logger.info("Wix API client session closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures session is closed."""
        self.close()
        return False
