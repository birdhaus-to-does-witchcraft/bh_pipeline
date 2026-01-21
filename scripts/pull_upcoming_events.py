"""
Pull upcoming events only - simple, single-purpose script.

Fetches only upcoming TICKETING events from Wix and saves to CSV.

Usage:
    python scripts/pull_upcoming_events.py
    python scripts/pull_upcoming_events.py --output-dir /path/to/output
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from utils.logger import setup_logging
from wix_api.client import WixAPIClient
from wix_api.events import EventsAPI
from transformers.events import EventsTransformer


def main():
    """Pull upcoming TICKETING events and save to CSV."""
    parser = argparse.ArgumentParser(description="Pull upcoming events from Wix")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for CSV (default: data/processed)"
    )
    args = parser.parse_args()

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

            # Save to CSV
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"upcoming_events_{timestamp}.csv"

            EventsTransformer.save_to_csv(ticketing_events, str(output_path))
            logger.info(f"Saved to: {output_path}")

        # Summary (client is now closed)
        logger.info("=" * 60)
        logger.info("COMPLETE")
        logger.info("=" * 60)
        logger.info(f"  Events: {len(ticketing_events)}")
        logger.info(f"  Output: {output_path.name}")

        return 0

    except Exception as e:
        logger.error(f"Failed to pull upcoming events: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

