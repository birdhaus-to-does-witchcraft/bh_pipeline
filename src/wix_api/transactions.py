"""
Wix Order Transactions API V1 wrapper.

This module provides high-level methods for interacting with the Wix Order Transactions V1 API.
All endpoints validated against official Wix documentation (October 2025).

Reference: VALIDATED_ENDPOINTS.md
Base URL: https://www.wixapis.com/ecom/v1
Documentation: https://dev.wix.com/docs/rest/business-solutions/e-commerce/orders/order-transactions/introduction
"""

import logging
from typing import Any, Dict, List, Optional

from wix_api.client import WixAPIClient

logger = logging.getLogger(__name__)


class TransactionsAPI:
    """
    Wrapper for Wix Order Transactions API V1.

    Provides methods to retrieve and manage payment and refund transactions for orders.

    Example:
        >>> from wix_api.client import WixAPIClient
        >>> client = WixAPIClient.from_env()
        >>> transactions_api = TransactionsAPI(client)
        >>> transactions = transactions_api.list_transactions_for_order("order-123")
    """

    def __init__(self, client: WixAPIClient):
        """
        Initialize Transactions API wrapper.

        Args:
            client: Authenticated WixAPIClient instance
        """
        self.client = client
        self.base_path = "/ecom/v1/orders"

    def list_transactions_for_order(self, order_id: str) -> Dict[str, Any]:
        """
        List all transactions (payments and refunds) for a single order.

        Endpoint: GET /ecom/v1/orders/{orderId}/transactions

        Args:
            order_id: The order ID

        Returns:
            List of transactions for the order

        Example:
            >>> transactions = transactions_api.list_transactions_for_order("order-123")
            >>> for txn in transactions.get("transactions", []):
            ...     print(f"{txn['type']}: {txn['amount']}")
        """
        logger.info(f"Listing transactions for order: {order_id}")
        return self.client.get(f"{self.base_path}/{order_id}/transactions")

    def list_transactions_for_multiple_orders(
        self,
        order_ids: List[str]
    ) -> Dict[str, Any]:
        """
        List transactions for multiple orders in a single request.

        Endpoint: POST /ecom/v1/orders/transactions/list

        Args:
            order_ids: List of order IDs

        Returns:
            Transactions grouped by order ID

        Example:
            >>> order_ids = ["order-1", "order-2", "order-3"]
            >>> transactions = transactions_api.list_transactions_for_multiple_orders(order_ids)
        """
        logger.info(f"Listing transactions for {len(order_ids)} orders")
        payload = {
            "orderIds": order_ids
        }
        return self.client.post(f"{self.base_path}/transactions/list", json=payload)

    def add_payments(
        self,
        order_id: str,
        payments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Add payment records to an order.

        Endpoint: POST /ecom/v1/orders/{orderId}/transactions/payments

        Can add up to 50 payment records in a single API call.

        Args:
            order_id: The order ID
            payments: List of payment records to add

        Returns:
            Added payment details

        Example:
            >>> payments = [
            ...     {
            ...         "amount": 100.00,
            ...         "currency": "USD",
            ...         "paymentMethod": "creditCard",
            ...         "transactionId": "txn-123",
            ...         "status": "COMPLETED"
            ...     }
            ... ]
            >>> result = transactions_api.add_payments("order-123", payments)
        """
        if len(payments) > 50:
            logger.warning(f"Adding {len(payments)} payments exceeds limit of 50, only first 50 will be added")
            payments = payments[:50]

        logger.info(f"Adding {len(payments)} payment records to order: {order_id}")
        payload = {
            "payments": payments
        }
        return self.client.post(f"{self.base_path}/{order_id}/transactions/payments", json=payload)

    def update_payment_status(
        self,
        order_id: str,
        transaction_id: str,
        status: str
    ) -> Dict[str, Any]:
        """
        Update payment transaction status.

        Endpoint: PATCH /ecom/v1/orders/{orderId}/transactions/{transactionId}/status

        Args:
            order_id: The order ID
            transaction_id: The transaction ID
            status: New status (e.g., "COMPLETED", "PENDING", "FAILED", "REFUNDED")

        Returns:
            Updated transaction details

        Example:
            >>> result = transactions_api.update_payment_status(
            ...     order_id="order-123",
            ...     transaction_id="txn-456",
            ...     status="COMPLETED"
            ... )
        """
        logger.info(f"Updating payment status for transaction {transaction_id} to {status}")
        payload = {
            "status": status
        }
        return self.client.patch(
            f"{self.base_path}/{order_id}/transactions/{transaction_id}/status",
            json=payload
        )

    def bulk_update_payment_statuses(
        self,
        updates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Bulk update payment statuses for multiple transactions.

        Endpoint: POST /ecom/v1/orders/transactions/statuses/bulk-update

        Args:
            updates: List of status updates with order_id, transaction_id, and status

        Returns:
            Bulk operation results

        Example:
            >>> updates = [
            ...     {
            ...         "orderId": "order-1",
            ...         "transactionId": "txn-1",
            ...         "status": "COMPLETED"
            ...     },
            ...     {
            ...         "orderId": "order-2",
            ...         "transactionId": "txn-2",
            ...         "status": "FAILED"
            ...     }
            ... ]
            >>> result = transactions_api.bulk_update_payment_statuses(updates)
        """
        logger.info(f"Bulk updating {len(updates)} payment statuses")
        payload = {
            "updates": updates
        }
        return self.client.post(f"{self.base_path}/transactions/statuses/bulk-update", json=payload)

    def get_all_transactions_for_orders(
        self,
        order_ids: List[str],
        batch_size: int = 50
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Helper method to retrieve all transactions for a large list of orders.

        Batches requests to handle large order lists efficiently.

        Args:
            order_ids: List of order IDs
            batch_size: Number of orders per batch request (default: 50)

        Returns:
            Dictionary mapping order IDs to their transactions

        Example:
            >>> order_ids = [f"order-{i}" for i in range(200)]
            >>> all_transactions = transactions_api.get_all_transactions_for_orders(order_ids)
            >>> for order_id, txns in all_transactions.items():
            ...     print(f"{order_id}: {len(txns)} transactions")
        """
        all_transactions = {}

        # Split into batches
        total_orders = len(order_ids)
        logger.info(f"Retrieving transactions for {total_orders} orders in batches of {batch_size}")

        for i in range(0, total_orders, batch_size):
            batch = order_ids[i:i + batch_size]
            logger.debug(f"Fetching batch {i // batch_size + 1} ({len(batch)} orders)")

            response = self.list_transactions_for_multiple_orders(batch)

            # Parse response and group by order
            for order_data in response.get("orders", []):
                order_id = order_data.get("orderId")
                transactions = order_data.get("transactions", [])
                all_transactions[order_id] = transactions

        logger.info(f"Retrieved transactions for {len(all_transactions)} orders")
        return all_transactions

    def get_payment_methods(self) -> List[str]:
        """
        Helper to document common payment method types.

        Returns:
            List of common payment method identifiers
        """
        return [
            "creditCard",
            "debitCard",
            "paypal",
            "stripe",
            "cash",
            "check",
            "bankTransfer",
            "wixPayments",
            "offline"
        ]

    def get_transaction_statuses(self) -> List[str]:
        """
        Helper to document transaction status values.

        Returns:
            List of transaction status constants
        """
        return [
            "PENDING",
            "COMPLETED",
            "FAILED",
            "CANCELLED",
            "REFUNDED",
            "PARTIALLY_REFUNDED",
            "CHARGEBACK",
            "CHARGEBACK_REVERSED"
        ]

    def get_transaction_types(self) -> List[str]:
        """
        Helper to document transaction type values.

        Returns:
            List of transaction type constants
        """
        return [
            "PAYMENT",
            "REFUND",
            "CHARGEBACK",
            "AUTHORIZATION"
        ]
