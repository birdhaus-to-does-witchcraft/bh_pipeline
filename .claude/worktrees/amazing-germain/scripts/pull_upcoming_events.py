"""
Pull upcoming events only - with optional format for different audiences.

Fetches only upcoming TICKETING events from Wix and saves to CSV.
Supports different output formats tailored for educators or social media.

Usage:
    python scripts/pull_upcoming_events.py
    python scripts/pull_upcoming_events.py --format educators
    python scripts/pull_upcoming_events.py --format socials
    python scripts/pull_upcoming_events.py --output-dir /path/to/output
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
from wix_api.orders import OrdersAPI
from transformers.events import EventsTransformer
from transformers.base import BaseTransformer

# Column sets for each format
EDUCATOR_FIELDS = [
    'title', 'start_date', 'start_time',
    'primary_category', 'category_names',
]

SOCIALS_FIELDS = [
    'title', 'day_of_week', 'start_date', 'start_time',
    'short_description', 'lowest_price', 'highest_price',
    'location_name', 'event_page_url', 'main_image_url', 'sold_out',
]


def main():
    """Pull upcoming TICKETING events and save to CSV."""
    parser = argparse.ArgumentParser(description="Pull upcoming events from Wix")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for CSV (default: data/processed)"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["full", "educators", "socials"],
        default="full",
        help="Output format: full (all fields), educators (category + ticket sales), socials (social-media-friendly)"
    )
    args = parser.parse_args()
    output_format = args.format

    # Set up structured logging
    logger = setup_logging(log_dir="logs", log_level="INFO")
    logger.info("=" * 60)
    logger.info("PULLING UPCOMING EVENTS")
    logger.info("=" * 60)

    try:
        # Set up output directory
        if args.output_dir:
            output_dir = Path(args.output_dir)
        else:
            output_dir = project_root / "data" / "processed"
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory: {output_dir}")

        # Initialize API client with context manager for guaranteed cleanup
        logger.info("Initializing Wix API client...")
        with WixAPIClient.from_env() as client:
            logger.info("Client initialized successfully")

            events_api = EventsAPI(client)

            # Query upcoming events only (using API filter)
            logger.info("Fetching upcoming events...")
            events = events_api.get_all_events(
                filter_dict={"status": ["UPCOMING"]}
            )
            logger.info(f"Retrieved {len(events)} upcoming events")

            # Filter to TICKETING events only (client-side)
            ticketing_events = [
                e for e in events
                if e.get('registration', {}).get('type') == 'TICKETING'
            ]
            rsvp_count = len(events) - len(ticketing_events)
            logger.info(f"Filtered to {len(ticketing_events)} TICKETING events (excluded {rsvp_count} RSVP/other)")

            if not ticketing_events:
                logger.warning("No upcoming TICKETING events found")
                return 0

            # Build output filename with format suffix
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if output_format == "full":
                output_path = output_dir / f"upcoming_events_{timestamp}.csv"
            else:
                output_path = output_dir / f"upcoming_events_{output_format}_{timestamp}.csv"

            if output_format == "full":
                # Full format: all fields, existing behavior
                EventsTransformer.save_to_csv(ticketing_events, str(output_path))

            elif output_format == "educators":
                # Educators format: category + ticket sales data
                logger.info("Fetching order summaries for ticket counts...")
                orders_api = OrdersAPI(client)

                def fetch_summary(event):
                    try:
                        return orders_api.get_summary_by_event(event.get('id'))
                    except Exception:
                        return {'sales': []}

                summary_responses = [None] * len(ticketing_events)
                with ThreadPoolExecutor(max_workers=10) as executor:
                    future_to_idx = {
                        executor.submit(fetch_summary, event): i
                        for i, event in enumerate(ticketing_events)
                    }
                    for future in as_completed(future_to_idx):
                        idx = future_to_idx[future]
                        summary_responses[idx] = future.result()

                logger.info(f"Retrieved summaries for {len(ticketing_events)} events")

                transformed = EventsTransformer.transform_events(ticketing_events)
                educator_rows = []
                for i, event_data in enumerate(transformed):
                    row = {k: event_data.get(k) for k in EDUCATOR_FIELDS}
                    sales = summary_responses[i].get('sales', [])
                    if sales:
                        row['tickets_sold'] = sales[0].get('totalTickets', 0)
                        total = sales[0].get('total', {})
                        row['total_revenue'] = total.get('amount')
                    else:
                        row['tickets_sold'] = 0
                        row['total_revenue'] = None
                    educator_rows.append(row)

                BaseTransformer.save_to_csv(educator_rows, str(output_path))

            elif output_format == "socials":
                # Socials format: fields useful for social media posts
                transformed = EventsTransformer.transform_events(ticketing_events)
                socials_rows = [
                    {k: event_data.get(k) for k in SOCIALS_FIELDS}
                    for event_data in transformed
                ]
                socials_rows.sort(key=lambda x: x.get('start_date') or '')
                BaseTransformer.save_to_csv(socials_rows, str(output_path))

            logger.info(f"Saved to: {output_path}")

        # Summary (client is now closed)
        logger.info("=" * 60)
        logger.info("COMPLETE")
        logger.info("=" * 60)
        logger.info(f"  Format: {output_format}")
        logger.info(f"  Events: {len(ticketing_events)}")
        logger.info(f"  Output: {output_path.name}")

        return 0

    except Exception as e:
        logger.error(f"Failed to pull upcoming events: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

