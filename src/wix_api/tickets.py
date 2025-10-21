"""
Wix Event Tickets API V1 wrapper.

This module provides high-level methods for interacting with the Wix Event Tickets V1 API.
All endpoints validated against official Wix documentation (October 2025).

Reference: VALIDATED_ENDPOINTS.md (to be updated)
Base URL: https://www.wixapis.com/events/v1
Documentation: https://dev.wix.com/docs/rest/business-solutions/events/events-v1/ticket/list-tickets

IMPORTANT: This is the Tickets API V1, which returns individual sold tickets with payment data.
This is different from:
- Ticket Definitions (templates for ticket types)
- Guest records (which may reference tickets)
- eCommerce Orders (which don't include event tickets)
"""

import logging
from typing import Any, Dict, List, Optional

from wix_api.client import WixAPIClient
from utils.pagination import paginate_query

logger = logging.getLogger(__name__)


class TicketsAPI:
    """
    Wrapper for Wix Event Tickets API V1.

    Provides methods to query and retrieve sold ticket information, including
    buyer details, pricing, and order information.

    Example:
        >>> from wix_api.client import WixAPIClient
        >>> client = WixAPIClient.from_env()
        >>> tickets_api = TicketsAPI(client)
        >>> tickets = tickets_api.list_tickets(event_id="event-123")
    """

    def __init__(self, client: WixAPIClient):
        """
        Initialize Tickets API wrapper.

        Args:
            client: Authenticated WixAPIClient instance
        """
        self.client = client
        self.base_path = "/events/v1/tickets"

    def list_tickets(
        self,
        event_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List tickets with optional filtering by event.

        Endpoint: GET /events/v1/tickets

        NOTE: This API uses GET with query parameters, not POST like other APIs.

        Args:
            event_id: Filter by specific event ID (optional)
            limit: Number of tickets to return (default: 100, max: 100)
            offset: Offset for pagination (default: 0)

        Returns:
            Response with tickets list and pagination metadata

        Example:
            >>> tickets = tickets_api.list_tickets(event_id="event-123", limit=50)
            >>> for ticket in tickets.get('tickets', []):
            ...     print(ticket['ticketNumber'], ticket['guestFullName'])
        """
        # Build query parameters
        params: Dict[str, Any] = {
            "limit": min(limit, 100),  # API max is 100
            "offset": offset
        }

        if event_id:
            params["eventId"] = event_id

        logger.info(f"Listing tickets (event_id={event_id}, limit={limit}, offset={offset})")

        return self.client.get(self.base_path, params=params)

    def get_ticket(self, ticket_number: str) -> Dict[str, Any]:
        """
        Get individual ticket details by ticket number.

        Endpoint: GET /events/v1/tickets/{ticketNumber}

        Args:
            ticket_number: The unique ticket number

        Returns:
            Ticket details

        Example:
            >>> ticket = tickets_api.get_ticket("TKT-12345")
        """
        logger.info(f"Getting ticket: {ticket_number}")
        return self.client.get(f"{self.base_path}/{ticket_number}")

    def get_all_tickets(
        self,
        event_id: Optional[str] = None,
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Helper method to retrieve all tickets with automatic pagination.

        Automatically handles pagination to retrieve all matching tickets.

        Args:
            event_id: Filter by specific event ID (optional)
            max_results: Maximum number of results to return (None = all)

        Returns:
            List of all tickets

        Example:
            >>> all_tickets = tickets_api.get_all_tickets()
            >>> event_tickets = tickets_api.get_all_tickets(event_id="event-123")
        """
        # Need to create a wrapper function for paginate_query since list_tickets
        # uses GET params instead of POST body
        def query_func(limit: int, offset: int, **kwargs) -> Dict[str, Any]:
            return self.list_tickets(
                limit=limit,
                offset=offset,
                event_id=kwargs.get('event_id')
            )

        return paginate_query(
            query_func=query_func,
            response_key="tickets",
            limit=100,
            max_results=max_results,
            event_id=event_id
        )

    def get_tickets_by_event(
        self,
        event_id: str,
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Helper method to retrieve all tickets for a specific event.

        Alias for get_all_tickets() with event_id specified for clarity.

        Args:
            event_id: The event ID to filter by
            max_results: Maximum number of results to return (None = all)

        Returns:
            List of all tickets for the event

        Example:
            >>> tickets = tickets_api.get_tickets_by_event("event-123")
        """
        return self.get_all_tickets(event_id=event_id, max_results=max_results)

    def get_ticket_statuses(self) -> List[str]:
        """
        Get available ticket order status values.

        Based on Wix API documentation.

        Returns:
            List of order status constants
        """
        return [
            "NA_ORDER_STATUS",  # Not applicable
            "PENDING",          # Payment pending
            "PAID",            # Payment completed
            "OFFLINE_PENDING", # Offline payment pending
            "DECLINED",        # Payment declined
            "FREE"             # Free ticket
        ]
