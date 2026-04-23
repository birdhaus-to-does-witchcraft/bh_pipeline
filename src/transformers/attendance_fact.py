"""
Attendance fact (gold layer) transformer.

Builds a denormalized one-row-per-ticket-stub analytics table by joining the
silver layer entities (guests, payments, events, ticket_definitions, contacts,
members, order_summaries, tickets when available).

Grain rules (validated against the snapshot 2026-04-22)
-------------------------------------------------------
- Wix's Guest API returns one BUYER row per order PLUS one TICKET_HOLDER row
  per individual ticket stub. For a person buying 1 ticket for themselves you
  get 2 rows (BUYER + TICKET_HOLDER) representing 1 actual attendee.
- This transformer keeps one row per *ticket stub*: every TICKET_HOLDER row
  becomes one fact row, and every legacy RSVP row becomes one fact row. The
  BUYER row is collapsed into derived columns on each TH row (it is never an
  attendee on its own).
- BUYER-only orders (no TICKET_HOLDER row in the same orderNumber) are
  DROPPED rather than promoted to attendees - they are consistently failed /
  cancelled / refunded checkouts in the current snapshot.

Identity rule (Phase 1: kill the "Good Kids" substitution)
----------------------------------------------------------
- Wix substitutes the site-owner contact ("info@goodkids.ca") into the
  TICKET_HOLDER's contact_id whenever per-attendee identity isn't captured
  at checkout (~269 TH rows across 8 events in the current snapshot).
- The BUYER row's contact_id is NEVER Good Kids and is the real purchaser.
- This transformer therefore sources every attendee identity column
  (contact_id, first_name, last_name, full_name, email, phone) from the
  BUYER row of the same order_number. The TH row's original contact_id is
  preserved on the diagnostic columns `th_contact_id_raw` /
  `identity_source` so the substitution is auditable.

Refund / cancel filtering (Phase 2)
-----------------------------------
- For every TH row we look up the latest payment for its order_number.
- TH rows whose order's `payments.status` is in
  {REFUND, PARTIAL_REFUND, BUYER_CANCELED, DECLINED, FAILED, CHARGE_BACK}
  are dropped by default. Pass `include_inactive_orders=True` to keep them
  with the status column populated for auditing.
- Orders with no payment row at all (purely free / comp / RSVP) keep their
  rows; `order_payment_status` is set to None.

Headcount dedup (Phase 3: the user's generalized rule)
------------------------------------------------------
- For every order we derive `paid_tickets_per_order` from
  `payments.total_quantity` minus the synthetic "Application Fee" line
  (Wix tags it as `app_fee_item`, always quantity 1, always present on
  paid orders). The first N TH rows in the order (sorted by ticket_number
  for determinism) are flagged `is_paid_ticket_stub=True`; the rest are
  flagged False (they are free / comp / manually-added free-tier stubs).
- Then we group by (event_id, buyer_contact_id) and apply the user's rule:
    paid_th = sum(is_paid_ticket_stub)
    free_th = total_th - paid_th
    humans_at_event_for_buyer = paid_th if (paid_th > 0 and free_th > 0)
                                else max(paid_th, free_th)
- The first `humans_at_event_for_buyer` rows in the group (paid first,
  then by ticket_number) get `counts_as_human=True`; the rest are False.
  Downstream can do `WHERE counts_as_human` to get the canonical human
  count without further dedup.

Ticket-kind signals (Phase 4: surface, do not classify)
-------------------------------------------------------
- We explicitly do NOT classify tickets as "couples" vs "single" or assign
  a `seats_per_ticket` multiplier in the pipeline. Every signal that could
  feed such a classification is surfaced as a column instead, so the
  analyst downstream can decide based on whatever combination of
  td_name + td_fixed_price_value + td_initial_limit + event_total_capacity
  fits their question.
- Per-row signals are matched by parsing `payments.product_name` against
  `ticket_definitions.name` for the event. When the order has multiple
  line items, the columns reflect the whole order with comma joins and
  `td_match_confidence` records whether the match was exact / ambiguous.

Other dimensions
----------------
- Event dimensions (title, categories, date/time, location) from events.
- Contact dimensions (member_id, etc.) from contacts.
- Member dimensions (is_member, signup) from members. Membership lookup
  always keys on the BUYER's contact_id, never on the TH's; plus-one
  seats inherit the buyer's status with `is_partner_seat=True`.
- Pricing fallback chain: order_status FREE -> $0; ticket.price_value;
  ticket_definition.fixed_price_value; order_summaries.avg_ticket_price.

Things that do NOT work in the current Wix snapshot
---------------------------------------------------
- `tickets` table: all join keys are 0% populated; effectively unjoinable.
  The forward-compatible joins remain so it auto-fills the day Wix fixes
  the API.
- `event_orders.status` and `event_orders.anonymized` are uniformly broken
  (`NA_ORDER_STATUS`, `False`); we ignore them.
- `coupons` cannot be linked to a specific order, so coupon attribution
  is impossible at the row level.
- `rsvp_events` are historical (Ticket Tuesday era) and have no guests
  rows; nothing to attribute. The RSVP code path below is preserved but
  is dead code on every snapshot since RSVPs were retired.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

from transformers.base import BaseTransformer

logger = logging.getLogger(__name__)


# Payment statuses that mean "this order should not count toward attendance".
# Mirrors the same set used by the Wix dashboard's attendance views.
INACTIVE_PAYMENT_STATUSES = frozenset({
    "REFUND",
    "PARTIAL_REFUND",
    "BUYER_CANCELED",
    "DECLINED",
    "FAILED",
    "CHARGE_BACK",
    "VOID",
    "EXPIRED",
})

# Wix tags the per-order processing fee with this synthetic line item id.
# It always carries quantity=1 and inflates payments.total_quantity by 1
# whenever a paid order exists. We subtract it when deriving paid ticket
# count.
APP_FEE_LABEL = "Application Fee"


def _bucket_price(value: Optional[float], free_flag: Optional[bool]) -> str:
    """Categorize ticket price into a filterable band."""
    if free_flag is True:
        return "Free"
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
    return "100+"


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


def _safe_int(value: Any) -> Optional[int]:
    f = _safe_float(value)
    if f is None:
        return None
    return int(f)


_TRUE_STRINGS = {"true", "1", "yes", "t", "y"}
_FALSE_STRINGS = {"false", "0", "no", "f", "n", "", "nan", "none", "null"}


def _safe_bool(value: Any) -> Optional[bool]:
    """
    Coerce a value to a true/false/None tri-state.

    Robust to stringy inputs from CSV reads (e.g. "True", "False", "nan"),
    which would otherwise be silently truthy under plain ``bool()``.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if value != value:  # NaN
            return None
        return bool(value)
    if isinstance(value, str):
        s = value.strip().lower()
        if s in _TRUE_STRINGS:
            return True
        if s in _FALSE_STRINGS:
            return None if s in {"", "nan", "none", "null"} else False
    return bool(value)


def _paid_tickets_from_payment(payment: Optional[Dict[str, Any]]) -> int:
    """
    Derive paid ticket count for an order from its payment row.

    Wix's silver `payments.total_quantity` already excludes the SERVICE_FEE
    line but still counts the synthetic "Application Fee" line (item id
    `app_fee_item`, always qty=1). We subtract that here so the count is
    just the number of physically-bought ticket stubs.

    Returns 0 when there's no payment row (the order is purely free/comp).
    """
    if not payment:
        return 0
    qty = _safe_int(payment.get("total_quantity"))
    if qty is None:
        return 0
    product_name = payment.get("product_name") or ""
    if APP_FEE_LABEL in product_name:
        qty = max(0, qty - 1)
    return qty


def _ticket_number_sort_key(ticket_number: Optional[str]) -> Tuple[int, str]:
    """Stable sort key for ticket numbers; pushes Nones to the end."""
    if not ticket_number:
        return (1, "")
    return (0, str(ticket_number))


class AttendanceFactTransformer(BaseTransformer):
    """Build the attendance_fact gold table from already-transformed silver dicts."""

    @staticmethod
    def build(
        transformed_guests: List[Dict[str, Any]],
        transformed_events: Optional[List[Dict[str, Any]]] = None,
        transformed_contacts: Optional[List[Dict[str, Any]]] = None,
        transformed_members: Optional[List[Dict[str, Any]]] = None,
        transformed_ticket_definitions: Optional[List[Dict[str, Any]]] = None,
        transformed_tickets: Optional[List[Dict[str, Any]]] = None,
        transformed_order_summaries: Optional[List[Dict[str, Any]]] = None,
        transformed_payments: Optional[List[Dict[str, Any]]] = None,
        include_inactive_orders: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Build attendance_fact rows from the silver layer.

        All inputs are *already-transformed* dict lists (the output of the
        per-entity transformers' `transform_*` methods), so this gold layer
        only does denormalization, identity normalization, and grain
        selection - no schema decisions.

        :param include_inactive_orders: when True, keep rows whose order is
            REFUND/CANCELED/etc. (with `order_payment_status` populated)
            for auditing. Default False drops them.

        Returns one row per ticket stub (see module docstring).
        """
        events_by_id = _index(transformed_events, "event_id")
        contacts_by_id = _index(transformed_contacts, "contact_id")
        members_by_contact = _index(transformed_members, "contact_id")
        defs_by_id = _index(transformed_ticket_definitions, "definition_id")
        summaries_by_event = _index(transformed_order_summaries, "event_id")

        # Group ticket definitions by event so we can match payment line
        # items to the right def per row.
        defs_by_event: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for d in transformed_ticket_definitions or []:
            ev = d.get("event_id")
            if ev:
                defs_by_event[ev].append(d)

        # Per-event capacity = sum of initial_limit across all defs for
        # that event. Surfaces as `event_total_capacity` so downstream can
        # spot small/private classes (often the couples-ticket pattern).
        event_total_capacity: Dict[str, Optional[int]] = {}
        event_distinct_td_count: Dict[str, int] = {}
        for ev, defs in defs_by_event.items():
            limits = [_safe_int(d.get("initial_limit")) for d in defs]
            limits = [x for x in limits if x is not None]
            event_total_capacity[ev] = sum(limits) if limits else None
            event_distinct_td_count[ev] = len(defs)

        # Index payments by wix_app_order_id, keeping the latest row per
        # order. The "latest" wins so a successful sale beats an earlier
        # failed attempt for the same order.
        payments_by_order: Dict[str, Dict[str, Any]] = {}
        for p in transformed_payments or []:
            order = p.get("wix_app_order_id")
            if not order:
                continue
            existing = payments_by_order.get(order)
            if existing is None:
                payments_by_order[order] = p
                continue
            # Prefer APPROVED over anything else; otherwise keep the most
            # recent createdAt.
            if (p.get("status") == "APPROVED" and existing.get("status") != "APPROVED"):
                payments_by_order[order] = p
                continue
            if (
                p.get("payment_datetime") and existing.get("payment_datetime")
                and str(p["payment_datetime"]) > str(existing["payment_datetime"])
            ):
                payments_by_order[order] = p

        # Tickets: index by ticket_number for direct lookup, and group by
        # (event_id, order_number) as a fallback when guests lack ticket_number.
        tickets_by_number: Dict[str, Dict[str, Any]] = {}
        tickets_by_order: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
        for t in transformed_tickets or []:
            tn = t.get("ticket_number")
            if tn:
                tickets_by_number[tn] = t
            key = (t.get("event_id"), t.get("order_number"))
            if all(key):
                tickets_by_order[key].append(t)

        # Group guests by orderNumber to apply the BUYER/TICKET_HOLDER grain rule
        guests_by_order: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        orphan_guests: List[Dict[str, Any]] = []  # rows without an orderNumber
        for g in transformed_guests:
            order = g.get("order_number")
            if order:
                guests_by_order[order].append(g)
            else:
                orphan_guests.append(g)

        # ------------------------------------------------------------------
        # First pass: build "raw rows" with all order-level context attached
        # but BEFORE the per-(event, buyer) dedup pass.
        # ------------------------------------------------------------------
        raw_rows: List[Dict[str, Any]] = []
        dropped_buyer_count = 0
        skipped_buyer_only_orders: List[str] = []
        dropped_inactive_counts: Dict[str, int] = defaultdict(int)

        for order, group in guests_by_order.items():
            buyers = [g for g in group if g.get("guest_type") == "BUYER"]
            holders = [g for g in group if g.get("guest_type") == "TICKET_HOLDER"]
            rsvps = [g for g in group if g.get("guest_type") == "RSVP"]

            buyer = buyers[0] if buyers else {}
            buyer_contact_id = buyer.get("contact_id")

            # Sort holders deterministically by ticket_number so the
            # paid-vs-free flagging is reproducible.
            holders = sorted(
                holders, key=lambda g: _ticket_number_sort_key(g.get("ticket_number"))
            )
            tickets_in_order = len(holders) if holders else None

            # Look up the order's latest payment status + paid ticket count.
            payment = payments_by_order.get(order, {})
            order_payment_status = payment.get("status") if payment else None
            paid_tickets_per_order = _paid_tickets_from_payment(payment)

            is_inactive = order_payment_status in INACTIVE_PAYMENT_STATUSES
            if is_inactive and not include_inactive_orders:
                dropped_inactive_counts[order_payment_status] += len(holders) + len(rsvps)
                dropped_buyer_count += len(buyers)
                continue

            if not (holders or rsvps):
                # BUYER-only order: most likely failed / cancelled / refunded
                # checkout that didn't show up as REFUND in payments either.
                # Skip, log, revisit only when per-event order extraction
                # gives us a real status field.
                dropped_buyer_count += len(buyers)
                skipped_buyer_only_orders.append(order)
                continue

            # Tag each TH as paid or free. The first `paid_tickets_per_order`
            # holders (after deterministic sort) are paid; the rest are
            # free / comp / manually-added free-tier stubs.
            for idx, th in enumerate(holders):
                th["_is_paid_stub"] = idx < paid_tickets_per_order

            # Build the per-row context shared across all holders/rsvps in
            # this order (buyer identity, payment status, paid count).
            shared = {
                "buyer": buyer,
                "buyer_contact_id": buyer_contact_id,
                "tickets_in_order": tickets_in_order,
                "order_payment_status": order_payment_status,
                "paid_tickets_per_order": paid_tickets_per_order,
                "payment": payment,
            }

            for guest in holders + rsvps:
                raw_rows.append({
                    "guest": guest,
                    "shared": shared,
                })
            dropped_buyer_count += len(buyers)

        # Orphans (no orderNumber): include as-is; can't compute buyer context
        for guest in orphan_guests:
            if guest.get("guest_type") == "BUYER":
                # Same dedup principle: drop standalone BUYER orphans
                dropped_buyer_count += 1
                continue
            raw_rows.append({
                "guest": guest,
                "shared": {
                    "buyer": {},
                    "buyer_contact_id": None,
                    "tickets_in_order": None,
                    "order_payment_status": None,
                    "paid_tickets_per_order": 0,
                    "payment": {},
                },
            })

        # ------------------------------------------------------------------
        # Second pass: per-(event, buyer_contact_id) dedup. Compute
        # `humans_at_event_for_buyer` and the per-row `counts_as_human`
        # flag using the user's generalized rule.
        # ------------------------------------------------------------------
        groups: Dict[Tuple[Optional[str], Optional[str]], List[Dict[str, Any]]] = defaultdict(list)
        for raw in raw_rows:
            guest = raw["guest"]
            shared = raw["shared"]
            key = (guest.get("event_id"), shared.get("buyer_contact_id"))
            groups[key].append(raw)

        # Flag rows in place
        for key, rows_in_group in groups.items():
            event_id, buyer_contact_id = key

            # RSVP rows are handled separately - each is one human, no dedup.
            rsvp_rows = [r for r in rows_in_group if r["guest"].get("guest_type") == "RSVP"]
            th_rows = [r for r in rows_in_group if r["guest"].get("guest_type") == "TICKET_HOLDER"]

            paid_th = sum(1 for r in th_rows if r["guest"].get("_is_paid_stub"))
            free_th = len(th_rows) - paid_th

            if paid_th > 0 and free_th > 0:
                # Mixed: same contact has paid AND free at this event.
                # Treat them as the same human(s); plus-ones come from the
                # paid count only. This collapses Bound Together's manually
                # added free Discussion stubs into the paid Jam stubs.
                humans_at_event = paid_th
            else:
                humans_at_event = max(paid_th, free_th)

            # Sort within the group: paid first, then by ticket_number.
            # First `humans_at_event` get counts_as_human=True.
            th_rows_sorted = sorted(
                th_rows,
                key=lambda r: (
                    0 if r["guest"].get("_is_paid_stub") else 1,
                    _ticket_number_sort_key(r["guest"].get("ticket_number")),
                ),
            )
            for i, r in enumerate(th_rows_sorted):
                guest = r["guest"]
                guest["_counts_as_human"] = i < humans_at_event
                guest["_humans_at_event_for_buyer"] = humans_at_event
                # First TH row in this group is the buyer's own seat (or
                # at least the seat we're calling theirs). Subsequent
                # counts_as_human seats are partner / plus-one seats.
                guest["_is_partner_seat"] = (
                    i > 0 and guest["_counts_as_human"]
                )

            # RSVP rows: treat each as one human, not a partner seat,
            # never deduplicated against TH (they are a separate legacy
            # population on a disjoint event set).
            for r in rsvp_rows:
                guest = r["guest"]
                guest["_counts_as_human"] = True
                guest["_humans_at_event_for_buyer"] = humans_at_event + len(rsvp_rows)
                guest["_is_partner_seat"] = False

        # ------------------------------------------------------------------
        # Third pass: build final rows with all dimensions denormalized.
        # ------------------------------------------------------------------
        attendee_rows: List[Dict[str, Any]] = []
        for raw in raw_rows:
            attendee_rows.append(
                AttendanceFactTransformer._build_row(
                    guest=raw["guest"],
                    shared=raw["shared"],
                    events_by_id=events_by_id,
                    contacts_by_id=contacts_by_id,
                    members_by_contact=members_by_contact,
                    defs_by_id=defs_by_id,
                    defs_by_event=defs_by_event,
                    event_total_capacity=event_total_capacity,
                    event_distinct_td_count=event_distinct_td_count,
                    tickets_by_number=tickets_by_number,
                    tickets_by_order=tickets_by_order,
                    summaries_by_event=summaries_by_event,
                )
            )

        logger.info(
            "Built attendance_fact: %d ticket-stub rows "
            "(dropped %d redundant BUYER rows, "
            "skipped %d BUYER-only orders as likely-failed checkouts, "
            "kept %d orphans)",
            len(attendee_rows),
            dropped_buyer_count,
            len(skipped_buyer_only_orders),
            len([g for g in orphan_guests if g.get("guest_type") != "BUYER"]),
        )
        if dropped_inactive_counts:
            summary = ", ".join(
                f"{status}={count}" for status, count in sorted(dropped_inactive_counts.items())
            )
            logger.info(
                "Dropped %d ticket stubs from refunded/canceled orders (%s); "
                "pass include_inactive_orders=True to retain for auditing",
                sum(dropped_inactive_counts.values()),
                summary,
            )
        if skipped_buyer_only_orders:
            preview = ", ".join(skipped_buyer_only_orders[:10])
            suffix = "" if len(skipped_buyer_only_orders) <= 10 else f" (+{len(skipped_buyer_only_orders) - 10} more)"
            logger.warning(
                "Skipped BUYER-only orders (no TICKET_HOLDER record - revisit "
                "once per-event order extraction returns real status field): %s%s",
                preview,
                suffix,
            )
        return attendee_rows

    @staticmethod
    def _build_row(
        guest: Dict[str, Any],
        shared: Dict[str, Any],
        events_by_id: Dict[str, Dict[str, Any]],
        contacts_by_id: Dict[str, Dict[str, Any]],
        members_by_contact: Dict[str, Dict[str, Any]],
        defs_by_id: Dict[str, Dict[str, Any]],
        defs_by_event: Dict[str, List[Dict[str, Any]]],
        event_total_capacity: Dict[str, Optional[int]],
        event_distinct_td_count: Dict[str, int],
        tickets_by_number: Dict[str, Dict[str, Any]],
        tickets_by_order: Dict[tuple, List[Dict[str, Any]]],
        summaries_by_event: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Construct one attendance_fact row by denormalizing all dimensions."""
        event_id = guest.get("event_id")
        order_number = guest.get("order_number")

        buyer = shared.get("buyer") or {}
        buyer_contact_id = shared.get("buyer_contact_id")
        payment = shared.get("payment") or {}
        order_payment_status = shared.get("order_payment_status")
        paid_tickets_per_order = shared.get("paid_tickets_per_order") or 0

        # ----- Identity (Phase 1: always from BUYER, never from TH) -----
        # Capture the original TH-side identity for diagnostics so any
        # future regression in Wix's TH-substitution behavior is auditable.
        th_contact_id_raw = guest.get("contact_id")

        if buyer_contact_id:
            # Use buyer's identity; fall back to contacts join for any gaps.
            buyer_contact = contacts_by_id.get(buyer_contact_id, {}) if buyer_contact_id else {}
            contact_id = buyer_contact_id
            first_name = buyer.get("first_name") or buyer_contact.get("first_name")
            last_name = buyer.get("last_name") or buyer_contact.get("last_name")
            full_name = (
                buyer.get("full_name")
                or buyer_contact.get("full_name")
                or _join_name(first_name, last_name)
            )
            email = (
                buyer.get("email")
                or buyer_contact.get("primary_email")
                or buyer_contact.get("email")
            )
            phone = buyer.get("phone") or buyer_contact.get("phone")

            if th_contact_id_raw == buyer_contact_id:
                identity_source = "th_matches_buyer"
            elif th_contact_id_raw is None:
                identity_source = "buyer"
            else:
                identity_source = "buyer_overrides_th_goodkids"
        else:
            # Orphan TH row with no BUYER context. Fall back to the TH's
            # own identity (and the contacts join). This is the only path
            # where Good Kids could leak through, and only for the small
            # number of orphan rows.
            contact_id = th_contact_id_raw
            contact = contacts_by_id.get(contact_id, {}) if contact_id else {}
            first_name = guest.get("first_name") or contact.get("first_name")
            last_name = guest.get("last_name") or contact.get("last_name")
            full_name = (
                guest.get("full_name")
                or contact.get("full_name")
                or _join_name(first_name, last_name)
            )
            email = guest.get("email") or contact.get("primary_email") or contact.get("email")
            phone = guest.get("phone") or contact.get("phone")
            identity_source = "orphan_no_buyer"

        # The contact whose membership status drives this row's
        # is_member flag (Phase 5: always the buyer).
        member_contact_id = buyer_contact_id or contact_id
        member_record = members_by_contact.get(member_contact_id, {}) if member_contact_id else {}
        member_contact = contacts_by_id.get(member_contact_id, {}) if member_contact_id else {}

        member_id = (
            member_record.get("member_id")
            or buyer.get("member_id")
            or member_contact.get("member_id")
        )
        is_member = bool(
            _safe_bool(buyer.get("is_member"))
            or _safe_bool(member_contact.get("is_member"))
            or member_id
        )

        event = events_by_id.get(event_id, {}) if event_id else {}
        summary = summaries_by_event.get(event_id, {}) if event_id else {}

        # ----- Optional ticket join (currently dead - tickets table empty) -----
        ticket: Dict[str, Any] = {}
        ticket_number = guest.get("ticket_number") or guest.get("primary_ticket_number")
        if ticket_number and ticket_number in tickets_by_number:
            ticket = tickets_by_number[ticket_number]
        elif event_id and order_number:
            order_tickets = tickets_by_order.get((event_id, order_number), [])
            if len(order_tickets) == 1:
                ticket = order_tickets[0]

        ticket_definition_id = (
            ticket.get("ticket_definition_id")
            or guest.get("primary_ticket_definition_id")
        )
        definition = defs_by_id.get(ticket_definition_id, {}) if ticket_definition_id else {}

        # ----- Phase 4: surface ticket-definition signals (no inference) -----
        td_signals = AttendanceFactTransformer._match_ticket_definitions(
            payment=payment,
            event_id=event_id,
            defs_by_event=defs_by_event,
        )

        # ----- Pricing resolution -----
        order_status_raw = (guest.get("order_status") or "").upper()
        price_value: Optional[float] = None
        price_currency = ticket.get("price_currency")
        price_source = "unknown"

        if order_status_raw == "FREE":
            price_value = 0.0
            price_currency = (
                price_currency
                or definition.get("fixed_price_currency")
                or summary.get("total_sales_currency")
                or event.get("currency")
            )
            price_source = "order_status"
        else:
            price_value = _safe_float(ticket.get("price_value"))
            if price_value is not None:
                price_source = "ticket"
            if price_value is None:
                def_price = _safe_float(definition.get("fixed_price_value"))
                if def_price is not None:
                    price_value = def_price
                    price_currency = price_currency or definition.get("fixed_price_currency")
                    price_source = "ticket_definition"
            if price_value is None and td_signals["td_fixed_price_value"] is not None:
                price_value = td_signals["td_fixed_price_value"]
                price_source = "td_match"
            if price_value is None:
                avg = _safe_float(summary.get("avg_ticket_price"))
                if avg is not None:
                    price_value = avg
                    price_currency = price_currency or summary.get("total_sales_currency")
                    price_source = "event_average"

        # ----- Free flag -----
        order_status = (guest.get("order_status") or "").upper()
        if order_status == "FREE":
            free_flag: Optional[bool] = True
        elif order_status == "PAID":
            free_flag = False
        else:
            free_flag = _safe_bool(ticket.get("free"))
            if free_flag is None:
                free_flag = _safe_bool(definition.get("free"))
            if free_flag is None and price_value is not None:
                free_flag = price_value == 0

        # ----- Check-in -----
        checked_in = _safe_bool(ticket.get("checked_in"))
        if checked_in is None:
            checked_in = _safe_bool(guest.get("checked_in"))
        check_in_date = ticket.get("check_in_date")
        check_in_time = ticket.get("check_in_time")

        was_buyer = bool(buyer_contact_id and contact_id and contact_id == buyer_contact_id)

        # ----- Phase 3 dedup outputs (set by the second pass) -----
        is_paid_ticket_stub = guest.get("_is_paid_stub")
        if is_paid_ticket_stub is None:
            # RSVPs and orphans don't have the flag; treat as None.
            is_paid_ticket_stub = None
        counts_as_human = guest.get("_counts_as_human")
        humans_at_event_for_buyer = guest.get("_humans_at_event_for_buyer")
        is_partner_seat = bool(guest.get("_is_partner_seat"))

        return {
            # ----- Grain identifiers -----
            "guest_id": guest.get("guest_id"),
            "event_id": event_id,
            "contact_id": contact_id,
            "buyer_contact_id": buyer_contact_id,
            "th_contact_id_raw": th_contact_id_raw,
            "identity_source": identity_source,
            "order_number": order_number,
            "ticket_number": ticket.get("ticket_number") or ticket_number,
            "ticket_definition_id": ticket_definition_id,
            # ----- Role within order -----
            "guest_type": guest.get("guest_type"),
            "was_buyer": was_buyer,
            "tickets_in_order": shared.get("tickets_in_order"),
            "attendance_status": guest.get("attendance_status"),
            # The most authoritative paid/free signal Wix gives us per row,
            # though it is order-level (FREE applies to the whole order).
            "order_status": guest.get("order_status"),
            # ----- Phase 2: refund / cancel state -----
            "order_payment_status": order_payment_status,
            "paid_tickets_per_order": shared.get("paid_tickets_per_order"),
            # ----- Phase 3: per-row paid/free + dedup -----
            "is_paid_ticket_stub": is_paid_ticket_stub,
            "humans_at_event_for_buyer": humans_at_event_for_buyer,
            "counts_as_human": counts_as_human,
            "is_partner_seat": is_partner_seat,
            # ----- Check-in -----
            "checked_in": checked_in,
            "check_in_date": check_in_date,
            "check_in_time": check_in_time,
            # ----- Event dimensions -----
            "event_title": event.get("title"),
            "event_slug": event.get("slug"),
            "event_status": event.get("status"),
            "registration_type": event.get("registration_type"),
            "category_names": event.get("category_names"),
            "category_count": event.get("category_count"),
            "start_date": event.get("start_date"),
            "start_time": event.get("start_time"),
            "start_datetime": event.get("start_datetime"),
            "day_of_week": event.get("day_of_week"),
            "is_weekend": event.get("is_weekend"),
            "location_name": event.get("location_name"),
            "location_city": event.get("location_city"),
            "event_lowest_price": event.get("lowest_price"),
            "event_highest_price": event.get("highest_price"),
            "event_currency": event.get("currency"),
            # ----- Phase 4: raw classification signals (no inference) -----
            "td_name": td_signals["td_name"],
            "td_fixed_price_value": td_signals["td_fixed_price_value"],
            "td_pricing_type": td_signals["td_pricing_type"],
            "td_initial_limit": td_signals["td_initial_limit"],
            "td_actual_limit": td_signals["td_actual_limit"],
            "td_limit_per_checkout": td_signals["td_limit_per_checkout"],
            "td_match_confidence": td_signals["td_match_confidence"],
            "event_total_capacity": event_total_capacity.get(event_id),
            "event_distinct_td_count": event_distinct_td_count.get(event_id),
            # ----- Pricing -----
            "ticket_name": (
                ticket.get("ticket_name")
                or guest.get("primary_ticket_name")
                or definition.get("name")
                or td_signals["td_name"]
            ),
            "price_value": price_value,
            "price_currency": price_currency,
            "price_source": price_source,
            "paid_bucket": _bucket_price(price_value, free_flag),
            "free": free_flag,
            "def_pricing_type": definition.get("pricing_type"),
            "def_fee_type": definition.get("fee_type"),
            "def_sale_status": definition.get("sale_status"),
            # ----- Identity (BUYER-sourced; TH override captured above) -----
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "is_member": is_member,
            "member_id": member_id,
            "member_signup_date": member_record.get("created_date"),
            "member_last_login_date": member_record.get("last_login_date"),
            # ----- Timing -----
            "registered_date": guest.get("created_date"),
            "registered_time": guest.get("created_time"),
        }

    @staticmethod
    def _match_ticket_definitions(
        payment: Optional[Dict[str, Any]],
        event_id: Optional[str],
        defs_by_event: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """
        Match an order's payment.product_name against the event's
        ticket_definitions to surface raw classification signals.

        Returns a dict of `td_*` columns. When the order has multiple
        line items (ambiguous match), the columns concatenate values
        with ", " and `td_match_confidence` is "ambiguous". When no
        match, all columns are None and `td_match_confidence` is "none".
        """
        empty = {
            "td_name": None,
            "td_fixed_price_value": None,
            "td_pricing_type": None,
            "td_initial_limit": None,
            "td_actual_limit": None,
            "td_limit_per_checkout": None,
            "td_match_confidence": "none",
        }
        if not event_id or not payment:
            return empty
        defs = defs_by_event.get(event_id) or []
        if not defs:
            return empty
        product_name = (payment.get("product_name") or "").lower()
        if not product_name:
            return empty

        matches: List[Dict[str, Any]] = []
        for d in defs:
            name = (d.get("name") or "").strip().lower()
            if name and name in product_name:
                matches.append(d)
        if not matches:
            return empty

        confidence = "exact" if len(matches) == 1 else "ambiguous"

        def _join_str(values: List[Any]) -> Optional[str]:
            cleaned = [str(v) for v in values if v not in (None, "")]
            if not cleaned:
                return None
            return cleaned[0] if len(cleaned) == 1 else ", ".join(cleaned)

        def _first_or_none(values: List[Any]) -> Any:
            for v in values:
                if v not in (None, ""):
                    return v
            return None

        names = [d.get("name") for d in matches]
        prices = [_safe_float(d.get("fixed_price_value")) for d in matches]
        pricing_types = [d.get("pricing_type") for d in matches]
        init_limits = [_safe_int(d.get("initial_limit")) for d in matches]
        actual_limits = [_safe_int(d.get("actual_limit")) for d in matches]
        per_checkout = [_safe_int(d.get("limit_per_checkout")) for d in matches]

        # For numeric columns prefer the single value when only one match,
        # otherwise expose them comma-joined so analysts see the full set.
        def _numeric_join(values: List[Optional[float]]) -> Any:
            non_null = [v for v in values if v is not None]
            if not non_null:
                return None
            if len(non_null) == 1 or len(matches) == 1:
                return non_null[0]
            return ", ".join(str(v) for v in non_null)

        return {
            "td_name": _join_str(names),
            "td_fixed_price_value": _numeric_join(prices),
            "td_pricing_type": _join_str(pricing_types),
            "td_initial_limit": _numeric_join(init_limits),
            "td_actual_limit": _numeric_join(actual_limits),
            "td_limit_per_checkout": _numeric_join(per_checkout),
            "td_match_confidence": confidence,
        }

    @staticmethod
    def save_to_csv(
        transformed_guests: List[Dict[str, Any]],
        output_path: str,
        encoding: str = "utf-8-sig",
        **kwargs,
    ):
        """Build the attendance_fact rows and write them to CSV."""
        dimension_kwargs = {
            k: kwargs.pop(k, None)
            for k in (
                "transformed_events",
                "transformed_contacts",
                "transformed_members",
                "transformed_ticket_definitions",
                "transformed_tickets",
                "transformed_order_summaries",
                "transformed_payments",
            )
        }
        include_inactive = kwargs.pop("include_inactive_orders", False)
        rows = AttendanceFactTransformer.build(
            transformed_guests,
            include_inactive_orders=include_inactive,
            **dimension_kwargs,
        )
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
