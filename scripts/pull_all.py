"""
Full data extraction script - pulls all data from Wix APIs.

Pipeline architecture:
- Bronze layer: raw JSON dumps to data/raw/<entity>/year=Y/month=M/day=D/snapshot_<ts>.json
- Silver layer: flattened CSVs in data/processed/<entity>_<ts>.csv (UTF-8 BOM for Excel)
- Per-run manifest at data/processed/manifest_<ts>.json with row counts, durations, errors

Entities pulled:
- Events (TICKETING + RSVP)
- Event Guests, RSVPs
- Tickets (joined with Ticket Definitions for fee_type, sale_status, sold_count)
- Ticket Definitions (with SALES_DETAILS fieldset)
- Contacts, Site Members
- Order Summaries (per event), Event Orders
- Payments (cashier transactions - mirrors the dashboard "Payments" CSV)
- Form Submissions (wide AND long format)
- Coupons (active + expired), Automations

Usage:
    python scripts/pull_all.py
    python scripts/pull_all.py --output-dir /path/to/output
    # Or if installed: wix-pull-all
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from utils.logger import setup_logging
from utils.raw_storage import dump_raw
from utils.manifest import RunManifest
from wix_api.client import WixAPIClient
from wix_api.events import EventsAPI
from wix_api.contacts import ContactsAPI
from wix_api.guests import GuestsAPI
from wix_api.orders import OrdersAPI
from wix_api.tickets import TicketsAPI
from wix_api.ticket_definitions import TicketDefinitionsAPI
from wix_api.rsvp import RSVPAPI
from wix_api.members import MembersAPI
from wix_api.forms import FormsAPI
from wix_api.coupons import CouponsAPI
from wix_api.automations import AutomationsAPI
from wix_api.payments import PaymentsAPI
from transformers.events import EventsTransformer
from transformers.contacts import ContactsTransformer
from transformers.guests import GuestsTransformer
from transformers.order_summaries import OrderSummariesTransformer
from transformers.event_orders import EventOrdersTransformer
from transformers.members import MembersTransformer
from transformers.form_submissions import FormSubmissionsTransformer
from transformers.coupons import CouponsTransformer
from transformers.automations import AutomationsTransformer
from transformers.payments import PaymentsTransformer
from transformers.rsvps import RSVPsTransformer
from transformers.tickets import TicketsTransformer
from transformers.ticket_definitions import TicketDefinitionsTransformer
from transformers.attendance_fact import AttendanceFactTransformer
from transformers.payments_fact import PaymentsFactTransformer
from transformers.base import BaseTransformer


def extract_events(client, output_dir, raw_dir, manifest, logger, timestamp):
    """
    Extract all events (TICKETING + RSVP).

    Returns a (ticketing_raw, rsvp_raw, ticketing_transformed) tuple. The
    transformed list is reused by the gold attendance_fact step downstream.
    """
    logger.info("=" * 60)
    logger.info("Extracting Events")
    logger.info("=" * 60)

    with manifest.timer("events") as timer:
        try:
            events_api = EventsAPI(client)
            all_events = events_api.get_all_events()
            logger.info(f"Retrieved {len(all_events)} total events")

            raw_path = dump_raw("events", all_events, timestamp, raw_dir)

            ticketing_events = [
                e for e in all_events
                if e.get('registration', {}).get('type') == 'TICKETING'
            ]
            rsvp_events = [
                e for e in all_events
                if e.get('registration', {}).get('type') == 'RSVP'
            ]
            other_count = len(all_events) - len(ticketing_events) - len(rsvp_events)
            logger.info(
                f"Split: {len(ticketing_events)} TICKETING, "
                f"{len(rsvp_events)} RSVP, {other_count} other"
            )

            extra_paths = {}
            csv_path = None
            ticketing_transformed: list = []

            if ticketing_events:
                csv_path = output_dir / f"events_{timestamp}.csv"
                ticketing_transformed = EventsTransformer.transform_events(ticketing_events)
                BaseTransformer.save_to_csv(ticketing_transformed, str(csv_path))
                logger.info(f"Saved {len(ticketing_transformed)} ticketing events to {csv_path.name}")

            if rsvp_events:
                rsvp_csv_path = output_dir / f"rsvp_events_{timestamp}.csv"
                EventsTransformer.save_to_csv(rsvp_events, str(rsvp_csv_path))
                logger.info(f"Saved {len(rsvp_events)} RSVP events to {rsvp_csv_path.name}")
                extra_paths["rsvp_events_csv"] = rsvp_csv_path

            if not ticketing_events and not rsvp_events:
                timer.record(status="skipped", row_count=0, raw_path=raw_path)
                return None, None, []

            timer.record(
                status="success",
                row_count=len(ticketing_events) + len(rsvp_events),
                raw_path=raw_path,
                csv_path=csv_path,
                extra_paths=extra_paths,
            )
            return ticketing_events, rsvp_events, ticketing_transformed

        except Exception as e:
            logger.error(f"Events extraction failed: {e}", exc_info=True)
            timer.record(status="failed", error=str(e))
            return None, None, []


def extract_contacts(client, output_dir, raw_dir, manifest, logger, timestamp):
    """
    Extract and transform all contacts.

    Returns a (raw_contacts, transformed_contacts) tuple. Raw is reused by
    the guests step for contactId-based enrichment (which reads nested
    info.name / info.emails). Transformed feeds the gold attendance_fact step.
    """
    logger.info("=" * 60)
    logger.info("Extracting Contacts")
    logger.info("=" * 60)

    with manifest.timer("contacts") as timer:
        try:
            contacts_api = ContactsAPI(client)
            contacts = contacts_api.get_all_contacts()
            logger.info(f"Retrieved {len(contacts)} contacts")

            raw_path = dump_raw("contacts", contacts, timestamp, raw_dir)

            if not contacts:
                logger.warning("No contacts found")
                timer.record(status="skipped", row_count=0, raw_path=raw_path)
                return None, []

            transformed = ContactsTransformer.transform_contacts(contacts)
            csv_path = output_dir / f"contacts_{timestamp}.csv"
            BaseTransformer.save_to_csv(transformed, str(csv_path))
            logger.info(f"Saved {len(transformed)} contacts to {csv_path.name}")

            timer.record(
                status="success",
                row_count=len(transformed),
                raw_path=raw_path,
                csv_path=csv_path,
            )
            return contacts, transformed

        except Exception as e:
            logger.error(f"Contacts extraction failed: {e}", exc_info=True)
            timer.record(status="failed", error=str(e))
            return None, []


def extract_members(client, output_dir, raw_dir, manifest, logger, timestamp):
    """Extract, transform, and return all site members (transformed dicts)."""
    logger.info("=" * 60)
    logger.info("Extracting Site Members")
    logger.info("=" * 60)

    with manifest.timer("members") as timer:
        try:
            members_api = MembersAPI(client)
            members = members_api.get_all_members()
            logger.info(f"Retrieved {len(members)} members")

            raw_path = dump_raw("members", members, timestamp, raw_dir)

            if not members:
                logger.warning("No members found")
                timer.record(status="skipped", row_count=0, raw_path=raw_path)
                return None

            transformed = MembersTransformer.transform_members(members)
            csv_path = output_dir / f"members_{timestamp}.csv"
            BaseTransformer.save_to_csv(transformed, str(csv_path))
            logger.info(f"Saved {len(transformed)} members to {csv_path.name}")

            timer.record(
                status="success",
                row_count=len(transformed),
                raw_path=raw_path,
                csv_path=csv_path,
            )
            return transformed

        except Exception as e:
            logger.error(f"Members extraction failed: {e}", exc_info=True)
            timer.record(status="failed", error=str(e))
            return None


def extract_guests(
    client, output_dir, raw_dir, manifest, logger, timestamp,
    rsvp_event_ids=None, raw_contacts=None,
):
    """
    Extract and transform all guests, excluding any tied to RSVP-type events.

    The Guests API V2 returns guests for both TICKETING and RSVP events.
    Since RSVP events are intentionally not extracted (slow per-event loop),
    we filter their guests out of the silver CSV. The bronze raw JSON still
    contains the full unfiltered API response for completeness.

    When `raw_contacts` is provided, the transformed guest rows are enriched
    with contact info (first_name, last_name, email, phone) by joining on
    contactId - the bulk Guests API does not return guestDetails so this
    join is the only way to get attendee identity in the silver CSV.
    """
    logger.info("=" * 60)
    logger.info("Extracting Guests (excluding RSVP-event guests)")
    logger.info("=" * 60)

    rsvp_event_ids = set(rsvp_event_ids or [])

    with manifest.timer("guests") as timer:
        try:
            guests_api = GuestsAPI(client)
            guests = guests_api.get_all_guests()
            logger.info(f"Retrieved {len(guests)} total guests")

            # Bronze layer keeps the FULL response (lossless)
            raw_path = dump_raw("guests", guests, timestamp, raw_dir)

            # Silver layer excludes guests for RSVP events
            if rsvp_event_ids:
                ticketing_guests = [
                    g for g in guests if g.get('eventId') not in rsvp_event_ids
                ]
                excluded = len(guests) - len(ticketing_guests)
                logger.info(
                    f"Filtered out {excluded} guests tied to {len(rsvp_event_ids)} RSVP events; "
                    f"keeping {len(ticketing_guests)} ticketing-event guests for silver CSV"
                )
            else:
                ticketing_guests = guests

            if not ticketing_guests:
                logger.warning("No ticketing-event guests found")
                timer.record(status="skipped", row_count=0, raw_path=raw_path)
                return None

            transformed_guests = GuestsTransformer.transform_guests(ticketing_guests)

            if raw_contacts:
                transformed_guests = GuestsTransformer.enrich_with_contact_data(
                    transformed_guests, raw_contacts
                )

            csv_path = output_dir / f"guests_{timestamp}.csv"
            BaseTransformer.save_to_csv(transformed_guests, str(csv_path))
            logger.info(f"Saved {len(transformed_guests)} guests to {csv_path.name}")

            timer.record(
                status="success",
                row_count=len(transformed_guests),
                raw_path=raw_path,
                csv_path=csv_path,
            )
            return transformed_guests

        except Exception as e:
            logger.error(f"Guests extraction failed: {e}", exc_info=True)
            timer.record(status="failed", error=str(e))
            return None


def extract_rsvps(client, output_dir, raw_dir, rsvp_events, manifest, logger, timestamp):
    """Extract RSVPs for all RSVP-type events."""
    logger.info("=" * 60)
    logger.info("Extracting RSVPs")
    logger.info("=" * 60)

    with manifest.timer("rsvps") as timer:
        try:
            if not rsvp_events:
                logger.warning("No RSVP events provided - skipping RSVP extraction")
                timer.record(status="skipped", row_count=0)
                return None

            rsvp_api = RSVPAPI(client)
            all_rsvps = []

            for event in rsvp_events:
                event_id = event.get('id')
                try:
                    rsvps = rsvp_api.get_all_rsvps_for_event(event_id)
                    logger.info(
                        f"Retrieved {len(rsvps)} RSVPs for event {event.get('title', event_id)}"
                    )
                    all_rsvps.extend(rsvps)
                except Exception as e:
                    logger.warning(f"Could not fetch RSVPs for event {event_id}: {e}")

            logger.info(
                f"Retrieved {len(all_rsvps)} total RSVPs across {len(rsvp_events)} events"
            )

            raw_path = dump_raw("rsvps", all_rsvps, timestamp, raw_dir)

            if not all_rsvps:
                logger.warning("No RSVPs found")
                timer.record(status="skipped", row_count=0, raw_path=raw_path)
                return None

            csv_path = output_dir / f"rsvps_{timestamp}.csv"
            RSVPsTransformer.save_to_csv(all_rsvps, str(csv_path))
            logger.info(f"Saved {len(all_rsvps)} RSVPs to {csv_path.name}")

            timer.record(
                status="success",
                row_count=len(all_rsvps),
                raw_path=raw_path,
                csv_path=csv_path,
            )
            return all_rsvps

        except Exception as e:
            logger.error(f"RSVPs extraction failed: {e}", exc_info=True)
            timer.record(status="failed", error=str(e))
            return None


def extract_ticket_definitions(client, output_dir, raw_dir, manifest, logger, timestamp):
    """
    Extract ticket definitions (templates with pricing, fee_type, sale_status).

    Returns a (raw_definitions, transformed_definitions) tuple. Raw is needed
    for the tickets join (uses raw nested fields), transformed feeds the gold
    attendance_fact step.
    """
    logger.info("=" * 60)
    logger.info("Extracting Ticket Definitions")
    logger.info("=" * 60)

    with manifest.timer("ticket_definitions") as timer:
        try:
            defs_api = TicketDefinitionsAPI(client)
            definitions = defs_api.get_all_ticket_definitions(fieldsets=["SALES_DETAILS"])
            logger.info(f"Retrieved {len(definitions)} ticket definitions")

            raw_path = dump_raw("ticket_definitions", definitions, timestamp, raw_dir)

            if not definitions:
                logger.warning("No ticket definitions found")
                timer.record(status="skipped", row_count=0, raw_path=raw_path)
                return None, []

            transformed = TicketDefinitionsTransformer.transform_definitions(definitions)
            csv_path = output_dir / f"ticket_definitions_{timestamp}.csv"
            BaseTransformer.save_to_csv(transformed, str(csv_path))
            logger.info(f"Saved {len(transformed)} ticket definitions to {csv_path.name}")

            timer.record(
                status="success",
                row_count=len(transformed),
                raw_path=raw_path,
                csv_path=csv_path,
            )
            return definitions, transformed

        except Exception as e:
            logger.error(f"Ticket definitions extraction failed: {e}", exc_info=True)
            timer.record(status="failed", error=str(e))
            return None, []


def extract_tickets(
    client, output_dir, raw_dir, ticket_definitions, manifest, logger, timestamp
):
    """
    Extract sold tickets, joined with their ticket definitions.

    Returns the transformed ticket dicts (with definition columns merged) so
    the gold attendance_fact step can pick up price / check-in / definition_id
    per ticket.
    """
    logger.info("=" * 60)
    logger.info("Extracting Tickets")
    logger.info("=" * 60)

    with manifest.timer("tickets") as timer:
        try:
            tickets_api = TicketsAPI(client)
            tickets = tickets_api.get_all_tickets()
            logger.info(f"Retrieved {len(tickets)} tickets")

            raw_path = dump_raw("tickets", tickets, timestamp, raw_dir)

            if not tickets:
                logger.warning("No tickets found")
                timer.record(status="skipped", row_count=0, raw_path=raw_path)
                return None

            # Build definitions lookup for join columns (def_fee_type, def_sale_status, etc.)
            defs_by_id = {}
            if ticket_definitions:
                defs_by_id = {d.get('id'): d for d in ticket_definitions if d.get('id')}
                logger.info(f"Built definitions lookup with {len(defs_by_id)} entries")

            transformed = TicketsTransformer.transform_tickets(tickets, defs_by_id)
            csv_path = output_dir / f"tickets_{timestamp}.csv"
            BaseTransformer.save_to_csv(transformed, str(csv_path))
            logger.info(f"Saved {len(transformed)} tickets to {csv_path.name}")

            timer.record(
                status="success",
                row_count=len(transformed),
                raw_path=raw_path,
                csv_path=csv_path,
            )
            return transformed

        except Exception as e:
            logger.error(f"Tickets extraction failed: {e}", exc_info=True)
            timer.record(status="failed", error=str(e))
            return None


def extract_order_summaries(
    client, output_dir, raw_dir, events, manifest, logger, timestamp
):
    """Extract per-event sales summaries (parallel)."""
    logger.info("=" * 60)
    logger.info("Extracting Order Summaries (Sales Data)")
    logger.info("=" * 60)

    with manifest.timer("order_summaries") as timer:
        try:
            if not events:
                logger.warning("No events provided - cannot extract order summaries")
                timer.record(status="skipped", row_count=0)
                return None

            orders_api = OrdersAPI(client)

            def fetch_summary(event):
                try:
                    return orders_api.get_summary_by_event(event.get('id'))
                except Exception:
                    return {'sales': []}

            logger.info(f"Fetching sales summaries for {len(events)} events (parallel)...")
            summary_responses = [None] * len(events)

            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_idx = {
                    executor.submit(fetch_summary, event): i
                    for i, event in enumerate(events)
                }

                completed = 0
                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    summary_responses[idx] = future.result()
                    completed += 1
                    if completed % 25 == 0:
                        logger.info(f"  Progress: {completed}/{len(events)} summaries fetched")

            events_with_sales = sum(1 for s in summary_responses if s.get('sales', []))
            logger.info(f"Retrieved summaries for {len(events)} events")
            logger.info(f"{events_with_sales} events have sales data")

            # Bronze: dump raw summary responses paired with event id
            raw_payload = [
                {"event_id": e.get('id'), "summary": s}
                for e, s in zip(events, summary_responses)
            ]
            raw_path = dump_raw("order_summaries", raw_payload, timestamp, raw_dir)

            transformed = OrderSummariesTransformer.transform_summaries(events, summary_responses)
            csv_path = output_dir / f"order_summaries_{timestamp}.csv"
            BaseTransformer.save_to_csv(transformed, str(csv_path))
            logger.info(f"Saved order summaries to {csv_path.name}")

            timer.record(
                status="success",
                row_count=len(transformed),
                raw_path=raw_path,
                csv_path=csv_path,
            )
            return transformed

        except Exception as e:
            logger.error(f"Order summaries extraction failed: {e}", exc_info=True)
            timer.record(status="failed", error=str(e))
            return None


def extract_event_orders(client, output_dir, raw_dir, manifest, logger, timestamp):
    """Extract individual ticket purchases (event orders)."""
    logger.info("=" * 60)
    logger.info("Extracting Event Orders")
    logger.info("=" * 60)

    with manifest.timer("event_orders") as timer:
        try:
            orders_api = OrdersAPI(client)
            logger.info("Fetching all event orders with pagination...")
            orders = orders_api.get_all_orders()
            logger.info(f"Retrieved {len(orders)} event orders")

            raw_path = dump_raw("event_orders", orders, timestamp, raw_dir)

            if not orders:
                logger.warning("No event orders found")
                timer.record(status="skipped", row_count=0, raw_path=raw_path)
                return None

            transformed = EventOrdersTransformer.transform_orders(orders)
            csv_path = output_dir / f"event_orders_{timestamp}.csv"
            BaseTransformer.save_to_csv(transformed, str(csv_path))
            logger.info(f"Saved {len(transformed)} event orders to {csv_path.name}")

            timer.record(
                status="success",
                row_count=len(transformed),
                raw_path=raw_path,
                csv_path=csv_path,
            )
            return transformed

        except Exception as e:
            logger.error(f"Event orders extraction failed: {e}", exc_info=True)
            timer.record(status="failed", error=str(e))
            return None


def extract_form_submissions(client, output_dir, raw_dir, manifest, logger, timestamp):
    """Extract form submissions, save BOTH wide and long-format CSVs."""
    logger.info("=" * 60)
    logger.info("Extracting Form Submissions")
    logger.info("=" * 60)

    with manifest.timer("form_submissions") as timer:
        try:
            forms_api = FormsAPI(client)
            submissions = forms_api.get_all_submissions_for_namespaces()
            logger.info(f"Retrieved {len(submissions)} total form submissions")

            raw_path = dump_raw("form_submissions", submissions, timestamp, raw_dir)

            if not submissions:
                logger.warning("No form submissions found")
                timer.record(status="skipped", row_count=0, raw_path=raw_path)
                return None

            # Wide format (one row per submission, dynamic field_* columns)
            wide_path = output_dir / f"form_submissions_{timestamp}.csv"
            FormSubmissionsTransformer.save_to_csv(submissions, str(wide_path))

            # Long format (one row per submission field, stable schema)
            long_path = output_dir / f"form_submissions_long_{timestamp}.csv"
            FormSubmissionsTransformer.save_to_csv_long(submissions, str(long_path))
            logger.info(
                f"Saved {len(submissions)} form submissions to {wide_path.name} (wide) "
                f"and {long_path.name} (long)"
            )

            timer.record(
                status="success",
                row_count=len(submissions),
                raw_path=raw_path,
                csv_path=wide_path,
                extra_paths={"long_csv": long_path},
            )
            return submissions

        except Exception as e:
            logger.error(f"Form submissions extraction failed: {e}", exc_info=True)
            timer.record(status="failed", error=str(e))
            return None


def extract_coupons(client, output_dir, raw_dir, manifest, logger, timestamp):
    """Extract all coupons (active + expired)."""
    logger.info("=" * 60)
    logger.info("Extracting Coupons")
    logger.info("=" * 60)

    with manifest.timer("coupons") as timer:
        try:
            coupons_api = CouponsAPI(client)
            coupons = coupons_api.get_all_coupons(include_expired=True)
            logger.info(f"Retrieved {len(coupons)} coupons")

            raw_path = dump_raw("coupons", coupons, timestamp, raw_dir)

            if not coupons:
                logger.warning("No coupons found")
                timer.record(status="skipped", row_count=0, raw_path=raw_path)
                return None

            csv_path = output_dir / f"coupons_{timestamp}.csv"
            CouponsTransformer.save_to_csv(coupons, str(csv_path))
            logger.info(f"Saved {len(coupons)} coupons to {csv_path.name}")

            timer.record(
                status="success",
                row_count=len(coupons),
                raw_path=raw_path,
                csv_path=csv_path,
            )
            return coupons

        except Exception as e:
            logger.error(f"Coupons extraction failed: {e}", exc_info=True)
            timer.record(status="failed", error=str(e))
            return None


def extract_automations(client, output_dir, raw_dir, manifest, logger, timestamp):
    """Extract all automation configurations."""
    logger.info("=" * 60)
    logger.info("Extracting Automations")
    logger.info("=" * 60)

    with manifest.timer("automations") as timer:
        try:
            automations_api = AutomationsAPI(client)
            automations = automations_api.get_all_automations()
            logger.info(f"Retrieved {len(automations)} automations")

            raw_path = dump_raw("automations", automations, timestamp, raw_dir)

            if not automations:
                logger.warning("No automations found")
                timer.record(status="skipped", row_count=0, raw_path=raw_path)
                return None

            csv_path = output_dir / f"automations_{timestamp}.csv"
            AutomationsTransformer.save_to_csv(automations, str(csv_path))
            logger.info(f"Saved {len(automations)} automations to {csv_path.name}")

            timer.record(
                status="success",
                row_count=len(automations),
                raw_path=raw_path,
                csv_path=csv_path,
            )
            return automations

        except Exception as e:
            logger.error(f"Automations extraction failed: {e}", exc_info=True)
            timer.record(status="failed", error=str(e))
            return None


def extract_payments(client, output_dir, raw_dir, manifest, logger, timestamp):
    """
    Extract every cashier transaction (the same data that powers the
    `Wix Dashboard > Sales > Payments` CSV export).

    Bronze: full JSON list dumped under data/raw/payments/year=Y/month=M/day=D/.
    Silver: one CSV row per transaction (sale, refund, declined, chargeback)
    with the Stripe / PayPal `provider_transaction_id`, billing contact info,
    refund roll-ups, and the `wix_app_order_id` join key back to event orders.
    """
    logger.info("=" * 60)
    logger.info("Extracting Payments (Cashier)")
    logger.info("=" * 60)

    with manifest.timer("payments") as timer:
        try:
            payments_api = PaymentsAPI(client)
            payments = payments_api.get_all_transactions(include_refunds=True)
            logger.info(f"Retrieved {len(payments)} cashier transactions")

            raw_path = dump_raw("payments", payments, timestamp, raw_dir)

            if not payments:
                logger.warning("No payments returned from cashier API")
                timer.record(status="skipped", row_count=0, raw_path=raw_path)
                return None

            transformed = PaymentsTransformer.transform_transactions(payments)
            csv_path = output_dir / f"payments_{timestamp}.csv"
            BaseTransformer.save_to_csv(transformed, str(csv_path))
            logger.info(f"Saved {len(transformed)} payments to {csv_path.name}")

            timer.record(
                status="success",
                row_count=len(transformed),
                raw_path=raw_path,
                csv_path=csv_path,
            )
            return transformed

        except Exception as e:
            logger.error(f"Payments extraction failed: {e}", exc_info=True)
            timer.record(status="failed", error=str(e))
            return None


def build_attendance_fact(
    output_dir,
    manifest,
    logger,
    timestamp,
    transformed_guests,
    transformed_events=None,
    transformed_contacts=None,
    transformed_members=None,
    transformed_ticket_definitions=None,
    transformed_tickets=None,
    transformed_order_summaries=None,
    transformed_payments=None,
):
    """
    Build the gold attendance_fact CSV: one row per attendee with all event,
    pricing, contact, and membership dimensions denormalized.

    Reuses the in-memory transformed silver dicts produced by the upstream
    extract steps - no extra API calls needed.
    """
    logger.info("=" * 60)
    logger.info("Building Attendance Fact (Gold Layer)")
    logger.info("=" * 60)

    with manifest.timer("attendance_fact") as timer:
        try:
            if not transformed_guests:
                logger.warning("No guests available - cannot build attendance_fact")
                timer.record(status="skipped", row_count=0)
                return None

            rows = AttendanceFactTransformer.build(
                transformed_guests=transformed_guests,
                transformed_events=transformed_events,
                transformed_contacts=transformed_contacts,
                transformed_members=transformed_members,
                transformed_ticket_definitions=transformed_ticket_definitions,
                transformed_tickets=transformed_tickets,
                transformed_order_summaries=transformed_order_summaries,
                transformed_payments=transformed_payments,
            )

            if not rows:
                logger.warning("Attendance fact built 0 rows")
                timer.record(status="skipped", row_count=0)
                return None

            csv_path = output_dir / f"attendance_fact_{timestamp}.csv"
            BaseTransformer.save_to_csv(rows, str(csv_path))
            logger.info(f"Saved {len(rows)} attendee rows to {csv_path.name}")

            timer.record(
                status="success",
                row_count=len(rows),
                csv_path=csv_path,
            )
            return rows

        except Exception as e:
            logger.error(f"Attendance fact build failed: {e}", exc_info=True)
            timer.record(status="failed", error=str(e))
            return None


def build_payments_fact(
    output_dir,
    manifest,
    logger,
    timestamp,
    transformed_payments,
    transformed_event_orders=None,
    transformed_events=None,
    transformed_contacts=None,
    transformed_members=None,
    transformed_order_summaries=None,
):
    """
    Build the gold payments_fact CSV: one row per cashier transaction, joined
    with event_orders -> events / contacts / members / order_summaries so each
    payment carries event_title, category_names, member status, etc.

    Reuses the in-memory transformed silver dicts produced upstream - no extra
    API calls needed.
    """
    logger.info("=" * 60)
    logger.info("Building Payments Fact (Gold Layer)")
    logger.info("=" * 60)

    with manifest.timer("payments_fact") as timer:
        try:
            if not transformed_payments:
                logger.warning("No payments available - cannot build payments_fact")
                timer.record(status="skipped", row_count=0)
                return None

            rows = PaymentsFactTransformer.build(
                transformed_payments=transformed_payments,
                transformed_event_orders=transformed_event_orders,
                transformed_events=transformed_events,
                transformed_contacts=transformed_contacts,
                transformed_members=transformed_members,
                transformed_order_summaries=transformed_order_summaries,
            )

            if not rows:
                logger.warning("Payments fact built 0 rows")
                timer.record(status="skipped", row_count=0)
                return None

            csv_path = output_dir / f"payments_fact_{timestamp}.csv"
            BaseTransformer.save_to_csv(rows, str(csv_path))
            logger.info(f"Saved {len(rows)} payment rows to {csv_path.name}")

            timer.record(
                status="success",
                row_count=len(rows),
                csv_path=csv_path,
            )
            return rows

        except Exception as e:
            logger.error(f"Payments fact build failed: {e}", exc_info=True)
            timer.record(status="failed", error=str(e))
            return None


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Extract all data from Wix APIs")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for processed CSV files (default: data/processed)",
    )
    parser.add_argument(
        "--raw-dir",
        type=str,
        default=None,
        help="Output directory for raw JSON dumps / bronze layer (default: data/raw)",
    )
    return parser.parse_args()


def main():
    """Main entry point for full data extraction."""
    args = parse_args()

    logger = setup_logging(log_dir="logs", log_level="INFO")
    logger.info("=" * 60)
    logger.info("STARTING FULL DATA EXTRACTION FROM WIX APIs")
    logger.info("=" * 60)

    # Single timestamp = atomic snapshot identifier across all files
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        # Resolve output directories
        output_dir = Path(args.output_dir) if args.output_dir else project_root / "data" / "processed"
        raw_dir = Path(args.raw_dir) if args.raw_dir else project_root / "data" / "raw"

        output_dir.mkdir(parents=True, exist_ok=True)
        raw_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Processed (silver) dir: {output_dir}")
        logger.info(f"Raw (bronze) dir: {raw_dir}")
        logger.info(f"Run timestamp: {run_timestamp}")

        # Initialize manifest for observability
        manifest = RunManifest(run_timestamp, output_dir)

        # Initialize API client with context manager for guaranteed cleanup
        logger.info("Initializing Wix API client...")
        with WixAPIClient.from_env() as client:
            logger.info("Client initialized successfully")

            # Events (returns ticketing + RSVP for downstream use)
            ticketing_events, rsvp_events, transformed_events = extract_events(
                client, output_dir, raw_dir, manifest, logger, run_timestamp
            )

            # Build set of RSVP event IDs - used to filter RSVP guests out of guests CSV
            rsvp_event_ids = {e.get('id') for e in (rsvp_events or []) if e.get('id')}

            # Contacts (raw kept for guests enrichment; transformed feeds gold)
            raw_contacts, transformed_contacts = extract_contacts(
                client, output_dir, raw_dir, manifest, logger, run_timestamp
            )

            # Site Members
            transformed_members = extract_members(
                client, output_dir, raw_dir, manifest, logger, run_timestamp
            )

            # Guests (filtered to exclude RSVP-event guests; enriched via contacts)
            transformed_guests = extract_guests(
                client, output_dir, raw_dir, manifest, logger, run_timestamp,
                rsvp_event_ids=rsvp_event_ids,
                raw_contacts=raw_contacts,
            )

            # NOTE: extract_rsvps() is intentionally NOT called.
            # RSVP extraction loops per-event and is too slow for the use case.
            # The RSVP events themselves are still captured in rsvp_events_<ts>.csv
            # via extract_events() above. Re-enable here if RSVP attendance data
            # is needed in the future.

            # Ticket Definitions (fetched FIRST so tickets can join with them)
            ticket_definitions, transformed_ticket_definitions = extract_ticket_definitions(
                client, output_dir, raw_dir, manifest, logger, run_timestamp
            )

            # Tickets (joined with definitions)
            transformed_tickets = extract_tickets(
                client, output_dir, raw_dir, ticket_definitions, manifest, logger, run_timestamp
            )

            # Order Summaries (uses ticketing events)
            transformed_order_summaries = extract_order_summaries(
                client, output_dir, raw_dir, ticketing_events, manifest, logger, run_timestamp
            )

            # Event Orders (individual purchases) - returned for the gold view
            transformed_event_orders = extract_event_orders(
                client, output_dir, raw_dir, manifest, logger, run_timestamp
            )

            # Payments (cashier transactions - powers the dashboard Payments CSV)
            transformed_payments = extract_payments(
                client, output_dir, raw_dir, manifest, logger, run_timestamp
            )

            # Gold layer: attendance_fact (one row per attendee, all dims joined)
            build_attendance_fact(
                output_dir, manifest, logger, run_timestamp,
                transformed_guests=transformed_guests,
                transformed_events=transformed_events,
                transformed_contacts=transformed_contacts,
                transformed_members=transformed_members,
                transformed_ticket_definitions=transformed_ticket_definitions,
                transformed_tickets=transformed_tickets,
                transformed_order_summaries=transformed_order_summaries,
                transformed_payments=transformed_payments,
            )

            # Gold layer: payments_fact (one row per payment, event + member dims joined)
            build_payments_fact(
                output_dir, manifest, logger, run_timestamp,
                transformed_payments=transformed_payments,
                transformed_event_orders=transformed_event_orders,
                transformed_events=transformed_events,
                transformed_contacts=transformed_contacts,
                transformed_members=transformed_members,
                transformed_order_summaries=transformed_order_summaries,
            )

            # Form Submissions (both wide + long)
            extract_form_submissions(
                client, output_dir, raw_dir, manifest, logger, run_timestamp
            )

            # Coupons (active + expired)
            extract_coupons(client, output_dir, raw_dir, manifest, logger, run_timestamp)

            # Automations
            extract_automations(client, output_dir, raw_dir, manifest, logger, run_timestamp)

        # Save manifest
        manifest_path = manifest.save()

        # Print summary
        logger.info("=" * 60)
        logger.info("EXTRACTION SUMMARY")
        logger.info("=" * 60)

        successful = [name for name, e in manifest.entities.items() if e.status == "success"]
        failed = [name for name, e in manifest.entities.items() if e.status == "failed"]
        skipped = [name for name, e in manifest.entities.items() if e.status == "skipped"]

        logger.info(f"Successful: {len(successful)}/{len(manifest.entities)}")
        for name in successful:
            row_count = manifest.entities[name].row_count
            logger.info(f"  ✓ {name} ({row_count} records)")

        if skipped:
            logger.info(f"Skipped: {len(skipped)}")
            for name in skipped:
                logger.info(f"  - {name}")

        if failed:
            logger.warning(f"Failed: {len(failed)}")
            for name in failed:
                err = manifest.entities[name].error or "unknown"
                logger.warning(f"  ✗ {name}: {err}")

        logger.info("=" * 60)
        logger.info(f"Silver CSVs:  {output_dir}")
        logger.info(f"Bronze JSONs: {raw_dir}")
        logger.info(f"Manifest:     {manifest_path}")
        logger.info("=" * 60)

        if not failed:
            logger.info("Full data extraction completed successfully!")
            return 0
        else:
            logger.warning(f"Completed with {len(failed)} failures - see manifest for details")
            return 0  # Still return 0 since at least some data was extracted

    except Exception as e:
        logger.error(f"Data extraction failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
