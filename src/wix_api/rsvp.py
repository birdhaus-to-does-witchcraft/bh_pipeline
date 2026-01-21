"""
Wix RSVP API V2 wrapper.

This module provides high-level methods for interacting with the Wix RSVP V2 API.
All endpoints validated against official Wix documentation (October 2025).

Reference: VALIDATED_ENDPOINTS.md
Base URL: https://www.wixapis.com/events/v2
Documentation: https://dev.wix.com/docs/rest/business-solutions/events/rsvp-v2/introduction
"""

import logging
from typing import Any, Dict, List, Optional

from wix_api.client import WixAPIClient

logger = logging.getLogger(__name__)


class RSVPAPI:
    """
    Wrapper for Wix RSVP API V2.

    Provides methods to manage RSVPs, check-ins, and guest lists for RSVP events.

    Example:
        >>> from wix_api.client import WixAPIClient
        >>> client = WixAPIClient.from_env()
        >>> rsvp_api = RSVPAPI(client)
        >>> rsvps = rsvp_api.query_rsvps(event_id="event-123")
    """

    def __init__(self, client: WixAPIClient):
        """
        Initialize RSVP API wrapper.

        Args:
            client: Authenticated WixAPIClient instance
        """
        self.client = client
        self.base_path = "/events/v2/rsvps"

    def query_rsvps(
        self,
        event_id: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
        filter_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Query RSVPs with filtering and pagination.

        Endpoint: POST /events/v2/rsvps/query

        Args:
            event_id: Filter by specific event ID
            limit: Number of RSVPs to return (default: 1000)
            offset: Offset for pagination (default: 0)
            filter_dict: Additional filter criteria
            sort: Sort criteria (e.g., [{"fieldName": "createdDate", "order": "ASC"}])

        Returns:
            Response with RSVPs list and paging metadata

        Example:
            >>> rsvps = rsvp_api.query_rsvps(
            ...     event_id="event-123",
            ...     filter_dict={"rsvpStatus": "YES"}
            ... )
        """
        payload: Dict[str, Any] = {
            "paging": {
                "limit": limit,
                "offset": offset
            }
        }

        # Build filter
        filter_obj = filter_dict.copy() if filter_dict else {}

        if event_id:
            filter_obj["eventId"] = event_id

        if filter_obj:
            payload["filter"] = filter_obj

        if sort:
            payload["sort"] = sort

        logger.info(f"Querying RSVPs (event_id={event_id}, limit={limit}, offset={offset})")
        return self.client.post(f"{self.base_path}/query", json=payload)

    def search_rsvps(
        self,
        search: Dict[str, Any],
        limit: int = 1000,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search RSVPs with advanced query capabilities.

        Endpoint: POST /events/v2/rsvps/search

        Args:
            search: Search query with filters and aggregations
            limit: Number of RSVPs to return (default: 1000)
            offset: Offset for pagination (default: 0)

        Returns:
            Response with RSVPs list and paging metadata

        Example:
            >>> search_query = {
            ...     "filter": {"eventId": "event-123"},
            ...     "sort": [{"fieldName": "createdDate", "order": "DESC"}]
            ... }
            >>> rsvps = rsvp_api.search_rsvps(search_query)
        """
        payload = {
            "search": search,
            "paging": {
                "limit": limit,
                "offset": offset
            }
        }

        logger.info(f"Searching RSVPs (limit={limit}, offset={offset})")
        return self.client.post(f"{self.base_path}/search", json=payload)

    def count_rsvps(self, filter_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Count RSVPs by filter.

        Endpoint: POST /events/v2/rsvps/count

        Args:
            filter_dict: Filter criteria

        Returns:
            Count of matching RSVPs

        Example:
            >>> count = rsvp_api.count_rsvps({"eventId": "event-123", "rsvpStatus": "YES"})
        """
        payload = {}
        if filter_dict:
            payload["filter"] = filter_dict

        logger.info("Counting RSVPs")
        return self.client.post(f"{self.base_path}/count", json=payload)

    def get_rsvp(self, rsvp_id: str) -> Dict[str, Any]:
        """
        Get RSVP by ID.

        Endpoint: GET /events/v2/rsvps/{rsvpId}

        Args:
            rsvp_id: The RSVP ID

        Returns:
            RSVP details

        Example:
            >>> rsvp = rsvp_api.get_rsvp("rsvp-123")
        """
        logger.info(f"Getting RSVP: {rsvp_id}")
        return self.client.get(f"{self.base_path}/{rsvp_id}")

    def create_rsvp(self, rsvp_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new RSVP.

        Endpoint: POST /events/v2/rsvps

        Args:
            rsvp_data: RSVP details (eventId, contactId, rsvpStatus, etc.)

        Returns:
            Created RSVP details

        Example:
            >>> rsvp_data = {
            ...     "eventId": "event-123",
            ...     "contactId": "contact-456",
            ...     "rsvpStatus": "YES",
            ...     "guestNames": ["John Doe"],
            ...     "additionalGuests": 0
            ... }
            >>> rsvp = rsvp_api.create_rsvp(rsvp_data)
        """
        logger.info("Creating new RSVP")
        return self.client.post(self.base_path, json=rsvp_data)

    def update_rsvp(self, rsvp_id: str, rsvp_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing RSVP.

        Endpoint: PATCH /events/v2/rsvps/{rsvpId}

        Args:
            rsvp_id: The RSVP ID
            rsvp_data: RSVP fields to update

        Returns:
            Updated RSVP details

        Example:
            >>> updates = {"rsvpStatus": "NO"}
            >>> rsvp = rsvp_api.update_rsvp("rsvp-123", updates)
        """
        logger.info(f"Updating RSVP: {rsvp_id}")
        return self.client.patch(f"{self.base_path}/{rsvp_id}", json=rsvp_data)

    def delete_rsvp(self, rsvp_id: str) -> Dict[str, Any]:
        """
        Delete an RSVP.

        Endpoint: DELETE /events/v2/rsvps/{rsvpId}

        Args:
            rsvp_id: The RSVP ID to delete

        Returns:
            Deletion confirmation

        Example:
            >>> result = rsvp_api.delete_rsvp("rsvp-123")
        """
        logger.info(f"Deleting RSVP: {rsvp_id}")
        return self.client.delete(f"{self.base_path}/{rsvp_id}")

    def bulk_update_rsvps(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Bulk update multiple RSVPs.

        Endpoint: POST /events/v2/rsvps/bulk-update

        Args:
            updates: Bulk update specifications

        Returns:
            Bulk operation results

        Example:
            >>> updates = {
            ...     "filter": {"eventId": "event-123"},
            ...     "set": {"rsvpStatus": "NO"}
            ... }
            >>> result = rsvp_api.bulk_update_rsvps(updates)
        """
        logger.info("Bulk updating RSVPs")
        return self.client.post(f"{self.base_path}/bulk-update", json=updates)

    def bulk_delete_rsvps(self, filter_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Bulk delete RSVPs by filter.

        Endpoint: POST /events/v2/rsvps/bulk-delete

        Args:
            filter_dict: Filter criteria to select RSVPs to delete

        Returns:
            Bulk operation results

        Example:
            >>> result = rsvp_api.bulk_delete_rsvps(
            ...     {"eventId": "event-123", "rsvpStatus": "WAITING"}
            ... )
        """
        logger.info("Bulk deleting RSVPs")
        return self.client.post(f"{self.base_path}/bulk-delete", json={"filter": filter_dict})

    def check_in_rsvp(self, rsvp_id: str) -> Dict[str, Any]:
        """
        Check in RSVP guests.

        Endpoint: POST /events/v2/rsvps/{rsvpId}/check-in

        Args:
            rsvp_id: The RSVP ID to check in

        Returns:
            Updated RSVP with check-in status

        Example:
            >>> rsvp = rsvp_api.check_in_rsvp("rsvp-123")
        """
        logger.info(f"Checking in RSVP: {rsvp_id}")
        return self.client.post(f"{self.base_path}/{rsvp_id}/check-in")

    def cancel_check_in(self, rsvp_id: str) -> Dict[str, Any]:
        """
        Cancel RSVP guest check-in.

        Endpoint: POST /events/v2/rsvps/{rsvpId}/cancel-check-in

        Args:
            rsvp_id: The RSVP ID to cancel check-in

        Returns:
            Updated RSVP with check-in status removed

        Example:
            >>> rsvp = rsvp_api.cancel_check_in("rsvp-123")
        """
        logger.info(f"Canceling check-in for RSVP: {rsvp_id}")
        return self.client.post(f"{self.base_path}/{rsvp_id}/cancel-check-in")

    def get_rsvp_summary(self) -> Dict[str, Any]:
        """
        Get RSVP summary statistics.

        Endpoint: GET /events/v2/rsvps/summary

        Returns:
            RSVP summary data

        Example:
            >>> summary = rsvp_api.get_rsvp_summary()
        """
        logger.info("Getting RSVP summary")
        return self.client.get(f"{self.base_path}/summary")

    def get_all_rsvps_for_event(
        self,
        event_id: str,
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Helper method to retrieve all RSVPs for a specific event using pagination.

        Automatically handles pagination to retrieve all RSVPs for an event.

        Args:
            event_id: The event ID
            max_results: Maximum number of results to return (None = all)

        Returns:
            List of all RSVPs for the event

        Example:
            >>> all_rsvps = rsvp_api.get_all_rsvps_for_event("event-123")
        """
        all_rsvps = []
        offset = 0
        limit = 1000

        logger.info(f"Retrieving all RSVPs for event {event_id} with pagination")

        while True:
            response = self.query_rsvps(
                event_id=event_id,
                limit=limit,
                offset=offset
            )

            rsvps = response.get("rsvps", [])
            all_rsvps.extend(rsvps)

            # Check if we've reached max_results
            if max_results and len(all_rsvps) >= max_results:
                all_rsvps = all_rsvps[:max_results]
                logger.info(f"Reached max_results limit: {max_results}")
                break

            # Check if there are more pages
            paging_metadata = response.get("pagingMetadata", {})
            has_next = paging_metadata.get("hasNext", False)

            if not has_next:
                logger.info(f"Retrieved all RSVPs for event {event_id}: {len(all_rsvps)} total")
                break

            offset += limit
            logger.debug(f"Fetching next page (offset={offset})")

        return all_rsvps

    def get_rsvp_statuses(self) -> List[str]:
        """
        Get available RSVP status values.

        Returns:
            List of RSVP status constants
        """
        return ["YES", "NO", "WAITING", "PENDING"]
