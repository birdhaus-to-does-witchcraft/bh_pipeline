"""
Unified API debugging tool.

Consolidates functionality from:
- debug_events.py
- debug_events_fieldsets.py
- test_endpoints.py
- test_pagination.py

This script helps debug Wix API issues with various testing options.

Usage:
    # Debug events API
    python scripts/debug_api.py --endpoint events --test response

    # Test pagination
    python scripts/debug_api.py --endpoint guests --test pagination

    # Test different fieldsets
    python scripts/debug_api.py --endpoint events --test fieldsets

    # Test endpoint paths
    python scripts/debug_api.py --endpoint events --test endpoints
"""

import sys
import json
import logging
import argparse
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from wix_api.client import WixAPIClient
from wix_api.events import EventsAPI
from wix_api.guests import GuestsAPI
from wix_api.contacts import ContactsAPI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_endpoint_paths(client):
    """Test different endpoint path variations."""
    print("\n" + "=" * 80)
    print("TESTING ENDPOINT PATHS")
    print("=" * 80)

    query_payload = {
        "query": {
            "paging": {
                "limit": 1
            }
        }
    }

    endpoints_to_test = [
        "/v3/events/query",
        "/events/v3/events/query",
        "/events/v3/query",
        "/v1/events/query",
        "/events/v1/query",
    ]

    print("\nTesting different endpoint paths...")

    for endpoint in endpoints_to_test:
        try:
            print(f"\n  Testing: POST {endpoint}")
            response = client.post(endpoint, json=query_payload)
            print(f"  ✓ SUCCESS! Response keys: {list(response.keys())}")
            print(f"  ✓ Found working endpoint: {endpoint}")
            return
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                print(f"  ✗ 404 Not Found")
            elif "400" in error_msg:
                print(f"  ✗ 400 Bad Request")
            elif "401" in error_msg:
                print(f"  ✗ 401 Unauthorized")
            elif "403" in error_msg:
                print(f"  ✗ 403 Forbidden")
            else:
                print(f"  ✗ Error: {e}")

    print("\n  None of the tested endpoints worked.")


def test_events_response(client):
    """Test events API response structure."""
    print("\n" + "=" * 80)
    print("TESTING EVENTS API RESPONSE")
    print("=" * 80)

    events_api = EventsAPI(client)

    # Test 1: Raw API call
    print("\n[1] Raw API call to /events/v3/events/query...")
    try:
        raw_response = client.post(
            "/events/v3/events/query",
            json={"query": {"paging": {"limit": 10}}}
        )
        print("\nRaw API Response:")
        print(json.dumps(raw_response, indent=2)[:1000] + "...")
    except Exception as e:
        print(f"\nERROR with raw API call: {e}")

    # Test 2: Using EventsAPI
    print("\n[2] Using EventsAPI.query_events()...")
    try:
        response = events_api.query_events(limit=10)
        print("\nEventsAPI Response:")
        print(json.dumps(response, indent=2)[:1000] + "...")

        events = response.get("events", [])
        print(f"\nNumber of events: {len(events)}")

        paging = response.get("pagingMetadata", {})
        print(f"Paging metadata: {paging}")

    except Exception as e:
        print(f"\nERROR with EventsAPI: {e}")

    # Test 3: Count by status
    print("\n[3] Event counts by status...")
    try:
        counts = events_api.count_events_by_status()
        print("\nEvent counts:")
        print(json.dumps(counts, indent=2))
    except Exception as e:
        print(f"\nERROR: {e}")


def test_events_fieldsets(client):
    """Test different fieldset configurations for events."""
    print("\n" + "=" * 80)
    print("TESTING EVENTS FIELDSETS")
    print("=" * 80)

    # Test 1: With FULL fieldset
    print("\n[1] Query with fieldsets=['FULL']...")
    try:
        response = client.post(
            "/events/v3/events/query",
            json={
                "query": {
                    "paging": {"limit": 5},
                    "fieldsets": ["FULL"]
                }
            }
        )
        print(f"  Response keys: {list(response.keys())}")
        print(f"  Number of events: {len(response.get('events', []))}")
        if response.get('events'):
            print(f"  First event keys: {list(response['events'][0].keys())}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Test 2: Without fieldsets
    print("\n[2] Query without fieldsets...")
    try:
        response = client.post(
            "/events/v3/events/query",
            json={"query": {"paging": {"limit": 5}}}
        )
        print(f"  Response keys: {list(response.keys())}")
        print(f"  Number of events: {len(response.get('events', []))}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Test 3: With cursorPaging
    print("\n[3] Query with cursorPaging...")
    try:
        response = client.post(
            "/events/v3/events/query",
            json={"query": {"cursorPaging": {"limit": 5}}}
        )
        print(f"  Response keys: {list(response.keys())}")
        print(f"  Paging: {response.get('pagingMetadata', {})}")
    except Exception as e:
        print(f"  ERROR: {e}")


def test_events_pagination(client):
    """Test pagination behavior for events."""
    print("\n" + "=" * 80)
    print("TESTING EVENTS PAGINATION")
    print("=" * 80)

    events_api = EventsAPI(client)

    print("\nPage 1 (offset=0, limit=100):")
    response = events_api.query_events(limit=100, offset=0)
    paging = response.get('pagingMetadata', {})
    print(f"  Count: {paging.get('count')}")
    print(f"  Total: {paging.get('total')}")
    print(f"  Offset: {paging.get('offset')}")
    print(f"  Has Next: {paging.get('hasNext', 'N/A')}")
    print(f"  Actual events returned: {len(response.get('events', []))}")

    if paging.get('total', 0) > 100:
        print("\nPage 2 (offset=100, limit=100):")
        response = events_api.query_events(limit=100, offset=100)
        paging = response.get('pagingMetadata', {})
        print(f"  Count: {paging.get('count')}")
        print(f"  Total: {paging.get('total')}")
        print(f"  Offset: {paging.get('offset')}")
        print(f"  Has Next: {paging.get('hasNext', 'N/A')}")
        print(f"  Actual events returned: {len(response.get('events', []))}")


def test_guests_response(client):
    """Test guests API response structure."""
    print("\n" + "=" * 80)
    print("TESTING GUESTS API RESPONSE")
    print("=" * 80)

    guests_api = GuestsAPI(client)

    # Test with fieldsets
    print("\n[1] Query with fieldsets=['GUEST_DETAILS']...")
    try:
        response = guests_api.query_guests(limit=10, include_details=True)
        print(f"\n  Response keys: {list(response.keys())}")

        guests = response.get('guests', [])
        paging = response.get('pagingMetadata', {})

        print(f"  Number of guests: {len(guests)}")
        print(f"  Paging: {paging}")

        if guests:
            print(f"\n  Sample guest keys: {list(guests[0].keys())}")
            print("\n  Sample guest:")
            print(json.dumps(guests[0], indent=4)[:500] + "...")
        else:
            print("\n  No guests found")

    except Exception as e:
        print(f"  ERROR: {e}")
        logger.exception("Guests API error")


def test_guests_pagination(client):
    """Test pagination behavior for guests."""
    print("\n" + "=" * 80)
    print("TESTING GUESTS PAGINATION")
    print("=" * 80)

    guests_api = GuestsAPI(client)

    print("\nPage 1 (offset=0, limit=100):")
    response = guests_api.query_guests(limit=100, offset=0)
    paging = response.get('pagingMetadata', {})
    print(f"  Count: {paging.get('count')}")
    print(f"  Total: {paging.get('total', 'Not provided')}")
    print(f"  Offset: {paging.get('offset')}")
    print(f"  Actual guests returned: {len(response.get('guests', []))}")

    # Test second page if we got a full page
    if paging.get('count', 0) >= 100:
        print("\nPage 2 (offset=100, limit=100):")
        response = guests_api.query_guests(limit=100, offset=100)
        paging = response.get('pagingMetadata', {})
        print(f"  Count: {paging.get('count')}")
        print(f"  Total: {paging.get('total', 'Not provided')}")
        print(f"  Offset: {paging.get('offset')}")
        print(f"  Actual guests returned: {len(response.get('guests', []))}")


def test_contacts_response(client):
    """Test contacts API response structure."""
    print("\n" + "=" * 80)
    print("TESTING CONTACTS API RESPONSE")
    print("=" * 80)

    contacts_api = ContactsAPI(client)

    print("\n[1] List contacts (limit=10)...")
    try:
        response = contacts_api.list_contacts(limit=10)
        print(f"\n  Response keys: {list(response.keys())}")

        contacts = response.get('contacts', [])
        paging = response.get('pagingMetadata', {})

        print(f"  Number of contacts: {len(contacts)}")
        print(f"  Paging: {paging}")

        if contacts:
            print(f"\n  Sample contact keys: {list(contacts[0].keys())}")
            print("\n  Sample contact:")
            print(json.dumps(contacts[0], indent=4)[:500] + "...")

    except Exception as e:
        print(f"  ERROR: {e}")
        logger.exception("Contacts API error")


def test_contacts_pagination(client):
    """Test pagination behavior for contacts."""
    print("\n" + "=" * 80)
    print("TESTING CONTACTS PAGINATION")
    print("=" * 80)

    contacts_api = ContactsAPI(client)

    print("\nPage 1 (offset=0, limit=100):")
    response = contacts_api.list_contacts(limit=100)
    paging = response.get('pagingMetadata', {})
    print(f"  Count: {paging.get('count')}")
    print(f"  Total: {paging.get('total')}")
    print(f"  Has Next: {paging.get('hasNext', 'N/A')}")
    print(f"  Actual contacts returned: {len(response.get('contacts', []))}")

    if paging.get('hasNext'):
        print("\nPage 2 (offset=100, limit=100):")
        response = contacts_api.list_contacts(limit=100, offset=100)
        paging = response.get('pagingMetadata', {})
        print(f"  Count: {paging.get('count')}")
        print(f"  Total: {paging.get('total')}")
        print(f"  Has Next: {paging.get('hasNext', 'N/A')}")
        print(f"  Actual contacts returned: {len(response.get('contacts', []))}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Debug Wix API endpoints')
    parser.add_argument(
        '--endpoint',
        choices=['events', 'guests', 'contacts'],
        default='events',
        help='API endpoint to debug (default: events)'
    )
    parser.add_argument(
        '--test',
        choices=['response', 'pagination', 'fieldsets', 'endpoints'],
        default='response',
        help='Type of test to run (default: response)'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("WIX API DEBUGGING TOOL")
    print("=" * 80)
    print(f"\nEndpoint: {args.endpoint}")
    print(f"Test: {args.test}")

    # Initialize client
    print("\nInitializing client...")
    client = WixAPIClient.from_env()
    print("  ✓ Client initialized")

    # Run appropriate test
    try:
        if args.endpoint == 'events':
            if args.test == 'response':
                test_events_response(client)
            elif args.test == 'pagination':
                test_events_pagination(client)
            elif args.test == 'fieldsets':
                test_events_fieldsets(client)
            elif args.test == 'endpoints':
                test_endpoint_paths(client)

        elif args.endpoint == 'guests':
            if args.test == 'response':
                test_guests_response(client)
            elif args.test == 'pagination':
                test_guests_pagination(client)
            else:
                print(f"\n  Test '{args.test}' not implemented for guests")

        elif args.endpoint == 'contacts':
            if args.test == 'response':
                test_contacts_response(client)
            elif args.test == 'pagination':
                test_contacts_pagination(client)
            else:
                print(f"\n  Test '{args.test}' not implemented for contacts")

    finally:
        client.close()

    print("\n" + "=" * 80)
    print("DEBUG COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
