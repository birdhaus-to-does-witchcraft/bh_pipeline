"""
Show the new fields added to the transformer.
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from wix_api.client import WixAPIClient
from wix_api.events import EventsAPI
from transformers.events import EventsTransformer


def main():
    """Show new fields."""
    print("=" * 80)
    print("NEW FIELDS ADDED TO EVENTS TRANSFORMER")
    print("=" * 80)

    # Get sample event
    client = WixAPIClient.from_env()
    events_api = EventsAPI(client)
    response = events_api.query_events(limit=1)
    events = response.get('events', [])

    if not events:
        print("No events found!")
        return

    transformed = EventsTransformer.transform_event(events[0])

    print("\n📍 DETAILED ADDRESS BREAKDOWN (5 new fields)")
    print("-" * 80)
    print(f"  location_subdivision (State/Province): {transformed.get('location_subdivision')}")
    print(f"  location_postal_code: {transformed.get('location_postal_code')}")
    print(f"  street_number: {transformed.get('street_number')}")
    print(f"  street_name: {transformed.get('street_name')}")
    print(f"  street_apt (Apartment): {transformed.get('street_apt')}")

    print("\n🖼️  IMAGE DIMENSIONS (2 new fields)")
    print("-" * 80)
    print(f"  main_image_width: {transformed.get('main_image_width')} px")
    print(f"  main_image_height: {transformed.get('main_image_height')} px")

    print("\n📝 DESCRIPTION FIELDS (4 fields total)")
    print("-" * 80)
    print(f"  short_description: {transformed.get('short_description')}")

    detailed = transformed.get('detailed_description', '')
    if detailed:
        print(f"  detailed_description: {detailed[:100]}...")
    else:
        print(f"  detailed_description: (empty)")

    rich_text = transformed.get('description_rich_text', '')
    if rich_text:
        print(f"  description_rich_text: {rich_text[:100]}...")
    else:
        print(f"  description_rich_text: (empty)")

    full = transformed.get('description_full', '')
    if full:
        print(f"  description_full: {full[:100]}...")
    else:
        print(f"  description_full: (empty)")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nTotal fields in transformed data: {len(transformed)}")
    print(f"\nBreakdown:")
    print(f"  - Original fields: 39")
    print(f"  - Address breakdown: +5 fields")
    print(f"  - Image dimensions: +2 fields")
    print(f"  - Description fields: +2 fields (detailed_description, description_rich_text)")
    print(f"  - Total: 48 fields")

    print("\n" + "=" * 80)
    print("DESCRIPTION FIELD LOGIC")
    print("=" * 80)
    print("""
The transformer now includes 4 description fields:

1. short_description - The brief event summary
2. detailed_description - Plain text detailed description (if available)
3. description_rich_text - Extracted from rich text nodes (if available)
4. description_full - Smart field that uses the best available description:
   → First tries: description_rich_text
   → Falls back to: detailed_description
   → Last resort: short_description

For most analysis, use 'description_full' - it gives you the best available text.
""")


if __name__ == "__main__":
    main()
