"""
Wix Event Orders API V1 wrapper.

This module provides high-level methods for interacting with the Wix Event Orders V1 API.
All endpoints validated against official Wix documentation (October 2025).

Reference: PAYMENT_DATA_ENDPOINTS.md
Base URL: https://www.wixapis.com/events/v1
Documentation: https://dev.wix.com/api/rest/wix-events/wix-events/order

IMPORTANT: This is the Orders API V1, which provides:
- List of all orders
- Individual order details (with event ID + order number)
- Sales summary per event (total sales, revenue, ticket counts)
"""

import logging
from typing import Any, Dict, List, Optional

from wix_api.client import WixAPIClient
from utils.pagination import paginate_query

logger = logging.getLogger(__name__)


class OrdersAPI:
    """
    Wrapper for Wix Event Orders API V1.

    Provides methods to query orders and retrieve sales summary information,
    including revenue, ticket counts, and payment data.

    Example:
        >>> from wix_api.client import WixAPIClient
        >>> client = WixAPIClient.from_env()
        >>> orders_api = OrdersAPI(client)
        >>> summary = orders_api.get_summary_by_event("event-123")
        >>> print(f"Total: ${summary['total']['amount']}")
    """

    def __init__(self, client: WixAPIClient):
        """
        Initialize Orders API wrapper.

        Args:
            client: Authenticated WixAPIClient instance
        """
        self.client = client
        self.base_path = "/events/v1/orders"

    def list_orders(
        self,
        limit: int = 400,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List all orders across all events.

        Endpoint: GET /events/v1/orders

        NOTE: This endpoint uses GET with query parameters.
        Response uses total/offset/limit format (not pagingMetadata).

        Args:
            limit: Number of orders to return (max 400, default: 400)
            offset: Offset for pagination (default: 0)

        Returns:
            Response with orders list and pagination data

        Example:
            >>> orders = orders_api.list_orders(limit=50)
            >>> for order in orders.get('orders', []):
            ...     print(order['orderNumber'], order['eventId'])
        """
        params = {
            "limit": limit,
            "offset": offset
        }

        logger.info(f"Listing orders (limit={limit}, offset={offset})")
        return self.client.get(self.base_path, params=params)

    def get_order(
        self,
        event_id: str,
        order_number: str
    ) -> Dict[str, Any]:
        """
        Get individual order details by event ID and order number.

        Endpoint: GET /events/v1/events/{eventId}/orders/{orderNumber}

        Args:
            event_id: The event GUID
            order_number: The order number (e.g., "2Z4T-98RG-RNZ")

        Returns:
            Response with order details and calendarLinks

        Example:
            >>> order = orders_api.get_order(
            ...     event_id="event-123",
            ...     order_number="2Z4T-98RG-RNZ"
            ... )
            >>> print(order['order']['transactionId'])
        """
        logger.info(f"Getting order: {order_number} for event {event_id}")
        return self.client.get(f"/events/v1/events/{event_id}/orders/{order_number}")

    def get_summary(
        self,
        event_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get sales summary with total sales, revenue, and ticket counts.

        Endpoint: GET /events/v1/orders/summary

        This is the KEY endpoint for getting actual sales/payment data!

        Returns aggregate data:
        - total: Total sales amount (including fees)
        - revenue: Net revenue (after Wix fees deducted)
        - totalOrders: Number of orders
        - totalTickets: Number of tickets sold

        Args:
            event_id: Optional event ID to filter summary (default: all events)

        Returns:
            Response with sales summary data

        Example (all events):
            >>> summary = orders_api.get_summary()
            >>> sales = summary['sales'][0]
            >>> print(f"Total: ${sales['total']['amount']}")
            >>> print(f"Revenue: ${sales['revenue']['amount']}")

        Example (specific event):
            >>> summary = orders_api.get_summary(event_id="event-123")
            >>> sales = summary['sales'][0]
            >>> print(f"Orders: {sales['totalOrders']}")
            >>> print(f"Tickets: {sales['totalTickets']}")
        """
        params = {}
        if event_id:
            params['eventId'] = event_id
            logger.info(f"Getting sales summary for event: {event_id}")
        else:
            logger.info("Getting sales summary for all events")

        return self.client.get(f"{self.base_path}/summary", params=params)

    def get_summary_by_event(self, event_id: str) -> Dict[str, Any]:
        """
        Get sales summary for a specific event.

        Alias for get_summary(event_id=...) for clarity.

        Args:
            event_id: The event ID to get summary for

        Returns:
            Sales summary for the event

        Example:
            >>> summary = orders_api.get_summary_by_event("event-123")
            >>> sales = summary['sales'][0]
            >>> total_revenue = float(sales['revenue']['amount'])
        """
        return self.get_summary(event_id=event_id)

    def get_all_orders(
        self,
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Helper method to retrieve all orders with automatic pagination.

        Args:
            max_results: Maximum number of results to return (None = all)

        Returns:
            List of all orders

        Example:
            >>> all_orders = orders_api.get_all_orders()
            >>> print(f"Total orders: {len(all_orders)}")
        """
        def query_func(limit: int, offset: int, **kwargs) -> Dict[str, Any]:
            return self.list_orders(limit=limit, offset=offset)

        return paginate_query(
            query_func=query_func,
            response_key="orders",
            limit=400,  # Wix API max limit for orders endpoint
            max_results=max_results
        )

    def get_order_statuses(self) -> List[str]:
        """
        Get available order status values.

        Based on Wix API documentation and observed data.

        Returns:
            List of order status constants
        """
        return [
            "NA_ORDER_STATUS",  # Not applicable / Unknown
            "INITIATED",        # Order initiated
            "PENDING",          # Payment pending
            "OFFLINE_PENDING",  # Offline payment pending
            "PAID",            # Payment completed
            "CONFIRMED"        # Order confirmed
        ]
