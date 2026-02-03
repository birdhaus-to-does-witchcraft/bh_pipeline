"""
Pagination utilities for Wix API responses.

This module provides reusable pagination logic that can be used across
different API endpoints (events, guests, contacts, etc.).
"""

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


def paginate_query(
    query_func: Callable,
    response_key: str,
    limit: int = 100,
    max_results: Optional[int] = None,
    **query_kwargs
) -> List[Dict[str, Any]]:
    """
    Generic pagination helper for Wix API queries.

    This function handles the pagination logic for any Wix API endpoint that
    uses offset-based pagination with pagingMetadata responses.

    Args:
        query_func: The query function to call (e.g., events_api.query_events)
        response_key: The key in the response containing the items (e.g., "events", "guests")
        limit: Number of items per page (default: 100)
        max_results: Maximum total results to return (None = all)
        **query_kwargs: Additional keyword arguments to pass to query_func

    Returns:
        List of all items collected from all pages

    Example:
        >>> from wix_api.events import EventsAPI
        >>> events_api = EventsAPI(client)
        >>> all_events = paginate_query(
        ...     query_func=events_api.query_events,
        ...     response_key="events",
        ...     limit=100,
        ...     filter_dict={"status": ["PUBLISHED"]}
        ... )
    """
    all_items = []
    offset = 0

    logger.info(f"Starting paginated query for '{response_key}' (limit={limit} per page)")

    while True:
        # Call the query function with current offset
        response = query_func(
            limit=limit,
            offset=offset,
            **query_kwargs
        )

        # Extract items from response
        items = response.get(response_key, [])
        all_items.extend(items)

        logger.debug(f"Retrieved {len(items)} items (total so far: {len(all_items)})")

        # Check if we've reached max_results
        if max_results and len(all_items) >= max_results:
            all_items = all_items[:max_results]
            logger.info(f"Reached max_results limit: {max_results}")
            break

        # Check pagination metadata - some APIs use pagingMetadata, others use top-level total
        paging_metadata = response.get("pagingMetadata", {})
        count = paging_metadata.get("count", len(items))  # Fallback to actual items count
        # Check for total in pagingMetadata first, then top-level response (orders API)
        total = paging_metadata.get("total") or response.get("total")

        # No more items if we got zero results
        if len(items) == 0:
            logger.info(f"Retrieved all items: {len(all_items)} total")
            break

        # If total is provided and we've reached it, stop
        if total is not None and len(all_items) >= total:
            logger.info(f"Retrieved all items: {len(all_items)} total (reached specified total: {total})")
            break

        # For APIs without total, continue until we get fewer items than requested
        if len(items) < limit:
            logger.info(f"Retrieved all items: {len(all_items)} total (partial page indicates end)")
            break

        # Move to next page
        offset += limit
        logger.debug(f"Fetching next page (offset={offset})")

    return all_items


def has_more_pages(paging_metadata: Dict[str, Any], current_total: int, limit: int = 100) -> bool:
    """
    Check if there are more pages to fetch based on Wix API paging metadata.

    Wix API returns pagingMetadata with:
    - count: Number of items in current response
    - offset: Current offset
    - total: Total number of items available (optional - not all APIs provide this)
    - hasNext: Boolean indicating if more pages exist (optional)

    Args:
        paging_metadata: The pagingMetadata object from API response
        current_total: Current total number of items fetched so far
        limit: Expected items per page (default: 100)

    Returns:
        True if there are more pages to fetch, False otherwise

    Example:
        >>> paging_metadata = {"count": 100, "offset": 0, "total": 250}
        >>> has_more_pages(paging_metadata, 100)
        True
        >>> paging_metadata = {"count": 50, "offset": 50}  # No total field
        >>> has_more_pages(paging_metadata, 50, limit=100)
        False  # Partial page indicates no more results
    """
    count = paging_metadata.get("count", 0)
    total = paging_metadata.get("total")  # May be None
    has_next = paging_metadata.get("hasNext", None)

    # No more pages if we got zero results
    if count == 0:
        return False

    # If hasNext is provided, use it
    if has_next is not None:
        return has_next

    # If total is provided, check against it
    if total is not None:
        return current_total < total

    # If no total, check if we got a partial page (fewer items than requested)
    # A partial page indicates we've reached the end
    return count >= limit
