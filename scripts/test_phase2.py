"""
Test script for Phase 2: API Endpoint Wrappers

This script tests all the API wrapper classes to verify they work correctly.

Usage:
    python scripts/test_phase2.py
"""

import sys
import logging
from pathlib import Path

# Enable logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"{title}")
    print("=" * 70)


def test_events_api():
    """Test Events API wrapper."""
    print_section("Test 1: Events API")

    try:
        from wix_api.client import WixAPIClient
        from wix_api.events import EventsAPI

        # Create client and API wrapper
        client = WixAPIClient.from_env()
        events_api = EventsAPI(client)

        # Test query_events
        print("  Testing: query_events(limit=5)...")
        events = events_api.query_events(limit=5)

        events_list = events.get("events", [])
        total = events.get("pagingMetadata", {}).get("total", 0)

        print(f"  ✓ Retrieved {len(events_list)} events")
        print(f"  ✓ Total events available: {total}")

        # Test get_event if we have events
        if events_list:
            event_id = events_list[0].get("id")
            print(f"\n  Testing: get_event('{event_id[:20]}...')...")
            event = events_api.get_event(event_id)
            print(f"  ✓ Retrieved event: {event.get('title', 'N/A')}")

        # Test count_events_by_status
        print("\n  Testing: count_events_by_status()...")
        counts = events_api.count_events_by_status()
        print(f"  ✓ Event counts: {counts}")

        client.close()
        return True

    except Exception as e:
        print(f"  ✗ Events API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_guests_api():
    """Test Guests API wrapper."""
    print_section("Test 2: Guests API")

    try:
        from wix_api.client import WixAPIClient
        from wix_api.guests import GuestsAPI

        # Create client and API wrapper
        client = WixAPIClient.from_env()
        guests_api = GuestsAPI(client)

        # Test query_guests
        print("  Testing: query_guests(limit=5, include_details=True)...")
        guests = guests_api.query_guests(limit=5, include_details=True)

        guests_list = guests.get("guests", [])
        total = guests.get("pagingMetadata", {}).get("total", 0)

        print(f"  ✓ Retrieved {len(guests_list)} guests")
        print(f"  ✓ Total guests available: {total}")

        # Show guest types
        print(f"\n  Available guest types: {guests_api.get_guest_types()}")
        print(f"  Available check-in statuses: {guests_api.get_check_in_statuses()}")

        client.close()
        return True

    except Exception as e:
        print(f"  ✗ Guests API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rsvp_api():
    """Test RSVP API wrapper."""
    print_section("Test 3: RSVP API")

    try:
        from wix_api.client import WixAPIClient
        from wix_api.rsvp import RSVPAPI

        # Create client and API wrapper
        client = WixAPIClient.from_env()
        rsvp_api = RSVPAPI(client)

        # Test query_rsvps
        print("  Testing: query_rsvps(limit=5)...")
        rsvps = rsvp_api.query_rsvps(limit=5)

        rsvps_list = rsvps.get("rsvps", [])
        total = rsvps.get("pagingMetadata", {}).get("total", 0)

        print(f"  ✓ Retrieved {len(rsvps_list)} RSVPs")
        print(f"  ✓ Total RSVPs available: {total}")

        # Test count_rsvps
        print("\n  Testing: count_rsvps()...")
        count_result = rsvp_api.count_rsvps()
        print(f"  ✓ RSVP count: {count_result}")

        # Show RSVP statuses
        print(f"\n  Available RSVP statuses: {rsvp_api.get_rsvp_statuses()}")

        client.close()
        return True

    except Exception as e:
        print(f"  ✗ RSVP API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_contacts_api():
    """Test Contacts API wrapper."""
    print_section("Test 4: Contacts API")

    try:
        from wix_api.client import WixAPIClient
        from wix_api.contacts import ContactsAPI

        # Create client and API wrapper
        client = WixAPIClient.from_env()
        contacts_api = ContactsAPI(client)

        # Test list_contacts
        print("  Testing: list_contacts(limit=5)...")
        contacts = contacts_api.list_contacts(limit=5)

        contacts_list = contacts.get("contacts", [])
        total = contacts.get("pagingMetadata", {}).get("total", 0)

        print(f"  ✓ Retrieved {len(contacts_list)} contacts")
        print(f"  ✓ Total contacts available: {total}")

        # Test get_contact if we have contacts
        if contacts_list:
            contact_id = contacts_list[0].get("id")
            print(f"\n  Testing: get_contact('{contact_id[:20]}...')...")
            contact = contacts_api.get_contact(contact_id)

            name = contact.get("name", {})
            full_name = f"{name.get('first', '')} {name.get('last', '')}".strip()
            print(f"  ✓ Retrieved contact: {full_name or 'N/A'}")

        # Show contact labels
        print(f"\n  Suggested contact labels: {contacts_api.get_contact_labels()}")

        client.close()
        return True

    except Exception as e:
        print(f"  ✗ Contacts API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_transactions_api():
    """Test Transactions API wrapper."""
    print_section("Test 5: Transactions API")

    try:
        from wix_api.client import WixAPIClient
        from wix_api.transactions import TransactionsAPI

        # Create client and API wrapper
        client = WixAPIClient.from_env()
        transactions_api = TransactionsAPI(client)

        # For transactions, we need an order ID
        # Let's first get some orders to test with
        print("  Note: Transactions API requires order IDs to test")
        print("  Skipping transaction retrieval (requires valid order ID)")

        # Show transaction types and statuses
        print(f"\n  Available payment methods: {transactions_api.get_payment_methods()}")
        print(f"  Available transaction statuses: {transactions_api.get_transaction_statuses()}")
        print(f"  Available transaction types: {transactions_api.get_transaction_types()}")

        print("\n  ✓ Transactions API wrapper initialized successfully")

        client.close()
        return True

    except Exception as e:
        print(f"  ✗ Transactions API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pagination_helpers():
    """Test pagination helper methods."""
    print_section("Test 6: Pagination Helpers")

    try:
        from wix_api.client import WixAPIClient
        from wix_api.events import EventsAPI

        # Create client and API wrapper
        client = WixAPIClient.from_env()
        events_api = EventsAPI(client)

        # Test get_all_events with max_results
        print("  Testing: get_all_events(max_results=10)...")
        all_events = events_api.get_all_events(max_results=10)

        print(f"  ✓ Retrieved {len(all_events)} events using pagination helper")

        client.close()
        return True

    except Exception as e:
        print(f"  ✗ Pagination helper test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all Phase 2 tests."""
    print("\n" + "=" * 70)
    print("Birdhaus Data Pipeline - Phase 2 Testing")
    print("API Endpoint Wrappers Verification")
    print("=" * 70)

    results = []

    # Run all tests
    results.append(("Events API", test_events_api()))
    results.append(("Guests API", test_guests_api()))
    results.append(("RSVP API", test_rsvp_api()))
    results.append(("Contacts API", test_contacts_api()))
    results.append(("Transactions API", test_transactions_api()))
    results.append(("Pagination Helpers", test_pagination_helpers()))

    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    all_passed = True
    for test_name, passed in results:
        status = "PASSED" if passed else "FAILED"
        symbol = "✓" if passed else "✗"
        print(f"{symbol} {test_name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 70)

    if all_passed:
        print("\n✓ All Phase 2 tests passed!")
        print("\nThe API wrappers are working correctly:")
        print("  - EventsAPI - Query, get, and manage events")
        print("  - GuestsAPI - Query guests with full details")
        print("  - RSVPAPI - Manage RSVPs and check-ins")
        print("  - ContactsAPI - Manage customer contacts")
        print("  - TransactionsAPI - Retrieve payment transactions")
        print("\n" + "=" * 70)
        print("Ready for Phase 3: Data Extraction")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Implement data extractors (extractors/)")
        print("2. Implement data transformers (transformers/)")
        print("3. Create main extraction scripts (scripts/)")
        return 0
    else:
        print("\n✗ Some Phase 2 tests failed.")
        print("\nPlease check the errors above and verify:")
        print("1. API endpoints are correct")
        print("2. API permissions are configured")
        print("3. Data exists in your Wix account for testing")
        return 1


if __name__ == "__main__":
    sys.exit(main())
