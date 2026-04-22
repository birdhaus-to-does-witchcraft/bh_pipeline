"""
Full data extraction script - pulls all data from Wix APIs.

This script extracts complete datasets for all entity types:
- Events
- Event Guests
- Contacts
- Order Summaries (Sales Data)
- Event Orders

All data is transformed and saved to timestamped CSV files with UTF-8 BOM encoding
for Excel compatibility.

Usage:
    python scripts/pull_all.py
    # Or with custom output directory:
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
from wix_api.client import WixAPIClient
from wix_api.events import EventsAPI
from wix_api.contacts import ContactsAPI
from wix_api.guests import GuestsAPI
from wix_api.orders import OrdersAPI
from transformers.events import EventsTransformer
from transformers.contacts import ContactsTransformer
from transformers.guests import GuestsTransformer
from transformers.order_summaries import OrderSummariesTransformer
from transformers.event_orders import EventOrdersTransformer
from transformers.base import BaseTransformer


def extract_events(client, output_dir, logger, timestamp):
    """Extract and transform all events."""
    logger.info("=" * 60)
    logger.info("Extracting Events")
    logger.info("=" * 60)

    try:
        events_api = EventsAPI(client)
        all_events = events_api.get_all_events()
        logger.info(f"Retrieved {len(all_events)} total events")

        # Filter out RSVP events - keep only TICKETING events
        events = [
            e for e in all_events
            if e.get('registration', {}).get('type') == 'TICKETING'
        ]
        rsvp_count = len(all_events) - len(events)
        logger.info(f"Filtered to {len(events)} TICKETING events (excluded {rsvp_count} RSVP events)")

        if not events:
            logger.warning("No events found")
            return None

        # Transform and save
        output_path = output_dir / f"events_{timestamp}.csv"

        EventsTransformer.save_to_csv(events, str(output_path))
        logger.info(f"Saved {len(events)} events to {output_path.name}")

        return events

    except Exception as e:
        logger.error(f"Events extraction failed: {e}", exc_info=True)
        return None


def extract_contacts(client, output_dir, logger, timestamp):
    """Extract and transform all contacts."""
    logger.info("=" * 60)
    logger.info("Extracting Contacts")
    logger.info("=" * 60)

    try:
        contacts_api = ContactsAPI(client)
        contacts = contacts_api.get_all_contacts()
        logger.info(f"Retrieved {len(contacts)} contacts")

        if not contacts:
            logger.warning("No contacts found")
            return None

        # Transform and save
        output_path = output_dir / f"contacts_{timestamp}.csv"

        ContactsTransformer.save_to_csv(contacts, str(output_path))
        logger.info(f"Saved {len(contacts)} contacts to {output_path.name}")

        return contacts

    except Exception as e:
        logger.error(f"Contacts extraction failed: {e}", exc_info=True)
        return None


def extract_guests(client, output_dir, logger, timestamp):
    """Extract and transform all guests."""
    logger.info("=" * 60)
    logger.info("Extracting Guests")
    logger.info("=" * 60)

    try:
        guests_api = GuestsAPI(client)
        guests = guests_api.get_all_guests()
        logger.info(f"Retrieved {len(guests)} guests")

        if not guests:
            logger.warning("No guests found - this is normal if no event registrations exist")
            return None

        # Transform guests
        transformed_guests = GuestsTransformer.transform_guests(guests)

        # Save guests
        output_path = output_dir / f"guests_{timestamp}.csv"
        BaseTransformer.save_to_csv(transformed_guests, str(output_path))
        logger.info(f"Saved {len(transformed_guests)} guests to {output_path.name}")

        return transformed_guests

    except Exception as e:
        logger.error(f"Guests extraction failed: {e}", exc_info=True)
        return None


def extract_order_summaries(client, output_dir, events, logger, timestamp):
    """Extract and transform order summaries (sales data per event)."""
    logger.info("=" * 60)
    logger.info("Extracting Order Summaries (Sales Data)")
    logger.info("=" * 60)

    try:
        if not events:
            logger.warning("No events provided - cannot extract order summaries")
            return None

        orders_api = OrdersAPI(client)

        # Helper function for parallel fetching
        def fetch_summary(event):
            try:
                return orders_api.get_summary_by_event(event.get('id'))
            except Exception:
                return {'sales': []}

        # Fetch summaries in parallel using ThreadPoolExecutor
        # Using 10 workers to stay well under Wix's 100 calls/minute rate limit
        logger.info(f"Fetching sales summaries for {len(events)} events (parallel)...")
        summary_responses = [None] * len(events)

        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all tasks and map futures to their index
            future_to_idx = {
                executor.submit(fetch_summary, event): i
                for i, event in enumerate(events)
            }

            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                summary_responses[idx] = future.result()
                completed += 1
                if completed % 25 == 0:
                    logger.info(f"  Progress: {completed}/{len(events)} summaries fetched")

        # Count events with sales
        events_with_sales = sum(1 for s in summary_responses if s.get('sales', []))

        logger.info(f"Retrieved summaries for {len(events)} events")
        logger.info(f"{events_with_sales} events have sales data")

        # Transform and save
        output_path = output_dir / f"order_summaries_{timestamp}.csv"

        OrderSummariesTransformer.save_to_csv(events, summary_responses, str(output_path))
        logger.info(f"Saved order summaries to {output_path.name}")

        return summary_responses

    except Exception as e:
        logger.error(f"Order summaries extraction failed: {e}", exc_info=True)
        return None


def extract_event_orders(client, output_dir, logger, timestamp):
    """Extract and transform event orders (individual ticket purchases)."""
    logger.info("=" * 60)
    logger.info("Extracting Event Orders")
    logger.info("=" * 60)

    try:
        # Use OrdersAPI to fetch all event orders
        orders_api = OrdersAPI(client)
        logger.info("Fetching all event orders with pagination...")
        orders = orders_api.get_all_orders()
        logger.info(f"Retrieved {len(orders)} event orders")

        if not orders:
            logger.warning("No event orders found")
            return None

        # Transform and save using EventOrdersTransformer
        output_path = output_dir / f"event_orders_{timestamp}.csv"

        EventOrdersTransformer.save_to_csv(orders, str(output_path))
        logger.info(f"Saved {len(orders)} event orders to {output_path.name}")

        return orders

    except Exception as e:
        logger.error(f"Event orders extraction failed: {e}", exc_info=True)
        return None


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Extract all data from Wix APIs"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for CSV files (default: data/processed)"
    )
    return parser.parse_args()


def main():
    """Main entry point for full data extraction."""
    args = parse_args()

    # Set up logging
    logger = setup_logging(log_dir="logs", log_level="INFO")
    logger.info("=" * 60)
    logger.info("STARTING FULL DATA EXTRACTION FROM WIX APIs")
    logger.info("=" * 60)

    # Create single timestamp for this run - ensures all files have matching timestamps
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        # Create output directory
        if args.output_dir:
            output_dir = Path(args.output_dir)
        else:
            output_dir = project_root / "data" / "processed"

        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"Run timestamp: {run_timestamp}")

        # Initialize API client with context manager for guaranteed cleanup
        logger.info("Initializing Wix API client...")
        with WixAPIClient.from_env() as client:
            logger.info("Client initialized successfully")

            # Extract all data types
            results = {}

            # Events (needed for order summaries)
            events = extract_events(client, output_dir, logger, run_timestamp)
            results['events'] = events is not None

            # Contacts (needed for guest enrichment)
            contacts = extract_contacts(client, output_dir, logger, run_timestamp)
            results['contacts'] = contacts is not None

            # Guests
            guests = extract_guests(client, output_dir, logger, run_timestamp)
            results['guests'] = guests is not None

            # Order Summaries (uses events)
            order_summaries = extract_order_summaries(client, output_dir, events, logger, run_timestamp)
            results['order_summaries'] = order_summaries is not None

            # Event Orders (individual ticket purchases)
            event_orders = extract_event_orders(client, output_dir, logger, run_timestamp)
            results['event_orders'] = event_orders is not None

        # Summary (client is now closed)
        logger.info("=" * 60)
        logger.info("EXTRACTION SUMMARY")
        logger.info("=" * 60)

        successful = [name for name, success in results.items() if success]
        failed = [name for name, success in results.items() if not success]

        logger.info(f"Successful: {len(successful)}/{len(results)}")
        for name in successful:
            logger.info(f"  ✓ {name.capitalize()}")

        if failed:
            logger.warning(f"Skipped/Failed: {len(failed)}")
            for name in failed:
                logger.warning(f"  ✗ {name.capitalize()}")

        logger.info("=" * 60)
        logger.info(f"All files saved to: {output_dir}")
        logger.info("=" * 60)

        if all(results.values()):
            logger.info("Full data extraction completed successfully!")
            return 0
        else:
            logger.warning("Some data types were skipped or failed")
            return 0  # Still return success if at least some data was extracted

    except Exception as e:
        logger.error(f"Data extraction failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
