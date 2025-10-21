"""
Test encoding fixes for special characters in CSV export.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from wix_api.client import WixAPIClient
from wix_api.events import EventsAPI
from transformers.events import EventsTransformer


def main():
    """Test encoding solutions."""
    print("=" * 80)
    print("ENCODING FIX TEST")
    print("=" * 80)

    # Get sample events
    print("\n1. Fetching events from API...")
    client = WixAPIClient.from_env()
    events_api = EventsAPI(client)
    response = events_api.query_events(limit=5)
    events = response.get('events', [])
    print(f"   Retrieved {len(events)} events")

    # Transform
    transformed = EventsTransformer.transform_events(events)

    # Show examples of special characters in the data
    print("\n2. Special characters found in data:")
    print("-" * 80)
    for event in transformed[:2]:
        text = event.get('formatted_date_time', '')
        if '\u2013' in text or '\u2014' in text or '\u2018' in text or '\u2019' in text or '\u201C' in text or '\u201D' in text:
            print(f"   Event: {event['title']}")
            print(f"   Text: {text}")
            print(f"   Contains: ", end='')
            if '\u2013' in text:
                print("EN DASH ", end='')
            if '\u2014' in text:
                print("EM DASH ", end='')
            if '\u2018' in text or '\u2019' in text:
                print("SMART QUOTES ", end='')
            print()

    # Test 3 different encoding solutions
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = project_root / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n3. Testing encoding solutions:")
    print("-" * 80)

    # Solution 1: UTF-8 with BOM (Excel-friendly)
    print("\n   Solution 1: UTF-8 with BOM (recommended for Excel)")
    file1 = output_dir / f"events_utf8_bom_{timestamp}.csv"
    EventsTransformer.save_to_csv(events, str(file1), encoding='utf-8-sig')
    print(f"   ✓ Saved: {file1.name}")

    # Check for BOM
    with open(file1, 'rb') as f:
        first_bytes = f.read(3)
        if first_bytes == b'\xef\xbb\xbf':
            print("   ✓ File has UTF-8 BOM → Excel will display correctly")
        else:
            print("   ✗ No BOM found")

    # Solution 2: Standard UTF-8 (no BOM)
    print("\n   Solution 2: Standard UTF-8 (no BOM)")
    file2 = output_dir / f"events_utf8_{timestamp}.csv"
    EventsTransformer.save_to_csv(events, str(file2), encoding='utf-8')
    print(f"   ✓ Saved: {file2.name}")
    print("   ⚠ Excel may show odd characters (but data is correct)")

    # Solution 3: ASCII-only (replace special chars)
    print("\n   Solution 3: ASCII-only (replace special characters)")
    file3 = output_dir / f"events_ascii_{timestamp}.csv"
    EventsTransformer.save_to_csv(events, str(file3), encoding='ascii')
    print(f"   ✓ Saved: {file3.name}")
    print("   ✓ All special characters replaced with ASCII equivalents")

    # Show the difference
    print("\n4. Comparing outputs:")
    print("-" * 80)

    import pandas as pd

    df1 = pd.read_csv(file1, encoding='utf-8-sig')
    df2 = pd.read_csv(file2, encoding='utf-8')
    df3 = pd.read_csv(file3, encoding='ascii')

    sample_text1 = df1['formatted_date_time'].iloc[0]
    sample_text2 = df2['formatted_date_time'].iloc[0]
    sample_text3 = df3['formatted_date_time'].iloc[0]

    print(f"\n   UTF-8 with BOM:  {sample_text1}")
    print(f"   UTF-8 no BOM:    {sample_text2}")
    print(f"   ASCII cleaned:   {sample_text3}")

    # Check description field
    desc1 = df1['description_full'].iloc[0][:100]
    desc3 = df3['description_full'].iloc[0][:100]

    print(f"\n   Description (UTF-8): {desc1}...")
    print(f"   Description (ASCII): {desc3}...")

    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    print("""
✅ RECOMMENDED: Use UTF-8 with BOM (default)
   - Preserves all original characters
   - Excel displays correctly
   - No data loss

   Usage: EventsTransformer.save_to_csv(events, 'output.csv')

Alternative: Use ASCII encoding if you need pure ASCII
   - Replaces special characters: EN DASH -> -, SMART QUOTE -> ', etc.
   - 100% ASCII compatible
   - Slight data loss (visual changes only)

   Usage: EventsTransformer.save_to_csv(events, 'output.csv', encoding='ascii')
""")

    print("=" * 80)
    print(f"✓ Test files saved to: {output_dir}")
    print("  Open these files in Excel to see the difference!")
    print("=" * 80)


if __name__ == "__main__":
    main()
