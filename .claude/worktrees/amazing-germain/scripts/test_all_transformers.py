"""
Test all transformers with the configured Wix site.

Run this script after updating WIX_SITE_ID in .env to test all transformers
with real data from your Wix site.

IMPORTANT: This script uses API wrapper classes with automatic pagination:
- EventsAPI.get_all_events() - Fetches ALL events (not just first 100)
- ContactsAPI.get_all_contacts() - Fetches ALL contacts (all 1,363+)
- GuestsAPI.get_all_guests() - Fetches ALL guests with pagination
- Orders API uses correct 'search' wrapper format

Previous version had pagination bugs that limited results to first page only.
"""

import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import os
from dotenv import load_dotenv

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from wix_api.client import WixAPIClient
from wix_api.events import EventsAPI
from wix_api.contacts import ContactsAPI
from wix_api.guests import GuestsAPI
from wix_api.orders import OrdersAPI
from transformers.events import EventsTransformer
from transformers.contacts import ContactsTransformer
from transformers.guests import GuestsTransformer
from transformers.transactions import TransactionsTransformer
from transformers.order_summaries import OrderSummariesTransformer


def test_events_transformer(client, output_dir):
    """Test the events transformer."""
    print("\n" + "=" * 80)
    print("1. TESTING EVENTS TRANSFORMER")
    print("=" * 80)

    try:
        # Fetch ALL events using API wrapper with pagination
        print("\n   Fetching ALL events from API (with automatic pagination)...")
        events_api = EventsAPI(client)
        events = events_api.get_all_events()

        print(f"   ✓ Retrieved {len(events)} events (ALL events fetched)")

        if not events:
            print("   ⚠ No events found - skipping transform")
            return None

        # Transform and save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"events_{timestamp}.csv"

        print(f"   Transforming {len(events)} events...")
        EventsTransformer.save_to_csv(events, str(output_path))

        print(f"   ✓ Saved to: {output_path.name}")

        # Verify encoding
        with open(output_path, 'rb') as f:
            first_bytes = f.read(3)
            if first_bytes == b'\xef\xbb\xbf':
                print(f"   ✓ UTF-8 BOM present (Excel-friendly)")

        # Show sample
        print(f"\n   Sample event fields:")
        transformed = EventsTransformer.transform_events(events[:1])
        if transformed:
            for key in list(transformed[0].keys())[:10]:
                print(f"      - {key}")
            print(f"      ... and {len(transformed[0]) - 10} more fields")

        return output_path

    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_contacts_transformer(client, output_dir):
    """Test the contacts transformer."""
    print("\n" + "=" * 80)
    print("2. TESTING CONTACTS TRANSFORMER")
    print("=" * 80)

    try:
        # Fetch ALL contacts using API wrapper with pagination
        print("\n   Fetching ALL contacts from API (with automatic pagination)...")
        print("   ℹ This may take a moment for sites with many contacts...")
        contacts_api = ContactsAPI(client)
        contacts = contacts_api.get_all_contacts()

        print(f"   ✓ Retrieved {len(contacts)} contacts (ALL contacts fetched)")

        if not contacts:
            print("   ⚠ No contacts found - skipping transform")
            return None

        # Transform and save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"contacts_{timestamp}.csv"

        print(f"   Transforming {len(contacts)} contacts...")
        ContactsTransformer.save_to_csv(contacts, str(output_path))

        print(f"   ✓ Saved to: {output_path.name}")

        # Verify encoding
        with open(output_path, 'rb') as f:
            first_bytes = f.read(3)
            if first_bytes == b'\xef\xbb\xbf':
                print(f"   ✓ UTF-8 BOM present (Excel-friendly)")

        # Show sample
        print(f"\n   Sample contact fields:")
        transformed = ContactsTransformer.transform_contacts(contacts[:1])
        if transformed:
            for key in list(transformed[0].keys())[:10]:
                print(f"      - {key}")
            print(f"      ... and {len(transformed[0]) - 10} more fields")

        return output_path

    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_guests_transformer(client, output_dir):
    """Test the guests transformer."""
    print("\n" + "=" * 80)
    print("3. TESTING GUESTS TRANSFORMER")
    print("=" * 80)

    try:
        # Fetch ALL guests using API wrapper with pagination
        print("\n   Fetching ALL guests from API (with automatic pagination)...")
        print("   ℹ This may take a moment for sites with many event registrations...")
        guests_api = GuestsAPI(client)
        guests = guests_api.get_all_guests()

        print(f"   ✓ Retrieved {len(guests)} guests (ALL guests fetched)")

        if not guests:
            print("   ⚠ No guests found - this is expected for dev site clones")
            print("   ℹ Guest data exists only on production sites with actual registrations")
            return None

        # Fetch contacts for enrichment (Guests API doesn't return names)
        print("\n   Fetching contacts for name enrichment...")
        print("   ℹ Wix Guests API doesn't return names - we'll join with Contacts data")
        contacts_api = ContactsAPI(client)
        contacts = contacts_api.get_all_contacts()
        print(f"   ✓ Retrieved {len(contacts)} contacts for enrichment")

        # Transform guests
        print(f"\n   Transforming {len(guests)} guests...")
        transformed_guests = GuestsTransformer.transform_guests(guests)

        # Enrich with contact data (adds names, emails, phones)
        print(f"   Enriching guests with contact data...")
        enriched_guests = GuestsTransformer.enrich_with_contact_data(transformed_guests, contacts)

        # Save to CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"guests_{timestamp}.csv"

        from transformers.base import BaseTransformer
        BaseTransformer.save_to_csv(enriched_guests, str(output_path))

        print(f"   ✓ Saved to: {output_path.name}")

        # Verify encoding
        with open(output_path, 'rb') as f:
            first_bytes = f.read(3)
            if first_bytes == b'\xef\xbb\xbf':
                print(f"   ✓ UTF-8 BOM present (Excel-friendly)")

        # Show sample with enriched data
        print(f"\n   Sample guest fields:")
        if enriched_guests:
            for key in list(enriched_guests[0].keys())[:10]:
                print(f"      - {key}")
            print(f"      ... and {len(enriched_guests[0]) - 10} more fields")

            # Show a sample enriched guest with name
            sample_with_name = next((g for g in enriched_guests if g.get('first_name')), None)
            if sample_with_name:
                print(f"\n   Sample enriched guest:")
                print(f"      Name: {sample_with_name.get('full_name', 'N/A')}")
                print(f"      Email: {sample_with_name.get('email', 'N/A')}")
                print(f"      Event ID: {sample_with_name.get('event_id', 'N/A')[:20]}...")

        return output_path

    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_order_summaries_transformer(client, output_dir, events_cache=None):
    """Test the order summaries transformer (sales data)."""
    print("\n" + "=" * 80)
    print("4. TESTING ORDER SUMMARIES TRANSFORMER (Sales Data)")
    print("=" * 80)

    try:
        # Fetch events (or use cache)
        if events_cache:
            events = events_cache
            print(f"\n   Using cached {len(events)} events")
        else:
            print("\n   Fetching all events...")
            events_api = EventsAPI(client)
            events = events_api.get_all_events()
            print(f"   ✓ Retrieved {len(events)} events")

        # Initialize Orders API
        orders_api = OrdersAPI(client)

        # Get sales summary for each event
        print(f"\n   Fetching sales summaries for {len(events)} events...")
        print("   ℹ This fetches actual payment/revenue data per event")

        summary_responses = []
        events_with_sales = 0

        for event in events:
            try:
                summary = orders_api.get_summary_by_event(event.get('id'))
                summary_responses.append(summary)

                # Count events with sales
                if summary.get('sales', []):
                    events_with_sales += 1

            except Exception as e:
                # Event may not have sales data
                summary_responses.append({'sales': []})

        print(f"   ✓ Retrieved summaries for {len(events)} events")
        print(f"   ℹ {events_with_sales} events have sales data")

        # Transform and save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"order_summaries_{timestamp}.csv"

        print(f"\n   Transforming sales data for {len(events)} events...")
        OrderSummariesTransformer.save_to_csv(events, summary_responses, str(output_path))

        print(f"   ✓ Saved to: {output_path.name}")

        # Verify encoding
        with open(output_path, 'rb') as f:
            first_bytes = f.read(3)
            if first_bytes == b'\xef\xbb\xbf':
                print(f"   ✓ UTF-8 BOM present (Excel-friendly)")

        # Show sample with sales
        print(f"\n   Sample fields:")
        transformed = OrderSummariesTransformer.transform_summaries(events[:1], summary_responses[:1])
        if transformed:
            for key in list(transformed[0].keys())[:10]:
                print(f"      - {key}")
            print(f"      ... and {len(transformed[0]) - 10} more fields")

        # Show summary stats
        all_transformed = OrderSummariesTransformer.transform_summaries(events, summary_responses)
        with_sales = [t for t in all_transformed if t.get('has_sales')]

        if with_sales:
            print(f"\n   Sample event with sales:")
            sample = with_sales[0]
            print(f"      Event: {sample.get('event_title', 'N/A')}")
            print(f"      Total Sales: {sample.get('total_sales_amount', 'N/A')} {sample.get('total_sales_currency', '')}")
            print(f"      Revenue (after fees): {sample.get('revenue_amount', 'N/A')} {sample.get('revenue_currency', '')}")
            print(f"      Orders: {sample.get('total_orders', 0)}")
            print(f"      Tickets: {sample.get('total_tickets', 0)}")

        return output_path, events  # Return events for caching

    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_transactions_transformer(client, output_dir):
    """Test the transactions transformer."""
    print("\n" + "=" * 80)
    print("5. TESTING TRANSACTIONS TRANSFORMER")
    print("=" * 80)

    try:
        # Fetch orders with correct payload format
        print("\n   Fetching orders from API...")
        # IMPORTANT: Wix Orders API requires 'search' wrapper object
        response = client.post('/ecom/v1/orders/search', json={
            'search': {
                'paging': {'limit': 100}
            }
        })
        orders = response.get('orders', [])
        total_count = response.get('totalCount', 'unknown')

        print(f"   ✓ Retrieved {len(orders)} orders (Total: {total_count})")

        if not orders:
            print("   ⚠ No orders found - skipping transform")
            return None

        # Fetch transactions for these orders
        print(f"\n   Fetching transactions for {len(orders)} orders...")
        order_ids = [o.get('id') for o in orders if o.get('id')]

        transactions_by_order = defaultdict(list)

        if order_ids:
            try:
                txn_response = client.post('/ecom/v1/orders/transactions/list',
                                          json={'orderIds': order_ids})
                transactions = txn_response.get('transactions', [])

                for txn in transactions:
                    order_id = txn.get('orderId')
                    if order_id:
                        transactions_by_order[order_id].append(txn)

                print(f"   ✓ Retrieved {len(transactions)} transactions")
            except Exception as e:
                print(f"   ⚠ Could not fetch transactions: {e}")

        # Transform and save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"transactions_{timestamp}.csv"

        print(f"   Transforming {len(orders)} orders...")
        TransactionsTransformer.save_to_csv(
            orders,
            str(output_path),
            transactions_by_order=dict(transactions_by_order) if transactions_by_order else None
        )

        print(f"   ✓ Saved to: {output_path.name}")

        # Verify encoding
        with open(output_path, 'rb') as f:
            first_bytes = f.read(3)
            if first_bytes == b'\xef\xbb\xbf':
                print(f"   ✓ UTF-8 BOM present (Excel-friendly)")

        # Show sample
        print(f"\n   Sample transaction fields:")
        transformed = TransactionsTransformer.transform_orders(
            orders[:1],
            dict(transactions_by_order) if transactions_by_order else None
        )
        if transformed:
            for key in list(transformed[0].keys())[:10]:
                print(f"      - {key}")
            print(f"      ... and {len(transformed[0]) - 10} more fields")

        return output_path

    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Test all transformers."""
    print("=" * 80)
    print("TESTING ALL TRANSFORMERS")
    print("=" * 80)

    # Load environment and show configuration
    load_dotenv()
    site_id = os.getenv('WIX_SITE_ID')
    account_id = os.getenv('WIX_ACCOUNT_ID')

    print(f"\nConfiguration:")
    print(f"  Site ID: {site_id}")
    print(f"  Account ID: {account_id}")

    if not site_id:
        print("\n✗ ERROR: WIX_SITE_ID not set in .env file!")
        print("  Please update your .env file with the production site ID")
        return

    # Initialize API client
    print(f"\nInitializing Wix API client...")
    client = WixAPIClient.from_env()
    print(f"  ✓ Client initialized")

    # Create output directory
    output_dir = project_root / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Test all transformers
    results = {}
    events_cache = None

    results['events'] = test_events_transformer(client, output_dir)
    results['contacts'] = test_contacts_transformer(client, output_dir)
    results['guests'] = test_guests_transformer(client, output_dir)

    # Order summaries uses events data - cache it to avoid re-fetching
    order_summaries_result, events_cache = test_order_summaries_transformer(client, output_dir, events_cache)
    results['order_summaries'] = order_summaries_result

    results['transactions'] = test_transactions_transformer(client, output_dir)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    successful = [name for name, path in results.items() if path is not None]
    failed = [name for name, path in results.items() if path is None]

    print(f"\n✓ Successful: {len(successful)}/{len(results)}")
    for name in successful:
        print(f"   - {name.capitalize()}: {results[name].name}")

    if failed:
        print(f"\n⚠ Skipped/Failed: {len(failed)}")
        for name in failed:
            print(f"   - {name.capitalize()}: No data or error")

    print("\n" + "=" * 80)
    print("All files saved to:", output_dir)
    print("=" * 80)

    if 'guests' in failed:
        print("\nℹ NOTE: Guests data requires production site access.")
        print("  Dev site clones don't include guest registration data.")
        print("  Update WIX_SITE_ID in .env to your production site ID to test guests.")


if __name__ == "__main__":
    main()
