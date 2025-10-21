"""
Diagnostic script to help identify why guests API returns no data.
"""

import sys
import json
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from wix_api.client import WixAPIClient
import os
from dotenv import load_dotenv

def main():
    """Diagnose guests API issue."""
    print("=" * 80)
    print("Guests API Diagnostic Script")
    print("=" * 80)

    # Load environment
    load_dotenv()

    # Check configuration
    print("\n1. Checking Configuration")
    print("-" * 80)
    site_id = os.getenv('WIX_SITE_ID')
    account_id = os.getenv('WIX_ACCOUNT_ID')
    api_key_preview = os.getenv('WIX_API_KEY', '')[:10] + '...' if os.getenv('WIX_API_KEY') else 'NOT SET'

    print(f"   Site ID: {site_id}")
    print(f"   Account ID: {account_id}")
    print(f"   API Key: {api_key_preview}")

    # Initialize client
    print("\n2. Initializing Client")
    print("-" * 80)
    client = WixAPIClient.from_env()
    print(f"   ✓ Client initialized")
    print(f"   Base URL: {client.base_url}")

    # Test Events API (we know this works)
    print("\n3. Testing Events API (Baseline)")
    print("-" * 80)
    try:
        response = client.post('/events/v3/events/query', json={'query': {'paging': {'limit': 3}}})
        events = response.get('events', [])
        total = response.get('pagingMetadata', {}).get('total', 'unknown')
        print(f"   ✓ Events API works!")
        print(f"   Total events: {total}")
        print(f"   Retrieved: {len(events)} events")

        if events:
            for i, event in enumerate(events, 1):
                print(f"\n   Event {i}:")
                print(f"      ID: {event['id']}")
                print(f"      Title: {event['title']}")
                print(f"      Status: {event['status']}")

                # Check ticket sales info
                reg = event.get('registration', {})
                tickets = reg.get('tickets', {})
                if tickets:
                    print(f"      Ticketing: ENABLED")
                    print(f"        Currency: {tickets.get('currency')}")
                    print(f"        Price: {tickets.get('lowestPrice', {}).get('formattedValue')} - {tickets.get('highestPrice', {}).get('formattedValue')}")
                    print(f"        Sold Out: {tickets.get('soldOut')}")
                else:
                    rsvp = reg.get('rsvp', {})
                    if rsvp:
                        print(f"      RSVP: ENABLED")
                    else:
                        print(f"      Registration: NONE")
    except Exception as e:
        print(f"   ✗ Events API failed: {e}")
        return

    # Test Guests API with various approaches
    print("\n4. Testing Guests API - All Guests")
    print("-" * 80)
    try:
        response = client.post('/events-guests/v2/guests/query', json={
            'query': {
                'fieldsets': ['GUEST_DETAILS'],
                'paging': {'limit': 10}
            }
        })
        guests = response.get('guests', [])
        paging = response.get('pagingMetadata', {})
        print(f"   Response received")
        print(f"   Total from paging: {paging.get('total', 'not specified')}")
        print(f"   Count: {paging.get('count', 'not specified')}")
        print(f"   Guests returned: {len(guests)}")

        if guests:
            print(f"\n   ✓ Found guests!")
            print(f"   First guest:")
            print(json.dumps(guests[0], indent=6))
        else:
            print(f"   No guests found")
            print(f"   Full response:")
            print(json.dumps(response, indent=6))
    except Exception as e:
        print(f"   ✗ Guests API failed: {e}")

    # Test Guests API for specific event
    if events:
        print("\n5. Testing Guests API - By Event ID")
        print("-" * 80)
        test_event = events[0]
        print(f"   Testing with event: {test_event['title']}")
        print(f"   Event ID: {test_event['id']}")

        try:
            response = client.post('/events-guests/v2/guests/query', json={
                'query': {
                    'filter': {'eventId': {'$eq': test_event['id']}},
                    'fieldsets': ['GUEST_DETAILS'],
                    'paging': {'limit': 10}
                }
            })
            guests = response.get('guests', [])
            paging = response.get('pagingMetadata', {})
            print(f"   Guests for this event: {len(guests)}")

            if guests:
                print(f"\n   ✓ Found event-specific guests!")
                print(json.dumps(guests[0], indent=6))
            else:
                print(f"   No guests found for this event")
        except Exception as e:
            print(f"   ✗ Failed: {e}")

    # Test Contacts API (alternative data source)
    print("\n6. Testing Contacts API")
    print("-" * 80)
    try:
        response = client.post('/contacts/v4/contacts/query', json={
            'paging': {'limit': 5}
        })
        contacts = response.get('contacts', [])
        print(f"   ✓ Contacts API works!")
        print(f"   Retrieved: {len(contacts)} contacts")
    except Exception as e:
        print(f"   ✗ Contacts API failed: {e}")

    # Summary
    print("\n" + "=" * 80)
    print("Diagnostic Summary")
    print("=" * 80)
    print("\nPossible Issues:")
    print("  1. Guests data might not be in this Wix site/account")
    print("  2. API key might not have permission to read guest data")
    print("  3. Events might not have actual guest registrations yet")
    print("  4. Guest data might be in Wix Stores/Orders instead of Events Guests")
    print("\nNext Steps:")
    print("  - Verify the Site ID matches the Wix site with event attendees")
    print("  - Check API key permissions in Wix Dashboard")
    print("  - Try querying /ecom/v1/orders instead for ticket purchases")
    print("=" * 80)


if __name__ == "__main__":
    main()
