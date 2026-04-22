"""
Wix Automations API V2 wrapper.

Provides high-level methods for querying automation configurations.

NOTE on endpoint URL:
The Wix Automations API lives on `manage.wix.com/automations-service/...`
NOT on the standard `www.wixapis.com` host. Wix's own docs are inconsistent:
the schema lists `https://www.wixapis.com/v2/automations/query` but that URL
returns 404. The cURL examples (and what actually works) use:
    https://manage.wix.com/automations-service/v2/automations/query

We pass the absolute URL into the client; `WixAPIClient._build_url()` passes
absolute URLs through unchanged.

Documentation: https://dev.wix.com/docs/api-reference/business-management/automations/automations/automations-v2/query-automations
"""

import logging
from typing import Any, Dict, List, Optional

from wix_api.client import WixAPIClient
from utils.pagination import paginate_cursor_query

logger = logging.getLogger(__name__)

# Absolute URL because this endpoint isn't on www.wixapis.com
AUTOMATIONS_QUERY_URL = "https://manage.wix.com/automations-service/v2/automations/query"


class AutomationsAPI:
    """
    Wrapper for Wix Automations API V2.

    Returns automation configurations (triggers, actions, status).
    Only returns automations from apps installed on the site.
    Uses cursor-based pagination.

    Example:
        >>> client = WixAPIClient.from_env()
        >>> automations_api = AutomationsAPI(client)
        >>> automations = automations_api.get_all_automations()
    """

    def __init__(self, client: WixAPIClient):
        self.client = client
        self.base_path = AUTOMATIONS_QUERY_URL

    def query_automations(
        self,
        filter_dict: Optional[Dict[str, Any]] = None,
        cursor: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Query automations with cursor pagination.

        Endpoint: POST /v2/automations/query

        Args:
            filter_dict: Optional filter criteria
            cursor: Cursor token for pagination (None for first page)
            limit: Number of items per page

        Returns:
            Response with automations list and pagingMetadata
        """
        query: Dict[str, Any] = {
            "cursorPaging": {"limit": limit},
        }
        if cursor:
            query["cursorPaging"]["cursor"] = cursor
        if filter_dict:
            query["filter"] = filter_dict

        payload = {"query": query}

        logger.info(f"Querying automations (limit={limit})")
        return self.client.post(self.base_path, json=payload)

    def get_all_automations(
        self,
        filter_dict: Optional[Dict[str, Any]] = None,
        max_results: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all automations using cursor pagination.

        Args:
            filter_dict: Optional filter criteria
            max_results: Maximum results to return (None = all)

        Returns:
            List of all automations
        """
        def query_func(cursor: Optional[str], limit: int, **kwargs) -> Dict[str, Any]:
            return self.query_automations(
                filter_dict=filter_dict,
                cursor=cursor,
                limit=limit,
            )

        return paginate_cursor_query(
            query_func=query_func,
            response_key="automations",
            limit=100,
            max_results=max_results,
        )
