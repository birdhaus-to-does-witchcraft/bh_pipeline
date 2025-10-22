"""
Full data extraction script - pulls all data from Wix APIs.

This script extracts complete datasets for all entity types:
- Events
- Event Guests
- Contacts
- Order Summaries (Sales Data)
- Transactions/Orders

All data is transformed and saved to timestamped CSV files with UTF-8 BOM encoding
for Excel compatibility.

Usage:
    python scripts/pull_all.py
    # Or with custom output directory:
    python scripts/pull_all.py --output-dir /path/to/output
    # Or if installed: wix-pull-all
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from utils.logger import setup_logging
from wix_api.client import WixAPIClient
from wix_api.events import EventsAPI
from wix_api.contacts import ContactsAPI
from wix_api.guests import GuestsAPI
from wix_api.orders import OrdersAPI
from transformers.events import EventsTransformer
from transformers.contacts import ContactsTransformer
from transformers.guests import GuestsTransformer
from transformers.order_summaries import OrderSummariesTransformer
from transformers.transactions import TransactionsTransformer
from transformers.base import BaseTransformer


def extract_events(client, output_dir, logger):
    """Extract and transform all events."""
    logger.info("=" * 60)
    logger.info("Extracting Events")
    logger.info("=" * 60)

    try:
        events_api = EventsAPI(client)
        events = events_api.get_all_events()
        logger.info(f"Retrieved {len(events)} events")

        if not events:
            logger.warning("No events found")
            return None

        # Transform and save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"events_{timestamp}.csv"

        EventsTransformer.save_to_csv(events, str(output_path))
        logger.info(f"Saved {len(events)} events to {output_path.name}")

        return events

    except Exception as e:
        logger.error(f"Events extraction failed: {e}", exc_info=True)
        return None


def extract_contacts(client, output_dir, logger):
    """Extract and transform all contacts."""
    logger.info("=" * 60)
    logger.info("Extracting Contacts")
    logger.info("=" * 60)

    try:
        contacts_api = ContactsAPI(client)
        contacts = contacts_api.get_all_contacts()
        logger.info(f"Retrieved {len(contacts)} contacts")

        if not contacts:
            logger.warning("No contacts found")
            return None

        # Transform and save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"contacts_{timestamp}.csv"

        ContactsTransformer.save_to_csv(contacts, str(output_path))
        logger.info(f"Saved {len(contacts)} contacts to {output_path.name}")

        return contacts

    except Exception as e:
        logger.error(f"Contacts extraction failed: {e}", exc_info=True)
        return None


def extract_guests(client, output_dir, contacts, logger):
    """Extract and transform all guests (enriched with contact data)."""
    logger.info("=" * 60)
    logger.info("Extracting Guests")
    logger.info("=" * 60)

    try:
        guests_api = GuestsAPI(client)
        guests = guests_api.get_all_guests()
        logger.info(f"Retrieved {len(guests)} guests")

        if not guests:
            logger.warning("No guests found - this is normal if no event registrations exist")
            return None

        # Transform guests
        transformed_guests = GuestsTransformer.transform_guests(guests)

        # Enrich with contact data (names, emails, phones)
        if contacts:
            logger.info(f"Enriching {len(guests)} guests with contact data...")
            enriched_guests = GuestsTransformer.enrich_with_contact_data(
                transformed_guests, contacts
            )
        else:
            logger.warning("No contacts available for enrichment")
            enriched_guests = transformed_guests

        # Save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"guests_{timestamp}.csv"

        BaseTransformer.save_to_csv(enriched_guests, str(output_path))
        logger.info(f"Saved {len(enriched_guests)} guests to {output_path.name}")

        return enriched_guests

    except Exception as e:
        logger.error(f"Guests extraction failed: {e}", exc_info=True)
        return None


def extract_order_summaries(client, output_dir, events, logger):
    """Extract and transform order summaries (sales data per event)."""
    logger.info("=" * 60)
    logger.info("Extracting Order Summaries (Sales Data)")
    logger.info("=" * 60)

    try:
        if not events:
            logger.warning("No events provided - cannot extract order summaries")
            return None

        orders_api = OrdersAPI(client)

        # Get sales summary for each event
        logger.info(f"Fetching sales summaries for {len(events)} events...")
        summary_responses = []
        events_with_sales = 0

        for event in events:
            try:
                summary = orders_api.get_summary_by_event(event.get('id'))
                summary_responses.append(summary)

                if summary.get('sales', []):
                    events_with_sales += 1

            except Exception:
                # Event may not have sales data
                summary_responses.append({'sales': []})

        logger.info(f"Retrieved summaries for {len(events)} events")
        logger.info(f"{events_with_sales} events have sales data")

        # Transform and save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"order_summaries_{timestamp}.csv"

        OrderSummariesTransformer.save_to_csv(events, summary_responses, str(output_path))
        logger.info(f"Saved order summaries to {output_path.name}")

        return summary_responses

    except Exception as e:
        logger.error(f"Order summaries extraction failed: {e}", exc_info=True)
        return None


def extract_transactions(client, output_dir, logger):
    """Extract and transform transactions/orders."""
    logger.info("=" * 60)
    logger.info("Extracting Transactions")
    logger.info("=" * 60)

    try:
        # Fetch orders
        logger.info("Fetching orders...")
        response = client.post('/ecom/v1/orders/search', json={
            'search': {'paging': {'limit': 100}}
        })
        orders = response.get('orders', [])
        total_count = response.get('totalCount', 'unknown')

        logger.info(f"Retrieved {len(orders)} orders (Total: {total_count})")

        if not orders:
            logger.warning("No orders found")
            return None

        # Fetch transactions for orders
        logger.info(f"Fetching transactions for {len(orders)} orders...")
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

                logger.info(f"Retrieved {len(transactions)} transactions")
            except Exception as e:
                logger.warning(f"Could not fetch transactions: {e}")

        # Transform and save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"transactions_{timestamp}.csv"

        TransactionsTransformer.save_to_csv(
            orders,
            str(output_path),
            transactions_by_order=dict(transactions_by_order) if transactions_by_order else None
        )
        logger.info(f"Saved {len(orders)} transactions to {output_path.name}")

        return orders

    except Exception as e:
        logger.error(f"Transactions extraction failed: {e}", exc_info=True)
        return None


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Extract all data from Wix APIs"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for CSV files (default: data/processed)"
    )
    return parser.parse_args()


def main():
    """Main entry point for full data extraction."""
    args = parse_args()

    # Set up logging
    logger = setup_logging(log_dir="logs", log_level="INFO")
    logger.info("=" * 60)
    logger.info("STARTING FULL DATA EXTRACTION FROM WIX APIs")
    logger.info("=" * 60)

    try:
        # Create output directory
        if args.output_dir:
            output_dir = Path(args.output_dir)
        else:
            output_dir = project_root / "data" / "processed"

        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory: {output_dir}")

        # Initialize API client
        logger.info("Initializing Wix API client...")
        client = WixAPIClient.from_env()
        logger.info("Client initialized successfully")

        # Extract all data types
        results = {}

        # Events (needed for order summaries)
        events = extract_events(client, output_dir, logger)
        results['events'] = events is not None

        # Contacts (needed for guest enrichment)
        contacts = extract_contacts(client, output_dir, logger)
        results['contacts'] = contacts is not None

        # Guests (enriched with contacts)
        guests = extract_guests(client, output_dir, contacts, logger)
        results['guests'] = guests is not None

        # Order Summaries (uses events)
        order_summaries = extract_order_summaries(client, output_dir, events, logger)
        results['order_summaries'] = order_summaries is not None

        # Transactions
        transactions = extract_transactions(client, output_dir, logger)
        results['transactions'] = transactions is not None

        # Clean up
        client.close()

        # Summary
        logger.info("=" * 60)
        logger.info("EXTRACTION SUMMARY")
        logger.info("=" * 60)

        successful = [name for name, success in results.items() if success]
        failed = [name for name, success in results.items() if not success]

        logger.info(f"Successful: {len(successful)}/{len(results)}")
        for name in successful:
            logger.info(f"  ✓ {name.capitalize()}")

        if failed:
            logger.warning(f"Skipped/Failed: {len(failed)}")
            for name in failed:
                logger.warning(f"  ✗ {name.capitalize()}")

        logger.info("=" * 60)
        logger.info(f"All files saved to: {output_dir}")
        logger.info("=" * 60)

        if all(results.values()):
            logger.info("Full data extraction completed successfully!")
            return 0
        else:
            logger.warning("Some data types were skipped or failed")
            return 0  # Still return success if at least some data was extracted

    except Exception as e:
        logger.error(f"Data extraction failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
