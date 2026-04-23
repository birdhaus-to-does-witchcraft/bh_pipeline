"""
Payments fact (gold layer) transformer.

Builds a denormalized one-row-per-payment analytics table by joining the
silver `payments` (cashier transactions) with `event_orders` (to resolve
event_id and contact_id), `events` (title, categories, schedule, location),
`contacts`/`members` (membership status), and `order_summaries` (event-level
revenue context).

Why this exists
---------------
The silver `payments_<ts>.csv` already mirrors the dashboard "Payments"
export, but it doesn't tell you *which event* a payment was for, what
*category* the event belongs to, or whether the buyer is a *member*.
Every analytical question we want to answer ("which events bring in the
most revenue?", "which categories pull the biggest crowds?", "are members
spending differently than non-members?") needs those joins, so we
materialize them once into a single wide table that's directly query-able
in Excel / DuckDB / pandas without writing JOINs.

Grain
-----
One row per payment (cashier transaction). Refunds, declines, chargebacks,
and cancelled checkouts each get their own row — same as the dashboard
CSV, plus the `BUYER_CANCELED` rows the dashboard silently filters out.

Join key chain
--------------
payments.wix_app_order_id (e.g. "3088-CBPT-789")
    -> event_orders.order_number
        -> event_orders.event_id          -> events.event_id
        -> event_orders.contact_id        -> contacts.contact_id
                                          -> members.contact_id
                                          -> order_summaries.event_id

When the join fails (payment with no matching order, e.g. test/manual
transactions), the dimension columns are left null and a `enrichment_status`
column documents which join missed so analysts can filter or audit.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional

from transformers.base import BaseTransformer

logger = logging.getLogger(__name__)


def _bucket_amount(value: Optional[float]) -> str:
    """Categorize transaction amount into a filterable band."""
    if value is None:
        return "Unknown"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "Unknown"
    if v == 0:
        return "Free"
    if v < 25:
        return "0-25"
    if v < 50:
        return "25-50"
    if v < 100:
        return "50-100"
    if v < 250:
        return "100-250"
    return "250+"


def _safe_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f


_TRUE_STRINGS = {"true", "1", "yes", "t", "y"}
_FALSE_STRINGS = {"false", "0", "no", "f", "n", "", "nan", "none", "null"}


def _safe_bool(value: Any) -> Optional[bool]:
    """Coerce stringy CSV booleans to a true/false/None tri-state."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if value != value:
            return None
        return bool(value)
    if isinstance(value, str):
        s = value.strip().lower()
        if s in _TRUE_STRINGS:
            return True
        if s in _FALSE_STRINGS:
            return None if s in {"", "nan", "none", "null"} else False
    return bool(value)


class PaymentsFactTransformer(BaseTransformer):
    """Build the payments_fact gold table from already-transformed silver dicts."""

    @staticmethod
    def build(
        transformed_payments: List[Dict[str, Any]],
        transformed_event_orders: Optional[List[Dict[str, Any]]] = None,
        transformed_events: Optional[List[Dict[str, Any]]] = None,
        transformed_contacts: Optional[List[Dict[str, Any]]] = None,
        transformed_members: Optional[List[Dict[str, Any]]] = None,
        transformed_order_summaries: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Build payments_fact rows from the silver layer.

        All inputs are *already-transformed* dict lists (the output of the
        per-entity transformers' `transform_*` methods), so this gold layer
        only does denormalization and never invents new schema decisions.

        Returns one row per payment (see module docstring for grain rules).
        """
        if not transformed_payments:
            logger.warning("No payments rows provided to PaymentsFactTransformer.build")
            return []

        orders_by_number = _index(transformed_event_orders, "order_number")
        events_by_id = _index(transformed_events, "event_id")
        contacts_by_id = _index(transformed_contacts, "contact_id")
        members_by_contact = _index(transformed_members, "contact_id")
        summaries_by_event = _index(transformed_order_summaries, "event_id")

        rows: List[Dict[str, Any]] = []
        unmatched_orders = 0
        unmatched_events = 0

        for payment in transformed_payments:
            wix_app_order = payment.get("wix_app_order_id")
            order = orders_by_number.get(wix_app_order, {}) if wix_app_order else {}
            if wix_app_order and not order:
                unmatched_orders += 1

            event_id = order.get("event_id")
            event = events_by_id.get(event_id, {}) if event_id else {}
            summary = summaries_by_event.get(event_id, {}) if event_id else {}
            if event_id and not event:
                unmatched_events += 1

            # Prefer event_orders.contact_id (canonical) but fall back to
            # nothing if the order didn't link a contact (Wix sometimes
            # anonymizes). Buyer email from the payment itself is still
            # captured below regardless of contact join success.
            contact_id = order.get("contact_id") or None
            contact = contacts_by_id.get(contact_id, {}) if contact_id else {}
            member = members_by_contact.get(contact_id, {}) if contact_id else {}

            # Member resolution priority: explicit member record > order's
            # member_id > contact's is_member flag. The latter two catch the
            # case where a contact has been linked to a Wix Member but the
            # member record itself didn't make it into this snapshot.
            member_id = (
                (member or {}).get("member_id")
                or order.get("member_id")
                or (contact or {}).get("member_id")
            )
            is_member = (
                _safe_bool(payment.get("is_member"))
                or _safe_bool((contact or {}).get("is_member"))
                or bool(member_id)
            )

            # Document where the join chain landed so analysts can filter to
            # fully-enriched rows or audit the unmatched ones.
            if not wix_app_order:
                enrichment_status = "no_order_id"
            elif not order:
                enrichment_status = "order_not_found"
            elif not event:
                enrichment_status = "event_not_found"
            elif not contact_id:
                enrichment_status = "no_contact_link"
            else:
                enrichment_status = "fully_enriched"

            rows.append(PaymentsFactTransformer._build_row(
                payment=payment,
                order=order,
                event=event,
                contact=contact,
                member=member,
                summary=summary,
                contact_id=contact_id,
                member_id=member_id,
                is_member=bool(is_member),
                enrichment_status=enrichment_status,
            ))

        logger.info(
            "Built payments_fact: %d payment rows "
            "(unmatched orders: %d, unmatched events: %d)",
            len(rows), unmatched_orders, unmatched_events,
        )
        return rows

    @staticmethod
    def _build_row(
        payment: Dict[str, Any],
        order: Dict[str, Any],
        event: Dict[str, Any],
        contact: Dict[str, Any],
        member: Dict[str, Any],
        summary: Dict[str, Any],
        contact_id: Optional[str],
        member_id: Optional[str],
        is_member: bool,
        enrichment_status: str,
    ) -> Dict[str, Any]:
        """Construct one payments_fact row by denormalizing all dimensions."""
        amount = _safe_float(payment.get("amount"))

        # Buyer identity: prefer the contact join (most authoritative) and
        # fall back to the cashier billing block when no contact was linked.
        first_name = (contact or {}).get("first_name") or payment.get("billing_first_name")
        last_name = (contact or {}).get("last_name") or payment.get("billing_last_name")
        full_name = (
            (contact or {}).get("full_name")
            or payment.get("billing_full_name")
            or _join_name(first_name, last_name)
        )
        email = (
            (contact or {}).get("primary_email")
            or (contact or {}).get("email")
            or payment.get("billing_email")
        )
        phone = (contact or {}).get("phone") or payment.get("billing_phone")

        return {
            # Grain identifiers - same primary key as silver payments
            "transaction_id": payment.get("transaction_id"),
            "provider_transaction_id": payment.get("provider_transaction_id"),
            "order_id": payment.get("order_id"),
            "wix_app_order_id": payment.get("wix_app_order_id"),
            "event_id": order.get("event_id"),
            "contact_id": contact_id,
            "member_id": member_id,
            # Diagnostics for failed joins
            "enrichment_status": enrichment_status,
            # Payment timing
            "payment_date": payment.get("payment_date"),
            "payment_time": payment.get("payment_time"),
            "payment_datetime": payment.get("payment_datetime"),
            # Money
            "currency": payment.get("currency"),
            "amount": amount,
            "platform_fee": payment.get("platform_fee"),
            "net_amount": payment.get("net_amount"),
            "tax": payment.get("tax"),
            "discount": payment.get("discount"),
            "amount_bucket": _bucket_amount(amount),
            # Status
            "status": payment.get("status"),
            "transaction_status": payment.get("transaction_status"),
            "transaction_type": payment.get("transaction_type"),
            "is_refundable": payment.get("is_refundable"),
            "failure_code": payment.get("failure_code"),
            # Provider / method
            "payment_provider": payment.get("payment_provider_friendly"),
            "payment_method": payment.get("payment_method"),
            "card_network": payment.get("card_network"),
            "card_last_four": payment.get("card_last_four"),
            # Refunds
            "refund_count": payment.get("refund_count"),
            "refund_succeeded_count": payment.get("refund_succeeded_count"),
            "refund_total_amount": payment.get("refund_total_amount"),
            "refund_status": payment.get("refund_status"),
            "refund_reason": payment.get("refund_reason"),
            "refund_date": payment.get("refund_date"),
            # Order line items (from cashier - no event join needed)
            "product_name": payment.get("product_name"),
            "product_count": payment.get("product_count"),
            "total_quantity": payment.get("total_quantity"),
            # Event dimensions (the whole point of this gold layer)
            "event_title": event.get("title"),
            "event_slug": event.get("slug"),
            "event_status": event.get("status"),
            "registration_type": event.get("registration_type"),
            "category_names": event.get("category_names"),
            "category_count": event.get("category_count"),
            "event_start_date": event.get("start_date"),
            "event_start_time": event.get("start_time"),
            "event_start_datetime": event.get("start_datetime"),
            "event_day_of_week": event.get("day_of_week"),
            "event_is_weekend": event.get("is_weekend"),
            "location_name": event.get("location_name"),
            "location_city": event.get("location_city"),
            "event_lowest_price": event.get("lowest_price"),
            "event_highest_price": event.get("highest_price"),
            # Event-level revenue context (useful for "this payment vs event avg" analyses)
            "event_total_orders": summary.get("total_orders"),
            "event_total_tickets": summary.get("total_tickets"),
            "event_total_sales": summary.get("total_sales_amount"),
            "event_avg_ticket_price": summary.get("avg_ticket_price"),
            # Order context (from event_orders silver)
            "order_channel": order.get("channel"),
            "order_status": order.get("status"),
            "order_tickets_quantity": order.get("tickets_quantity"),
            "order_ticket_names": order.get("ticket_names"),
            # Buyer / member identity
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "is_member": is_member,
            "member_signup_date": (member or {}).get("created_date"),
            "member_last_login_date": (member or {}).get("last_login_date"),
            # Pass-through billing (kept so the gold table is also a drop-in
            # replacement for the dashboard Payments CSV when a contact join
            # fails)
            "billing_city": payment.get("billing_city"),
            "billing_country": payment.get("billing_country"),
        }

    @staticmethod
    def save_to_csv(
        transformed_payments: List[Dict[str, Any]],
        output_path: str,
        encoding: str = "utf-8-sig",
        **kwargs,
    ) -> None:
        """Build the payments_fact rows and write them to CSV."""
        dimension_kwargs = {
            k: kwargs.pop(k, None)
            for k in (
                "transformed_event_orders",
                "transformed_events",
                "transformed_contacts",
                "transformed_members",
                "transformed_order_summaries",
            )
        }
        rows = PaymentsFactTransformer.build(transformed_payments, **dimension_kwargs)
        BaseTransformer.save_to_csv(rows, output_path, encoding=encoding, **kwargs)


def _index(items: Optional[Iterable[Dict[str, Any]]], key: str) -> Dict[str, Dict[str, Any]]:
    """Index a list of dicts by the given key. Later rows win on collision."""
    if not items:
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for item in items:
        k = item.get(key)
        if k:
            out[k] = item
    return out


def _join_name(first: Optional[str], last: Optional[str]) -> Optional[str]:
    parts = [p for p in (first, last) if p]
    return " ".join(parts) if parts else None
