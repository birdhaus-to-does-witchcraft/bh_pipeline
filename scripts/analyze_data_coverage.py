"""
Analyze what data is kept vs removed in the transformation.
Supports: events, guests, contacts, orders, order_summaries
"""

import sys
from pathlib import Path
import json

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from wix_api.client import WixAPIClient
from wix_api.events import EventsAPI
from wix_api.guests import GuestsAPI
from wix_api.contacts import ContactsAPI
from wix_api.orders import OrdersAPI
from transformers.events import EventsTransformer
from transformers.guests import GuestsTransformer
from transformers.contacts import ContactsTransformer
from transformers.order_summaries import OrderSummariesTransformer


def flatten_dict(d, parent_key='', sep='_'):
    """Recursively flatten a nested dictionary."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            # For lists of dicts, just note it's a complex structure
            items.append((new_key, f"<list of {len(v)} objects>"))
        else:
            items.append((new_key, v))
    return dict(items)


def analyze_events(client):
    """Analyze events data transformation."""
    print("\n" + "=" * 80)
    print("EVENTS DATA ANALYSIS")
    print("=" * 80)

    events_api = EventsAPI(client)
    response = events_api.query_events(limit=1)
    events = response.get('events', [])

    if not events:
        print("No events found!")
        return

    raw_event = events[0]
    transformed_event = EventsTransformer.transform_event(raw_event)

    # Flatten raw event to see all possible fields
    flattened_raw = flatten_dict(raw_event)

    print(f"\n📊 Raw API Response Fields: {len(flattened_raw)}")
    print(f"📊 Transformed Fields: {len(transformed_event)}")
    print(f"📊 Difference: {len(flattened_raw) - len(transformed_event)} fields")

    # Categorize fields
    kept_fields = set()
    transformed_fields = set(transformed_event.keys())

    # Map raw fields to transformed fields
    field_mapping = {
        'id': 'event_id',
        'title': 'title',
        'slug': 'slug',
        'status': 'status',
        'shortDescription': 'short_description',
        'detailedDescription': 'description_text',
        'categories_categories': ['category_names', 'category_count', 'primary_category'],
        'dateAndTimeSettings_startDate': 'start_date',
        'dateAndTimeSettings_endDate': 'end_date',
        'dateAndTimeSettings_timeZoneId': 'timezone',
        'dateAndTimeSettings_recurrenceStatus': 'recurrence_status',
        'dateAndTimeSettings_formatted_dateAndTime': 'formatted_date_time',
        'location_name': 'location_name',
        'location_type': 'location_type',
        'location_address_formattedAddress': 'location_address',
        'location_address_city': 'location_city',
        'location_address_country': 'location_country',
        'location_address_geocode_latitude': 'location_latitude',
        'location_address_geocode_longitude': 'location_longitude',
        'registration_type': 'registration_type',
        'registration_status': 'registration_status',
        'registration_tickets_currency': 'currency',
        'registration_tickets_lowestPrice_value': 'lowest_price',
        'registration_tickets_highestPrice_value': 'highest_price',
        'registration_tickets_soldOut': 'sold_out',
        'mainImage_url': 'main_image_url',
        'mainImage_id': 'main_image_id',
        'createdDate': 'created_date',
        'updatedDate': 'updated_date',
        'publishedDate': 'published_date',
        'instanceId': 'instance_id',
        'userId': 'user_id',
        'guestListSettings_displayedPublicly': 'guest_list_public',
        'onlineConferencing_enabled': 'online_conference_enabled',
        'onlineConferencing_type': 'online_conference_type',
        'calendarUrls_google': 'google_calendar_url',
        'calendarUrls_ics': 'ics_calendar_url',
        'description': 'description_text',
    }

    # Print categorized breakdown
    print("\n" + "=" * 80)
    print("KEPT DATA (transformed and included)")
    print("=" * 80)

    kept_categories = {
        'Basic Info': ['id', 'title', 'slug', 'status', 'shortDescription'],
        'Categories': ['categories_categories'],
        'Dates & Times': [k for k in flattened_raw.keys() if k.startswith('dateAndTimeSettings_')],
        'Location': [k for k in flattened_raw.keys() if k.startswith('location_')],
        'Registration': [k for k in flattened_raw.keys() if k.startswith('registration_') and not k.startswith('registration_rsvp_') and not k.startswith('registration_tickets_confirmationMessages')],
        'Pricing': [k for k in flattened_raw.keys() if 'price' in k.lower() or 'currency' in k.lower()],
        'Images': [k for k in flattened_raw.keys() if k.startswith('mainImage_')],
        'Metadata': ['createdDate', 'updatedDate', 'publishedDate', 'instanceId', 'userId'],
        'Calendar URLs': [k for k in flattened_raw.keys() if k.startswith('calendarUrls_')],
        'Online Conference': [k for k in flattened_raw.keys() if k.startswith('onlineConferencing_')],
        'Guest Settings': [k for k in flattened_raw.keys() if k.startswith('guestListSettings_')],
        'Description': ['description', 'detailedDescription'],
    }

    for category, fields in kept_categories.items():
        matching = [f for f in fields if f in flattened_raw]
        if matching:
            print(f"\n{category}: ({len(matching)} fields)")
            for field in matching[:5]:  # Show first 5
                value = flattened_raw.get(field)
                if isinstance(value, str) and len(value) > 50:
                    value = value[:50] + "..."
                print(f"  ✓ {field}: {value}")
            if len(matching) > 5:
                print(f"  ... and {len(matching) - 5} more")

    print("\n" + "=" * 80)
    print("REMOVED DATA (not included in transformation)")
    print("=" * 80)

    # Find fields that weren't explicitly kept
    kept_raw_fields = set()
    for fields in kept_categories.values():
        kept_raw_fields.update(fields)

    removed_fields = set(flattened_raw.keys()) - kept_raw_fields

    removed_categories = {
        'Form Fields': [k for k in removed_fields if k.startswith('form_')],
        'RSVP Messages': [k for k in removed_fields if 'confirmationMessages' in k or k.startswith('registration_rsvp_')],
        'Rich Text Structure': [k for k in removed_fields if 'nodes' in k or 'paragraphData' in k or 'textData' in k],
        'Address Details': [k for k in removed_fields if 'subdivisions' in k or 'streetAddress' in k],
        'Ticket Details': [k for k in removed_fields if 'tickets_' in k and k not in kept_raw_fields],
        'Event Display Settings': [k for k in removed_fields if 'eventDisplaySettings' in k or 'labellingSettings' in k],
        'Image Dimensions': [k for k in removed_fields if 'mainImage_height' in k or 'mainImage_width' in k],
        'Recurring Event Details': [k for k in removed_fields if 'recurringEvents' in k],
        'Other': [k for k in removed_fields if not any([
            k.startswith('form_'),
            'confirmationMessages' in k,
            'nodes' in k,
            'subdivisions' in k,
            'tickets_' in k,
            'eventDisplaySettings' in k,
            'mainImage_height' in k,
            'recurringEvents' in k,
        ])],
    }

    for category, fields in removed_categories.items():
        if fields:
            print(f"\n{category}: ({len(fields)} fields removed)")
            for field in sorted(fields)[:5]:  # Show first 5
                value = flattened_raw.get(field)
                if isinstance(value, str) and len(value) > 50:
                    value = value[:50] + "..."
                print(f"  ✗ {field}: {value}")
            if len(fields) > 5:
                print(f"  ... and {len(fields) - 5} more")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total_kept = sum(len(fields) for fields in kept_categories.values() if fields)
    total_removed = sum(len(fields) for fields in removed_categories.values() if fields)

    print(f"\n✓ Kept: {total_kept} raw fields → {len(transformed_event)} transformed fields")
    print(f"✗ Removed: {total_removed} raw fields")
    print(f"\nTotal raw fields: {len(flattened_raw)}")


def analyze_guests(client):
    """Analyze guests data transformation."""
    print("\n" + "=" * 80)
    print("GUESTS DATA ANALYSIS")
    print("=" * 80)

    guests_api = GuestsAPI(client)
    response = guests_api.query_guests(limit=1)
    guests = response.get('guests', [])

    if not guests:
        print("No guests found!")
        return

    raw_guest = guests[0]
    transformed_guest = GuestsTransformer.transform_guest(raw_guest)
    flattened_raw = flatten_dict(raw_guest)

    print(f"\n📊 Raw API Response Fields: {len(flattened_raw)}")
    print(f"📊 Transformed Fields: {len(transformed_guest)}")
    print(f"📊 Difference: {len(flattened_raw) - len(transformed_guest)} fields")

    print("\n✓ Sample transformed fields:")
    for i, (key, value) in enumerate(list(transformed_guest.items())[:10]):
        if isinstance(value, str) and len(value) > 50:
            value = value[:50] + "..."
        print(f"  {key}: {value}")
    if len(transformed_guest) > 10:
        print(f"  ... and {len(transformed_guest) - 10} more")


def analyze_contacts(client):
    """Analyze contacts data transformation."""
    print("\n" + "=" * 80)
    print("CONTACTS DATA ANALYSIS")
    print("=" * 80)

    contacts_api = ContactsAPI(client)
    response = contacts_api.list_contacts(limit=1)
    contacts = response.get('contacts', [])

    if not contacts:
        print("No contacts found!")
        return

    raw_contact = contacts[0]
    transformed_contact = ContactsTransformer.transform_contact(raw_contact)
    flattened_raw = flatten_dict(raw_contact)

    print(f"\n📊 Raw API Response Fields: {len(flattened_raw)}")
    print(f"📊 Transformed Fields: {len(transformed_contact)}")
    print(f"📊 Difference: {len(flattened_raw) - len(transformed_contact)} fields")

    print("\n✓ Sample transformed fields:")
    for i, (key, value) in enumerate(list(transformed_contact.items())[:10]):
        if isinstance(value, str) and len(value) > 50:
            value = value[:50] + "..."
        print(f"  {key}: {value}")
    if len(transformed_contact) > 10:
        print(f"  ... and {len(transformed_contact) - 10} more")


def analyze_order_summaries(client):
    """Analyze order summaries data transformation."""
    print("\n" + "=" * 80)
    print("ORDER SUMMARIES DATA ANALYSIS")
    print("=" * 80)

    # Get a sample event first
    events_api = EventsAPI(client)
    response = events_api.query_events(limit=1)
    events = response.get('events', [])

    if not events:
        print("No events found!")
        return

    event = events[0]
    event_id = event.get('id')
    event_title = event.get('title', 'Unknown Event')

    # Get order summary for this event
    orders_api = OrdersAPI(client)
    summary_response = orders_api.get_summary(event_id=event_id)

    transformed_summary = OrderSummariesTransformer.transform_summary(
        event_id, event_title, summary_response
    )
    flattened_raw = flatten_dict(summary_response)

    print(f"\n📊 Raw API Response Fields: {len(flattened_raw)}")
    print(f"📊 Transformed Fields: {len(transformed_summary)}")
    print(f"📊 Difference: {len(flattened_raw) - len(transformed_summary)} fields")

    print("\n✓ Transformed fields:")
    for key, value in transformed_summary.items():
        if isinstance(value, str) and len(value) > 50:
            value = value[:50] + "..."
        print(f"  {key}: {value}")


def main():
    """Analyze data coverage for all data types."""
    import argparse

    parser = argparse.ArgumentParser(description='Analyze data transformation coverage')
    parser.add_argument('--type', choices=['events', 'guests', 'contacts', 'orders', 'all'],
                       default='all', help='Data type to analyze (default: all)')
    args = parser.parse_args()

    print("=" * 80)
    print("DATA COVERAGE ANALYSIS: Raw API → Transformed Data")
    print("=" * 80)

    client = WixAPIClient.from_env()

    if args.type == 'all':
        analyze_events(client)
        analyze_guests(client)
        analyze_contacts(client)
        analyze_order_summaries(client)
    elif args.type == 'events':
        analyze_events(client)
    elif args.type == 'guests':
        analyze_guests(client)
    elif args.type == 'contacts':
        analyze_contacts(client)
    elif args.type == 'orders':
        analyze_order_summaries(client)

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
