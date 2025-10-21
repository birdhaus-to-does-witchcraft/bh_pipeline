"""
Check if there are any guests in the system and their structure.
"""

import sys
import json
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from wix_api.client import WixAPIClient

def main():
    """Check for guests data."""
    print("=" * 80)
    print("Checking Wix Guests Data")
    print("=" * 80)

    # Initialize API client
    print("\n1. Initializing Wix API client...")
    client = WixAPIClient.from_env()

    # Query all guests (no filter)
    print("\n2. Querying all guests...")
    print("-" * 80)
    try:
        payload = {
            "query": {
                "fieldsets": ["GUEST_DETAILS"],
                "paging": {"limit": 100, "offset": 0}
            }
        }
        response = client.post('/events/v2/guests/query', json=payload)

        paging_metadata = response.get('pagingMetadata', {})
        guests = response.get('guests', [])

        print(f"   Total guests in system: {paging_metadata.get('total', 'unknown')}")
        print(f"   Retrieved: {len(guests)} guests")

        if guests:
            print(f"\n3. Sample guest structure:")
            print("-" * 80)
            print(json.dumps(guests[0], indent=2)[:2000])  # First 2000 chars

            # Save sample to file for reference
            sample_file = project_root / "data" / "raw" / "guests" / "sample_guest.json"
            sample_file.parent.mkdir(parents=True, exist_ok=True)
            with open(sample_file, 'w') as f:
                json.dump(guests[0], f, indent=2)
            print(f"\n   ✓ Saved sample to: {sample_file}")
        else:
            print("\n   No guests found in the system.")
            print("   This is expected if there are no event registrations yet.")

            # Check events to see if any have tickets
            print("\n3. Checking events for ticket sales...")
            print("-" * 80)
            events_response = client.post('/events/v3/events/query',
                                         json={"query": {"paging": {"limit": 20}}})
            events = events_response.get('events', [])

            events_with_tickets = []
            for event in events:
                registration = event.get('registration', {})
                tickets = registration.get('tickets', {})
                if tickets:
                    events_with_tickets.append({
                        'id': event.get('id'),
                        'title': event.get('title'),
                        'status': event.get('status'),
                        'sold_out': tickets.get('soldOut', False),
                        'currency': tickets.get('currency'),
                        'price_range': f"{tickets.get('lowestPrice', {}).get('formattedValue', 'N/A')} - {tickets.get('highestPrice', {}).get('formattedValue', 'N/A')}"
                    })

            print(f"   Found {len(events_with_tickets)} events with ticketing enabled")
            if events_with_tickets:
                for evt in events_with_tickets[:5]:  # Show first 5
                    print(f"      - {evt['title']} ({evt['status']})")
                    print(f"        Price range: {evt['price_range']}, Sold out: {evt['sold_out']}")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("Check complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
