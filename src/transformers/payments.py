"""
Cashier Payments transformer.

Flattens the raw Wix Cashier Transactions API response (one row per
financial transaction) into an Excel-friendly CSV that matches the schema
of the manual `Payments` export from the Wix dashboard, with extra columns
useful for joining back to events / orders / contacts in downstream gold
views.

Source: ``src/wix_api/payments.py`` -> ``PaymentsAPI.get_all_transactions()``.

Schema design notes
-------------------
* Grain is one row per Wix transaction (sale, refund, chargeback, declined).
  This matches the dashboard "Payments" CSV one-to-one and is finer than the
  per-order grain in `event_orders_<ts>.csv`.
* `wix_app_order_id` is the join key back to `event_orders.order_number`
  (e.g. "3088-CBPT-789") -- preserved deliberately so a downstream gold
  fact can attach event_title / category_names / etc.
* Refunds live as a list inside the original sale transaction; we surface
  them as derived `refund_count`, `refund_total_amount`, `refund_status` and
  also expose `net_amount = amount - platform_fee - refund_total_amount`
  so the silver CSV is directly usable for revenue rollups without
  needing the raw refunds array.
* `transaction_status_friendly` maps the raw enum to the human-readable
  labels Wix uses in the dashboard (Successful / Declined / Refunded /
  Chargeback / Cancelled). Keep the raw `status` too so analysts can
  filter by the canonical enum.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from transformers.base import BaseTransformer

logger = logging.getLogger(__name__)


# Maps the raw TransactionStatus enum to the human label Wix shows in the
# Payments dashboard CSV. Anything not listed is passed through verbatim so
# we never silently drop a new state Wix introduces.
STATUS_FRIENDLY = {
    "APPROVED": "Successful",
    "AUTHORIZED": "Successful",
    "PENDING": "Pending",
    "PENDING_BUYER": "Pending",
    "PENDING_MERCHANT": "Pending",
    "IN_PROCESS": "Pending",
    "INITIALIZED": "Pending",
    "REFUND": "Refunded",
    "PARTIAL_REFUND": "Partially refunded",
    "CHARGE_BACK": "Chargeback",
    "DISPUTE": "Dispute",
    "DECLINED": "Declined",
    "FAILED": "Failed",
    "EXPIRED": "Expired",
    "TIMEOUT": "Timed out",
    "BUYER_CANCELED": "Cancelled",
    "VOID": "Voided",
    "TPA_CANCELED": "Cancelled",
    "OFFLINE": "Offline",
    "COMPLETED_FUNDS_HELD": "Funds held",
}

# Maps the `provider` field (a reverse-DNS-ish identifier) to the friendly
# label that appears in the Payments dashboard CSV's "Payment Provider"
# column.
PROVIDER_FRIENDLY = {
    "com.stripe": "Stripe",
    "payPal": "PayPal",
    "paypal": "PayPal",
    "NA": "Pay in person",
    "": "Pay in person",
}

# Wix app GUIDs we currently care about. Useful for filtering payments to
# just Events/Bookings/etc. on the silver layer without parsing item names.
APP_ID_FRIENDLY = {
    "140603ad-af8d-84a5-2c80-a0f60cb47351": "Wix Events & Tickets",
    "215238eb-22a5-4c36-9e7b-e7c08025e04e": "Wix Stores",
    "13d21c63-b5ec-5912-8397-c3a5ddb27a97": "Wix Bookings",
}

# Item id Wix uses on the synthetic "Service Fee" line. We split it out
# from real product items so quantity / product_name aggregates aren't
# polluted by the fee row.
SERVICE_FEE_ITEM_ID = "SERVICE_FEE"


def _safe_float(value: Any) -> Optional[float]:
    """Coerce to float, treating empty strings and NaN as None."""
    if value is None or value == "":
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f


def _join_nonempty(parts: List[Optional[str]], sep: str = " ") -> Optional[str]:
    cleaned = [str(p).strip() for p in parts if p]
    return sep.join(p for p in cleaned if p) or None


class PaymentsTransformer(BaseTransformer):
    """Flatten Wix Cashier transactions into one CSV row per transaction."""

    @staticmethod
    def transform_transaction(txn: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single transaction dict into a flat row."""
        order = txn.get("order") or {}
        description = order.get("description") or {}
        billing = description.get("billingAddress") or {}
        shipping = description.get("shippingAddress") or {}
        items = description.get("items") or []
        additional = description.get("additionalCharges") or {}
        subscription = description.get("subscription") or {}

        amount_obj = txn.get("amount") or {}
        method_data = txn.get("paymentMethodData") or {}
        cashier_error = txn.get("cashierError") or {}
        refundability = txn.get("refundability") or {}
        refunds = txn.get("refunds") or []

        # Split product items from the synthetic SERVICE_FEE line so qty /
        # product_name stay clean. The service fee line still gets summed
        # into `service_fee_line_amount` for visibility.
        product_items = [i for i in items if i.get("id") != SERVICE_FEE_ITEM_ID]
        fee_items = [i for i in items if i.get("id") == SERVICE_FEE_ITEM_ID]

        product_names = [i.get("name") for i in product_items if i.get("name")]
        product_quantities = [int(i.get("quantity") or 0) for i in product_items]
        primary_product = product_items[0] if product_items else {}

        # Refund roll-ups (used for net_amount and dashboard parity).
        # We only count SUCCEEDED refunds toward the financial total but
        # surface counts for all refund records for completeness.
        succeeded_refunds = [r for r in refunds if (r.get("status") or "").upper() == "SUCCEEDED"]
        refund_total = sum(_safe_float(r.get("amount")) or 0.0 for r in succeeded_refunds) or None
        latest_refund = max(refunds, key=lambda r: r.get("createdAt") or "", default=None)

        amount = _safe_float(amount_obj.get("amount"))
        platform_fee = _safe_float(txn.get("platformFee"))

        # Net = what landed in the merchant's account *after* Wix fee and
        # any successful refunds. This is the equivalent of the "Net" column
        # in the dashboard Payments CSV (which Wix often leaves blank).
        net_amount: Optional[float] = None
        if amount is not None:
            net_amount = amount - (platform_fee or 0.0) - (refund_total or 0.0)

        created_at = txn.get("createdAt")
        created_date, created_time = (None, None)
        if created_at:
            created_date, created_time = BaseTransformer.extract_date_and_time(created_at)

        latest_refund_date = (latest_refund or {}).get("createdAt")
        refund_date, refund_time = (None, None)
        if latest_refund_date:
            refund_date, refund_time = BaseTransformer.extract_date_and_time(latest_refund_date)

        raw_status = txn.get("status") or ""
        status_friendly = STATUS_FRIENDLY.get(raw_status, raw_status.title() if raw_status else None)
        # If Wix recorded successful refunds against an APPROVED txn, the
        # dashboard relabels it Refunded. Mirror that so transaction_status
        # matches the manual export.
        if raw_status == "APPROVED" and refund_total:
            status_friendly = "Refunded" if (amount and refund_total >= amount) else "Partially refunded"

        provider = txn.get("provider") or ""
        provider_friendly = PROVIDER_FRIENDLY.get(provider) or txn.get("providerName") or provider or None

        billing_full_name = _join_nonempty([billing.get("firstName"), billing.get("lastName")])

        return {
            # Grain identifiers
            "transaction_id": txn.get("transactionId"),
            "provider_transaction_id": txn.get("providerTransactionId") or None,
            "order_id": order.get("id"),
            "wix_app_order_id": description.get("wixAppOrderId") or None,
            "wix_app_buyer_id": description.get("wixAppBuyerId") or None,
            "app_id": txn.get("appId"),
            "app_name": APP_ID_FRIENDLY.get(txn.get("appId") or "", None),

            # Dates
            "payment_date": created_date,
            "payment_time": created_time,
            "payment_datetime": created_at,

            # Money
            "currency": amount_obj.get("currency"),
            "amount": amount,
            "platform_fee": platform_fee,
            "service_fee_line_amount": (
                sum(_safe_float(i.get("price")) or 0.0 for i in fee_items) or None
            ),
            "net_amount": net_amount,
            "tax": _safe_float(additional.get("tax")),
            "shipping": _safe_float(additional.get("shipping")),
            "discount": _safe_float(additional.get("discount")),

            # Status
            "status": raw_status or None,
            "transaction_status": status_friendly,
            "transaction_type": txn.get("type"),
            "is_refundable": refundability.get("isRefundable"),
            "non_refundable_reason": (refundability.get("reason") or {}).get("value"),
            "failure_code": cashier_error.get("failureCode") or None,

            # Provider / payment method
            "payment_provider": provider or None,
            "payment_provider_friendly": provider_friendly,
            "payment_method": txn.get("paymentMethod") or None,
            "payment_method_type": method_data.get("PaymentMethodDataType") or None,
            "provider_dashboard_link": txn.get("providerDashboardLink") or None,

            # Card / wallet detail (for Credit/Debit only)
            "card_network": method_data.get("network") or None,
            "card_last_four": method_data.get("lastFour") or None,
            "card_masked": method_data.get("maskedCreditCard") or None,
            "card_expiry": method_data.get("creditCardExpiryMonth") or None,
            "card_holder_name": (method_data.get("holderName") or "").strip() or None,
            "card_bin": method_data.get("bin") or None,
            "installments": method_data.get("installments") or None,

            # Refunds
            "refund_count": len(refunds),
            "refund_succeeded_count": len(succeeded_refunds),
            "refund_total_amount": refund_total,
            "refund_status": (latest_refund or {}).get("status"),
            "refund_type": (latest_refund or {}).get("type"),
            "refund_reason": (latest_refund or {}).get("reason"),
            "refund_provider_id": (latest_refund or {}).get("providerRefundId"),
            "refund_date": refund_date,
            "refund_time": refund_time,

            # Buyer / billing
            "billing_first_name": billing.get("firstName") or None,
            "billing_last_name": billing.get("lastName") or None,
            "billing_full_name": billing_full_name,
            "billing_email": billing.get("email") or None,
            "billing_phone": billing.get("phone") or None,
            "billing_company": billing.get("company") or None,
            "billing_address": billing.get("address") or None,
            "billing_city": billing.get("city") or None,
            "billing_state": billing.get("state") or None,
            "billing_zip": billing.get("zipCode") or None,
            "billing_country": billing.get("countryCode") or None,

            # Shipping (rare for events but Wix returns the structure)
            "shipping_first_name": shipping.get("firstName") or None,
            "shipping_last_name": shipping.get("lastName") or None,
            "shipping_email": shipping.get("email") or None,
            "shipping_city": shipping.get("city") or None,
            "shipping_country": shipping.get("countryCode") or None,

            # Order line items
            "product_name": ", ".join(product_names) if product_names else None,
            "product_count": len(product_items),
            "total_quantity": sum(product_quantities) if product_quantities else None,
            "primary_product_name": primary_product.get("name") or None,
            "primary_product_unit_price": _safe_float(primary_product.get("price")),
            "primary_product_quantity": primary_product.get("quantity") or None,

            # Subscription (only populated for recurring billing)
            "subscription_status": subscription.get("status") or None,
            "subscription_frequency": subscription.get("frequency") or None,
            "subscription_interval": subscription.get("interval") or None,
            "subscription_billing_cycles": subscription.get("billingCycles") or None,
        }

    @staticmethod
    def transform_transactions(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform a list of cashier transactions, skipping malformed rows."""
        out: List[Dict[str, Any]] = []
        for t in transactions:
            try:
                out.append(PaymentsTransformer.transform_transaction(t))
            except Exception as e:
                logger.error(
                    "Failed to transform payment %s: %s",
                    t.get("transactionId", "<unknown>"), e,
                )
        logger.info("Transformed %d payments", len(out))
        return out

    @staticmethod
    def save_to_csv(
        transactions: List[Dict[str, Any]],
        output_path: str,
        encoding: str = "utf-8-sig",
        **kwargs,
    ) -> None:
        """Transform and save to CSV in one step (UTF-8 BOM for Excel)."""
        rows = PaymentsTransformer.transform_transactions(transactions)
        BaseTransformer.save_to_csv(rows, output_path, encoding=encoding, **kwargs)
