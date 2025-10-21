"""
Test the Wix Guests API to find the correct query format.
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from wix_api.client import WixAPIClient

def main():
    """Test the guests API with different query formats."""
    print("=" * 80)
    print("Testing Wix Guests API Query Formats")
    print("=" * 80)

    # Initialize API client
    print("\n1. Initializing Wix API client...")
    client = WixAPIClient.from_env()

    # Test 1: Empty query (should fail but see error message)
    print("\n2. Test 1: Empty query object")
    print("-" * 80)
    try:
        response = client.post('/events/v2/guests/query', json={})
        print(f"   ✓ Success (unexpected!): {response}")
    except Exception as e:
        print(f"   ✗ Failed (expected): {e}")

    # Test 2: Query with just paging
    print("\n3. Test 2: Query with paging only")
    print("-" * 80)
    try:
        payload = {
            "query": {
                "paging": {"limit": 5, "offset": 0}
            }
        }
        print(f"   Payload: {payload}")
        response = client.post('/events/v2/guests/query', json=payload)
        print(f"   ✓ Success!")
        print(f"   Total guests: {response.get('pagingMetadata', {}).get('total', 'unknown')}")
        guests = response.get('guests', [])
        print(f"   Retrieved: {len(guests)} guests")
        if guests:
            print(f"\n   Sample guest keys: {list(guests[0].keys())}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    # Test 3: Query with fieldsets
    print("\n4. Test 3: Query with fieldsets for full details")
    print("-" * 80)
    try:
        payload = {
            "query": {
                "fieldsets": ["GUEST_DETAILS"],
                "paging": {"limit": 5, "offset": 0}
            }
        }
        print(f"   Payload: {payload}")
        response = client.post('/events/v2/guests/query', json=payload)
        print(f"   ✓ Success!")
        print(f"   Total guests: {response.get('pagingMetadata', {}).get('total', 'unknown')}")
        guests = response.get('guests', [])
        print(f"   Retrieved: {len(guests)} guests")
        if guests:
            print(f"\n   Sample guest keys: {list(guests[0].keys())}")
            print(f"   First guest sample:")
            first_guest = guests[0]
            for key, value in list(first_guest.items())[:10]:  # First 10 fields
                print(f"      {key}: {value}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    # Test 4: Query with event filter
    print("\n5. Test 4: Query with event ID filter")
    print("-" * 80)
    # Get an event ID first
    try:
        events_response = client.post('/events/v3/events/query', json={"query": {"paging": {"limit": 1}}})
        events = events_response.get('events', [])
        if events:
            event_id = events[0]['id']
            print(f"   Using event ID: {event_id}")

            payload = {
                "query": {
                    "filter": {"eventId": {"$eq": event_id}},
                    "fieldsets": ["GUEST_DETAILS"],
                    "paging": {"limit": 10, "offset": 0}
                }
            }
            print(f"   Payload: {payload}")
            response = client.post('/events/v2/guests/query', json=payload)
            print(f"   ✓ Success!")
            print(f"   Total guests for this event: {response.get('pagingMetadata', {}).get('total', 'unknown')}")
            guests = response.get('guests', [])
            print(f"   Retrieved: {len(guests)} guests")
        else:
            print("   No events found to test with")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    print("\n" + "=" * 80)
    print("Testing complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
