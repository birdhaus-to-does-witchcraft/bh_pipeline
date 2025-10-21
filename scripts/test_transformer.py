"""
Test the events transformer with real Wix API data.
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from wix_api.client import WixAPIClient
from wix_api.events import EventsAPI
from transformers.events import EventsTransformer
import json


def main():
    """Test the events transformer."""
    print("=" * 80)
    print("Testing Events Transformer")
    print("=" * 80)

    # Initialize API client
    print("\n1. Initializing Wix API client...")
    client = WixAPIClient.from_env()
    events_api = EventsAPI(client)

    # Get some events
    print("\n2. Fetching events from API...")
    response = events_api.query_events(limit=5)
    events = response.get('events', [])
    print(f"   Retrieved {len(events)} events")

    if not events:
        print("No events found!")
        return

    # Show original categories format
    print("\n3. Original categories format (hard to read):")
    print("-" * 80)
    first_event = events[0]
    categories = first_event.get('categories', {}).get('categories', [])
    print(f"Event: {first_event.get('title')}")
    print(f"categories_categories = {categories}")

    # Transform events
    print("\n4. Transforming events...")
    transformed_events = EventsTransformer.transform_events(events)

    # Show transformed categories format
    print("\n5. Transformed categories format (clean and readable):")
    print("-" * 80)
    first_transformed = transformed_events[0]
    print(f"Event: {first_transformed.get('title')}")
    print(f"category_names = {first_transformed.get('category_names')}")
    print(f"category_count = {first_transformed.get('category_count')}")
    print(f"primary_category = {first_transformed.get('primary_category')}")

    # Show comparison of all fields
    print("\n6. Sample transformed event (all fields):")
    print("-" * 80)
    for key, value in first_transformed.items():
        # Truncate long values
        if isinstance(value, str) and len(value) > 100:
            value = value[:100] + "..."
        print(f"  {key}: {value}")

    # Create DataFrame
    print("\n7. Creating DataFrame...")
    df = EventsTransformer.to_dataframe(transformed_events)
    print(f"   DataFrame shape: {df.shape}")
    print(f"   Columns: {', '.join(df.columns.tolist())}")

    # Show sample data
    print("\n8. Sample data (first 3 rows, key columns):")
    print("-" * 80)
    key_columns = ['title', 'status', 'category_names', 'start_date', 'lowest_price', 'currency']
    available_columns = [col for col in key_columns if col in df.columns]
    print(df[available_columns].head(3).to_string())

    # Save to CSV with timestamp to avoid file lock issues
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = project_root / "data" / "processed" / f"events_test_{timestamp}.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n9. Saving to CSV: {output_path}")
    EventsTransformer.save_to_csv(events, str(output_path))
    print(f"   ✓ Saved successfully!")

    print("\n" + "=" * 80)
    print("✓ Transformer test completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
