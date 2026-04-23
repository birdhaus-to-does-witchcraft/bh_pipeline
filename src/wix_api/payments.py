"""
Wix Cashier Payments API wrapper.

Hits the Wix dashboard "Payments" data — the same source that powers the CSV
exported from `Wix Dashboard > Sales > Payments`. This is NOT the eCommerce
Orders API or the Events Orders API; it is a separate "cashier" service that
records the financial transaction layer (Stripe / PayPal / Pay-in-person) sitting
underneath every paid order across all Wix business apps (Events, Stores,
Bookings, etc.).

Key endpoint
------------
GET https://www.wixapis.com/payments/api/merchant/v2/transactions

Validated 2026-04-22 against the live Birdhaus production site:
- 2735 transactions retrievable, paginated 100 at a time
- Each row carries the Stripe `pi_xxx` providerTransactionId, Wix
  transaction GUID, status, payment method, refunds[], platformFee, billing
  contact info, and `wixAppOrderId` (the events orderNumber for joins)

Why this lives in its own module
--------------------------------
`src/wix_api/transactions.py` already exists and wraps the eCommerce orders
+ transactions endpoints, which return zero rows for sites that don't sell
through Wix Stores. The Cashier API is the right source for an
event-ticketing-only site like Birdhaus, so we keep the wrappers separate
to avoid confusing the two.

Reference
---------
https://dev.wix.com/docs/api-reference/business-management/payments/cashier/payments/transaction/transactions-list
"""

import logging
from typing import Any, Dict, List, Optional

from wix_api.client import WixAPIClient

logger = logging.getLogger(__name__)


class PaymentsAPI:
    """
    Wrapper for the Wix Cashier (Payments dashboard) Transactions list API.

    Example:
        >>> from wix_api.client import WixAPIClient
        >>> client = WixAPIClient.from_env()
        >>> payments_api = PaymentsAPI(client)
        >>> all_payments = payments_api.get_all_transactions()
    """

    def __init__(self, client: WixAPIClient):
        self.client = client
        self.base_path = "/payments/api/merchant/v2/transactions"

    def list_transactions(
        self,
        limit: int = 100,
        offset: int = 0,
        include_refunds: bool = True,
        ignore_totals: bool = False,
        order: str = "date:desc",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        currency: Optional[str] = None,
        payment_provider: Optional[str] = None,
        payment_method: Optional[str] = None,
        status: Optional[List[str]] = None,
        app_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Single page of cashier transactions.

        Args:
            limit: Page size (max 100 per Wix conventions; default 100).
            offset: Pagination offset.
            include_refunds: Include refund records in the `refunds[]` array on
                each transaction. Recommended True so we can compute net /
                refund_amount on the silver layer.
            ignore_totals: When True, skip computing `pagination.total`. Faster
                on large datasets but you lose the total count.
            order: Sort order. Only `date:asc` and `date:desc` are supported.
            from_date / to_date: ISO-8601 date filters on createdAt.
            currency / payment_provider / payment_method: filter shortcuts.
            status: List of TransactionStatus enums to filter to.
            app_id: Filter to one Wix app's transactions.

        Returns:
            Raw response dict with `transactions` (list) and `pagination`.
        """
        params: Dict[str, Any] = {
            "limit": limit,
            "offset": offset,
            "includeRefunds": "true" if include_refunds else "false",
            "ignoreTotals": "true" if ignore_totals else "false",
            "order": order,
        }
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        if currency:
            params["currency"] = currency
        if payment_provider:
            params["paymentProvider"] = payment_provider
        if payment_method:
            params["paymentMethod"] = payment_method
        if status:
            params["status"] = status  # requests will repeat the key per value
        if app_id:
            params["appId"] = app_id

        logger.debug(
            "Listing payments (limit=%d, offset=%d, include_refunds=%s)",
            limit, offset, include_refunds,
        )
        return self.client.get(self.base_path, params=params)

    def get_all_transactions(
        self,
        include_refunds: bool = True,
        page_size: int = 100,
        max_results: Optional[int] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Paginate through every cashier transaction the API will return.

        The Cashier endpoint uses offset+limit pagination and exposes a
        `pagination.total` count when `ignoreTotals=false`, so we use it as
        the canonical termination signal. We also fall back to "stop on
        partial page" so a misreported total can't trap us in an infinite
        loop.

        Args:
            include_refunds: Pull the refunds[] array for each txn (recommended).
            page_size: Items per page (Wix max appears to be 100).
            max_results: Cap total rows returned. None = pull everything.
            from_date / to_date: Optional ISO-8601 createdAt window.

        Returns:
            Flat list of transaction dicts, oldest-first by createdAt
            (we sort `date:asc` so paginated runs are deterministic even when
            new transactions land mid-pull).
        """
        all_txns: List[Dict[str, Any]] = []
        offset = 0
        total: Optional[int] = None

        logger.info(
            "Fetching all cashier transactions (page_size=%d, include_refunds=%s)",
            page_size, include_refunds,
        )

        while True:
            response = self.list_transactions(
                limit=page_size,
                offset=offset,
                include_refunds=include_refunds,
                ignore_totals=False,
                order="date:asc",
                from_date=from_date,
                to_date=to_date,
            )
            page = response.get("transactions", []) or []
            all_txns.extend(page)

            pagination = response.get("pagination", {}) or {}
            if total is None:
                total = pagination.get("total")
                if total is not None:
                    logger.info("Cashier reports %d total transactions", total)

            logger.debug(
                "Fetched %d transactions (running total: %d)",
                len(page), len(all_txns),
            )

            if max_results and len(all_txns) >= max_results:
                all_txns = all_txns[:max_results]
                logger.info("Reached max_results cap: %d", max_results)
                break

            if not page:
                break
            if total is not None and len(all_txns) >= total:
                break
            if len(page) < page_size:
                # Partial page = no more results, even if `total` was misreported
                break

            offset += page_size

        logger.info("Retrieved %d cashier transactions", len(all_txns))
        return all_txns
