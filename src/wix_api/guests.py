"""
Wix Event Guests API V2 wrapper.

This module provides high-level methods for interacting with the Wix Event Guests V2 API.
All endpoints validated against official Wix documentation (October 2025).

Reference: VALIDATED_ENDPOINTS.md
Base URL: https://www.wixapis.com/events/v2
Documentation: https://dev.wix.com/docs/rest/business-solutions/events/event-guests/introduction
"""

import logging
from typing import Any, Dict, List, Optional

from wix_api.client import WixAPIClient
from utils.pagination import paginate_query

logger = logging.getLogger(__name__)


class GuestsAPI:
    """
    Wrapper for Wix Event Guests API V2.

    Provides methods to query and retrieve guest information for events.

    IMPORTANT: Must include fieldsets: ["GUEST_DETAILS"] to retrieve full guest data.

    Example:
        >>> from wix_api.client import WixAPIClient
        >>> client = WixAPIClient.from_env()
        >>> guests_api = GuestsAPI(client)
        >>> guests = guests_api.query_guests(event_id="event-123")
    """

    def __init__(self, client: WixAPIClient):
        """
        Initialize Guests API wrapper.

        Args:
            client: Authenticated WixAPIClient instance
        """
        self.client = client
        self.base_path = "/events/v2/guests"

    def query_guests(
        self,
        event_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        filter_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[List[Dict[str, str]]] = None,
        include_details: bool = True
    ) -> Dict[str, Any]:
        """
        Query event guests with filtering and pagination.

        Endpoint: POST /events/v2/guests/query

        IMPORTANT: include_details=True adds fieldsets: ["GUEST_DETAILS"] to get full data.
        Without this, the response contains minimal guest information.

        Args:
            event_id: Filter by specific event ID
            limit: Number of guests to return (default: 100)
            offset: Offset for pagination (default: 0)
            filter_dict: Additional filter criteria
            sort: Sort criteria (e.g., [{"fieldName": "createdDate", "order": "ASC"}])
            include_details: Include GUEST_DETAILS fieldset (default: True)

        Returns:
            Response with guests list and paging metadata

        Example:
            >>> guests = guests_api.query_guests(
            ...     event_id="event-123",
            ...     limit=50,
            ...     include_details=True
            ... )
        """
        # Build query object
        query_obj: Dict[str, Any] = {
            "paging": {
                "limit": limit,
                "offset": offset
            }
        }

        # CRITICAL: Include fieldsets to get full guest details
        if include_details:
            query_obj["fieldsets"] = ["GUEST_DETAILS"]

        # Build filter
        filter_obj = filter_dict.copy() if filter_dict else {}

        if event_id:
            filter_obj["eventId"] = event_id

        if filter_obj:
            query_obj["filter"] = filter_obj

        if sort:
            query_obj["sort"] = sort

        # Wrap in query object
        payload = {"query": query_obj}

        logger.info(f"Querying guests (event_id={event_id}, limit={limit}, offset={offset})")
        if not include_details:
            logger.warning("Querying guests without GUEST_DETAILS fieldset - response will be minimal")

        return self.client.post(f"{self.base_path}/query", json=payload)

    def get_guest(self, guest_id: str, include_details: bool = True) -> Dict[str, Any]:
        """
        Get individual guest details by ID.

        Endpoint: GET /events/v2/guests/{guestId}

        Args:
            guest_id: The guest ID
            include_details: Include GUEST_DETAILS fieldset (default: True)

        Returns:
            Guest details

        Example:
            >>> guest = guests_api.get_guest("guest-123")
        """
        logger.info(f"Getting guest: {guest_id}")

        params = {}
        if include_details:
            params["fieldsets"] = "GUEST_DETAILS"

        return self.client.get(f"{self.base_path}/{guest_id}", params=params)

    def get_all_guests_for_event(
        self,
        event_id: str,
        include_details: bool = True,
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Helper method to retrieve all guests for a specific event using pagination.

        Automatically handles pagination to retrieve all guests for an event.

        Args:
            event_id: The event ID
            include_details: Include GUEST_DETAILS fieldset (default: True)
            max_results: Maximum number of results to return (None = all)

        Returns:
            List of all guests for the event

        Example:
            >>> all_guests = guests_api.get_all_guests_for_event("event-123")
        """
        return paginate_query(
            query_func=self.query_guests,
            response_key="guests",
            limit=100,
            max_results=max_results,
            event_id=event_id,
            include_details=include_details
        )

    def get_all_guests(
        self,
        filter_dict: Optional[Dict[str, Any]] = None,
        include_details: bool = True,
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Helper method to retrieve all guests with optional filtering using pagination.

        Automatically handles pagination to retrieve all matching guests.

        Args:
            filter_dict: Filter criteria (e.g., {"status": "ATTENDING"})
            include_details: Include GUEST_DETAILS fieldset (default: True)
            max_results: Maximum number of results to return (None = all)

        Returns:
            List of all guests

        Example:
            >>> all_guests = guests_api.get_all_guests(
            ...     filter_dict={"checkInStatus": "CHECKED_IN"}
            ... )
        """
        return paginate_query(
            query_func=self.query_guests,
            response_key="guests",
            limit=100,
            max_results=max_results,
            filter_dict=filter_dict,
            include_details=include_details
        )

    def get_guest_types(self) -> List[str]:
        """
        Get available guest types.

        Guest types according to Wix API documentation:
        - RSVP: An invited guest, no ticket necessary
        - BUYER: The guest who bought the tickets
        - TICKET_HOLDER: The guest for whom the ticket was bought

        Returns:
            List of guest type constants
        """
        return ["RSVP", "BUYER", "TICKET_HOLDER"]

    def get_check_in_statuses(self) -> List[str]:
        """
        Get available check-in status values.

        Returns:
            List of check-in status constants
        """
        return ["CHECKED_IN", "NOT_CHECKED_IN", "PENDING"]
