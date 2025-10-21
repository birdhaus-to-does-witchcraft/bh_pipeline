"""
Export all Wix events and their guests to CSV files.

This script:
1. Fetches all events from Wix Events API
2. For each event, fetches all associated guests
3. Exports events to events.csv
4. Exports all guests (from all events) to guests.csv

Usage:
    python scripts/export_events_and_guests.py
"""

import sys
import csv
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Enable detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
    """
    Flatten a nested dictionary.

    Example:
        {"a": {"b": 1, "c": 2}} -> {"a_b": 1, "a_c": 2}
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            # Convert lists to strings
            items.append((new_key, str(v)))
        else:
            items.append((new_key, v))
    return dict(items)


def export_events_to_csv(events: List[Dict[str, Any]], output_file: str):
    """
    Export events to CSV file.

    Args:
        events: List of event dictionaries
        output_file: Path to output CSV file
    """
    if not events:
        logger.warning("No events to export")
        return

    logger.info(f"Exporting {len(events)} events to {output_file}")

    # Flatten all events
    flattened_events = [flatten_dict(event) for event in events]

    # Get all unique keys across all events
    all_keys = set()
    for event in flattened_events:
        all_keys.update(event.keys())

    # Sort keys for consistent column ordering
    fieldnames = sorted(all_keys)

    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flattened_events)

    logger.info(f"Successfully exported events to {output_file}")


def export_guests_to_csv(guests: List[Dict[str, Any]], output_file: str):
    """
    Export guests to CSV file.

    Args:
        guests: List of guest dictionaries
        output_file: Path to output CSV file
    """
    if not guests:
        logger.warning("No guests to export")
        return

    logger.info(f"Exporting {len(guests)} guests to {output_file}")

    # Flatten all guests
    flattened_guests = [flatten_dict(guest) for guest in guests]

    # Get all unique keys across all guests
    all_keys = set()
    for guest in flattened_guests:
        all_keys.update(guest.keys())

    # Sort keys for consistent column ordering
    fieldnames = sorted(all_keys)

    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flattened_guests)

    logger.info(f"Successfully exported guests to {output_file}")


def main():
    """Main execution function."""
    print("\n" + "=" * 60)
    print("Wix Events and Guests Export")
    print("=" * 60)

    try:
        # Import required modules
        from wix_api.client import WixAPIClient
        from wix_api.events import EventsAPI
        from wix_api.guests import GuestsAPI

        # Initialize client
        print("\n[1/5] Initializing Wix API client...")
        client = WixAPIClient.from_env()
        events_api = EventsAPI(client)
        guests_api = GuestsAPI(client)
        print("    Client initialized successfully")

        # Fetch all events
        print("\n[2/5] Fetching all events from Wix...")
        events = events_api.get_all_events()
        print(f"    Retrieved {len(events)} events")

        if not events:
            print("\n    No events found. Exiting.")
            client.close()
            return 0

        # Fetch guests for each event
        print("\n[3/5] Fetching guests for all events...")
        all_guests = []

        for i, event in enumerate(events, 1):
            event_id = event.get('id')
            event_title = event.get('title', 'Unknown')

            print(f"    [{i}/{len(events)}] Fetching guests for: {event_title} (ID: {event_id})")

            try:
                guests = guests_api.get_all_guests_for_event(
                    event_id=event_id,
                    include_details=True
                )

                # Add event_id to each guest record for reference
                for guest in guests:
                    guest['event_id'] = event_id
                    guest['event_title'] = event_title

                all_guests.extend(guests)
                print(f"        Found {len(guests)} guests")

            except Exception as e:
                logger.error(f"Failed to fetch guests for event {event_id}: {e}")
                print(f"        ERROR: Could not fetch guests - {e}")

        print(f"\n    Total guests retrieved: {len(all_guests)}")

        # Create output directory
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        # Generate timestamped filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        events_file = output_dir / f"events_{timestamp}.csv"
        guests_file = output_dir / f"guests_{timestamp}.csv"

        # Export events to CSV
        print(f"\n[4/5] Exporting events to CSV...")
        export_events_to_csv(events, str(events_file))
        print(f"    Events saved to: {events_file}")

        # Export guests to CSV
        print(f"\n[5/5] Exporting guests to CSV...")
        export_guests_to_csv(all_guests, str(guests_file))
        print(f"    Guests saved to: {guests_file}")

        # Clean up
        client.close()

        # Summary
        print("\n" + "=" * 60)
        print("Export Summary")
        print("=" * 60)
        print(f"Total events exported: {len(events)}")
        print(f"Total guests exported: {len(all_guests)}")
        print(f"\nOutput files:")
        print(f"  - Events: {events_file}")
        print(f"  - Guests: {guests_file}")
        print("=" * 60)
        print("\nExport completed successfully!")

        return 0

    except Exception as e:
        print(f"\n✗ Export failed: {e}")
        logger.error(f"Export failed", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
