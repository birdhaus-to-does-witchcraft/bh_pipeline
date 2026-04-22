"""
Wix Coupons API V2 wrapper.

Provides high-level methods for querying coupon data.

Base URL: https://www.wixapis.com/stores/v2
Documentation: https://dev.wix.com/docs/rest/business-management/marketing/coupons/coupons/query-coupons
"""

import json
import logging
from typing import Any, Dict, List, Optional

from wix_api.client import WixAPIClient
from utils.pagination import paginate_query

logger = logging.getLogger(__name__)


class CouponsAPI:
    """
    Wrapper for Wix Coupons API V2.

    Note: This API uses JSON-encoded strings for filter and sort parameters,
    which is a Wix-specific quirk.

    Example:
        >>> client = WixAPIClient.from_env()
        >>> coupons_api = CouponsAPI(client)
        >>> coupons = coupons_api.get_all_coupons()
    """

    def __init__(self, client: WixAPIClient):
        self.client = client
        self.base_path = "/stores/v2/coupons"

    def query_coupons(
        self,
        limit: int = 100,
        offset: int = 0,
        filter_str: Optional[str] = None,
        sort_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Query coupons with pagination.

        Endpoint: POST /stores/v2/coupons/query

        Note: filter and sort are JSON-encoded strings, not objects.

        Args:
            limit: Number of coupons per page (max 100)
            offset: Pagination offset
            filter_str: JSON-encoded filter string (e.g. '{"expired":"true"}')
            sort_str: JSON-encoded sort string (e.g. '[{"dateCreated":"asc"}]')

        Returns:
            Response with coupons list and pagination metadata
        """
        query: Dict[str, Any] = {
            "paging": {"limit": limit, "offset": offset},
        }
        if filter_str:
            query["filter"] = filter_str
        if sort_str:
            query["sort"] = sort_str

        payload = {"query": query}

        logger.info(f"Querying coupons (limit={limit}, offset={offset})")
        return self.client.post(f"{self.base_path}/query", json=payload)

    def get_coupon(self, coupon_id: str) -> Dict[str, Any]:
        """
        Get coupon by ID.

        Endpoint: GET /stores/v2/coupons/{id}
        """
        logger.info(f"Getting coupon: {coupon_id}")
        return self.client.get(f"{self.base_path}/{coupon_id}")

    def get_all_coupons(
        self,
        include_expired: bool = True,
        max_results: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all coupons using pagination.

        When include_expired is True, makes two passes (active + expired)
        since the expired filter excludes active coupons.

        Args:
            include_expired: Include expired coupons (default: True)
            max_results: Maximum results to return (None = all)

        Returns:
            List of all coupons
        """
        def _fetch_page(limit: int, offset: int, **kwargs) -> Dict[str, Any]:
            return self.query_coupons(
                limit=limit,
                offset=offset,
                filter_str=kwargs.get("filter_str"),
            )

        # Fetch active coupons
        logger.info("Fetching active coupons...")
        active = paginate_query(
            query_func=_fetch_page,
            response_key="coupons",
            limit=100,
            max_results=max_results,
        )
        logger.info(f"Retrieved {len(active)} active coupons")

        if not include_expired:
            return active

        # Fetch expired coupons
        logger.info("Fetching expired coupons...")
        expired = paginate_query(
            query_func=_fetch_page,
            response_key="coupons",
            limit=100,
            max_results=max_results,
            filter_str=json.dumps({"expired": "true"}),
        )
        logger.info(f"Retrieved {len(expired)} expired coupons")

        all_coupons = active + expired
        logger.info(f"Total coupons: {len(all_coupons)}")
        return all_coupons
