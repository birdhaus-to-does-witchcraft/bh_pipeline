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

    # Set up output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = project_root / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("PULLING UPCOMING EVENTS")
    print("=" * 60)

    # Initialize API client
    print("\nInitializing Wix API client...")
    client = WixAPIClient.from_env()
    events_api = EventsAPI(client)
    print("✓ Client initialized")

    # Query upcoming events only (using API filter)
    print("\nFetching upcoming events...")
    events = events_api.get_all_events(
        filter_dict={"status": ["UPCOMING"]}
    )
    print(f"✓ Retrieved {len(events)} upcoming events")

    # Filter to TICKETING events only (client-side)
    ticketing_events = [
        e for e in events
        if e.get('registration', {}).get('type') == 'TICKETING'
    ]
    rsvp_count = len(events) - len(ticketing_events)
    print(f"✓ Filtered to {len(ticketing_events)} TICKETING events (excluded {rsvp_count} RSVP/other)")

    if not ticketing_events:
        print("\n⚠ No upcoming TICKETING events found")
        client.close()
        return 0

    # Save to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"upcoming_events_{timestamp}.csv"

    EventsTransformer.save_to_csv(ticketing_events, str(output_path))
    print(f"\n✓ Saved to: {output_path}")

    # Clean up
    client.close()

    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)
    print(f"  Events: {len(ticketing_events)}")
    print(f"  Output: {output_path.name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

