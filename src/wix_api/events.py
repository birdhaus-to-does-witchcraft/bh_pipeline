"""
Wix Events API V3 wrapper.

This module provides high-level methods for interacting with the Wix Events V3 API.
All endpoints validated against official Wix documentation (October 2025).

Reference: VALIDATED_ENDPOINTS.md
Base URL: https://www.wixapis.com/events/v3
Documentation: https://dev.wix.com/docs/rest/business-solutions/events/events-v3/introduction
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from wix_api.client import WixAPIClient
from utils.pagination import paginate_query

logger = logging.getLogger(__name__)


class EventsAPI:
    """
    Wrapper for Wix Events API V3.

    Provides methods to query, create, update, and manage events.

    Example:
        >>> from wix_api.client import WixAPIClient
        >>> client = WixAPIClient.from_env()
        >>> events_api = EventsAPI(client)
        >>> events = events_api.query_events(limit=10)
    """

    def __init__(self, client: WixAPIClient):
        """
        Initialize Events API wrapper.

        Args:
            client: Authenticated WixAPIClient instance
        """
        self.client = client
        self.base_path = "/events/v3/events"

    def query_events(
        self,
        limit: int = 100,
        offset: int = 0,
        filter_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Query events with filtering and pagination.

        Endpoint: POST /events/v3/events/query

        Args:
            limit: Number of events to return (default: 100)
            offset: Offset for pagination (default: 0)
            filter_dict: Filter criteria (e.g., {"status": ["PUBLISHED"]})
            sort: Sort criteria (e.g., [{"fieldName": "scheduling.config.startDate", "order": "ASC"}])

        Returns:
            Response with events list and paging metadata

        Example:
            >>> events = events_api.query_events(
            ...     limit=10,
            ...     filter_dict={"status": ["PUBLISHED"]},
            ...     sort=[{"fieldName": "scheduling.config.startDate", "order": "DESC"}]
            ... )
        """
        query_obj: Dict[str, Any] = {
            "paging": {
                "limit": limit,
                "offset": offset
            }
        }

        if filter_dict:
            query_obj["filter"] = filter_dict

        if sort:
            query_obj["sort"] = sort

        # Wrap in query object as required by API
        payload = {"query": query_obj}

        logger.info(f"Querying events (limit={limit}, offset={offset})")
        return self.client.post(f"{self.base_path}/query", json=payload)

    def get_event(self, event_id: str) -> Dict[str, Any]:
        """
        Get detailed event information by ID.

        Endpoint: GET /events/v3/events/{eventId}

        Args:
            event_id: The event ID

        Returns:
            Event details

        Example:
            >>> event = events_api.get_event("event-123")
        """
        logger.info(f"Getting event: {event_id}")
        return self.client.get(f"{self.base_path}/{event_id}")

    def get_event_by_slug(self, slug: str) -> Dict[str, Any]:
        """
        Get detailed event information by slug.

        Endpoint: GET /events/v3/events/by-slug/{slug}

        Args:
            slug: The event slug (URL-friendly identifier)

        Returns:
            Event details

        Example:
            >>> event = events_api.get_event_by_slug("summer-concert-2025")
        """
        logger.info(f"Getting event by slug: {slug}")
        return self.client.get(f"{self.base_path}/by-slug/{slug}")

    def list_events_by_category(
        self,
        category_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List events by category.

        Endpoint: GET /events/v3/events/by-category/{categoryId}

        Args:
            category_id: The category ID
            limit: Number of events to return (default: 100)
            offset: Offset for pagination (default: 0)

        Returns:
            List of events in the category

        Example:
            >>> events = events_api.list_events_by_category("cat-123", limit=10)
        """
        logger.info(f"Listing events by category: {category_id}")
        params = {
            "limit": limit,
            "offset": offset
        }
        return self.client.get(f"{self.base_path}/by-category/{category_id}", params=params)

    def create_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new event.

        Endpoint: POST /events/v3/events

        Args:
            event_data: Event configuration (title, description, scheduling, etc.)

        Returns:
            Created event details including ID

        Example:
            >>> event_data = {
            ...     "title": "New Event",
            ...     "description": "Event description",
            ...     "scheduling": {
            ...         "config": {
            ...             "startDate": "2025-12-01T18:00:00Z",
            ...             "endDate": "2025-12-01T22:00:00Z",
            ...             "timeZoneId": "America/New_York"
            ...         }
            ...     }
            ... }
            >>> event = events_api.create_event(event_data)
        """
        logger.info("Creating new event")
        return self.client.post(self.base_path, json=event_data)

    def update_event(self, event_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing event.

        Endpoint: PATCH /events/v3/events/{eventId}

        Args:
            event_id: The event ID
            event_data: Event fields to update

        Returns:
            Updated event details

        Example:
            >>> updates = {"title": "Updated Title"}
            >>> event = events_api.update_event("event-123", updates)
        """
        logger.info(f"Updating event: {event_id}")
        return self.client.patch(f"{self.base_path}/{event_id}", json=event_data)

    def clone_event(self, event_id: str) -> Dict[str, Any]:
        """
        Clone an existing event.

        Endpoint: POST /events/v3/events/{eventId}/clone

        Args:
            event_id: The event ID to clone

        Returns:
            Cloned event details

        Example:
            >>> cloned = events_api.clone_event("event-123")
        """
        logger.info(f"Cloning event: {event_id}")
        return self.client.post(f"{self.base_path}/{event_id}/clone")

    def publish_event(self, event_id: str) -> Dict[str, Any]:
        """
        Publish a draft event.

        Endpoint: POST /events/v3/events/{eventId}/publish

        Args:
            event_id: The event ID to publish

        Returns:
            Published event details

        Example:
            >>> event = events_api.publish_event("event-123")
        """
        logger.info(f"Publishing event: {event_id}")
        return self.client.post(f"{self.base_path}/{event_id}/publish")

    def cancel_event(self, event_id: str) -> Dict[str, Any]:
        """
        Cancel an event.

        Endpoint: POST /events/v3/events/{eventId}/cancel

        Args:
            event_id: The event ID to cancel

        Returns:
            Canceled event details

        Example:
            >>> event = events_api.cancel_event("event-123")
        """
        logger.info(f"Canceling event: {event_id}")
        return self.client.post(f"{self.base_path}/{event_id}/cancel")

    def bulk_cancel_events(self, filter_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Bulk cancel events by filter.

        Endpoint: POST /events/v3/events/cancel

        Args:
            filter_dict: Filter criteria to select events to cancel

        Returns:
            Bulk operation results

        Example:
            >>> result = events_api.bulk_cancel_events(
            ...     {"eventId": {"$in": ["event-1", "event-2"]}}
            ... )
        """
        logger.info("Bulk canceling events")
        return self.client.post(f"{self.base_path}/cancel", json={"filter": filter_dict})

    def delete_event(self, event_id: str) -> Dict[str, Any]:
        """
        Delete an event.

        Endpoint: DELETE /events/v3/events/{eventId}

        Args:
            event_id: The event ID to delete

        Returns:
            Deletion confirmation

        Example:
            >>> result = events_api.delete_event("event-123")
        """
        logger.info(f"Deleting event: {event_id}")
        return self.client.delete(f"{self.base_path}/{event_id}")

    def bulk_delete_events(self, filter_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Bulk delete events by filter.

        Endpoint: POST /events/v3/events/delete

        Args:
            filter_dict: Filter criteria to select events to delete

        Returns:
            Bulk operation results

        Example:
            >>> result = events_api.bulk_delete_events(
            ...     {"status": ["DRAFT"]}
            ... )
        """
        logger.info("Bulk deleting events")
        return self.client.post(f"{self.base_path}/delete", json={"filter": filter_dict})

    def count_events_by_status(self) -> Dict[str, Any]:
        """
        Count events by status.

        Endpoint: POST /events/v3/events/count-by-status

        Returns:
            Event counts by status (PUBLISHED, DRAFT, CANCELED, etc.)

        Example:
            >>> counts = events_api.count_events_by_status()
            >>> print(f"Published: {counts['PUBLISHED']}")
        """
        logger.info("Counting events by status")
        return self.client.post(f"{self.base_path}/count-by-status")

    def get_all_events(
        self,
        filter_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[List[Dict[str, str]]] = None,
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Helper method to retrieve all events using pagination.

        Automatically handles pagination to retrieve all matching events.

        Args:
            filter_dict: Filter criteria
            sort: Sort criteria
            max_results: Maximum number of results to return (None = all)

        Returns:
            List of all events

        Example:
            >>> all_events = events_api.get_all_events(
            ...     filter_dict={"status": ["PUBLISHED"]},
            ...     max_results=1000
            ... )
        """
        return paginate_query(
            query_func=self.query_events,
            response_key="events",
            limit=100,
            max_results=max_results,
            filter_dict=filter_dict,
            sort=sort
        )
