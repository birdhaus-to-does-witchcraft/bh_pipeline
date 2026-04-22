"""
Wix Ticket Definitions API V3 wrapper.

A Ticket Definition is a reusable configuration (template) for the ticket types
available for a ticketed event. Ticket Definitions describe pricing, fee handling,
sale period, and inventory limits. Sold Tickets reference a Ticket Definition by ID.

Base URL: https://www.wixapis.com/events/v3
Documentation: https://dev.wix.com/docs/api-reference/business-solutions/events/event-management/ticket-definitions-v3
"""

import logging
from typing import Any, Dict, List, Optional

from wix_api.client import WixAPIClient
from utils.pagination import paginate_query

logger = logging.getLogger(__name__)


class TicketDefinitionsAPI:
    """
    Wrapper for Wix Ticket Definitions V3 API.

    Use the SALES_DETAILS fieldset to get sold/unsold counts and sale status.

    Example:
        >>> client = WixAPIClient.from_env()
        >>> defs_api = TicketDefinitionsAPI(client)
        >>> definitions = defs_api.get_all_ticket_definitions(fieldsets=["SALES_DETAILS"])
    """

    def __init__(self, client: WixAPIClient):
        self.client = client
        self.base_path = "/events/v3/ticket-definitions"

    def query_ticket_definitions(
        self,
        limit: int = 100,
        offset: int = 0,
        filter_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[List[Dict[str, str]]] = None,
        fieldsets: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Query ticket definitions with pagination.

        Endpoint: POST /events/v3/ticket-definitions/query

        Args:
            limit: Items per page (default 100)
            offset: Pagination offset
            filter_dict: Filter criteria (e.g. {"eventId": "..."})
            sort: Sort criteria
            fieldsets: Optional fieldsets (e.g. ["SALES_DETAILS", "EVENT_DETAILS"])

        Returns:
            Response with ticketDefinitions list and pagination metadata
        """
        query: Dict[str, Any] = {
            "paging": {"limit": limit, "offset": offset},
        }
        if filter_dict:
            query["filter"] = filter_dict
        if sort:
            query["sort"] = sort
        if fieldsets:
            query["fieldsets"] = fieldsets

        payload = {"query": query}

        logger.info(
            f"Querying ticket definitions (limit={limit}, offset={offset}, fieldsets={fieldsets})"
        )
        return self.client.post(f"{self.base_path}/query", json=payload)

    def get_ticket_definition(
        self,
        definition_id: str,
        fieldsets: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get a single ticket definition by ID.

        Endpoint: GET /events/v3/ticket-definitions/{id}
        """
        params: Dict[str, Any] = {}
        if fieldsets:
            params["fieldsets"] = fieldsets

        logger.info(f"Getting ticket definition: {definition_id}")
        return self.client.get(f"{self.base_path}/{definition_id}", params=params)

    def get_all_ticket_definitions(
        self,
        filter_dict: Optional[Dict[str, Any]] = None,
        fieldsets: Optional[List[str]] = None,
        max_results: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all ticket definitions using pagination.

        Args:
            filter_dict: Optional filter criteria
            fieldsets: Optional fieldsets (default: ["SALES_DETAILS"] for sold counts)
            max_results: Maximum results to return (None = all)

        Returns:
            List of all ticket definitions
        """
        if fieldsets is None:
            fieldsets = ["SALES_DETAILS"]

        return paginate_query(
            query_func=self.query_ticket_definitions,
            response_key="ticketDefinitions",
            limit=100,
            max_results=max_results,
            filter_dict=filter_dict,
            fieldsets=fieldsets,
        )
