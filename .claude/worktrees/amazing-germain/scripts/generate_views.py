"""
Generate a unified ticket sales view from Wix data.

Creates a single CSV that joins guests + contacts + events, similar to an 
Eventbrite export. Each row represents one ticket/guest with enriched 
contact info (name, email) and event info (title, date, estimated price).

This makes the Wix data comparable to the Eventbrite export format.

Usage:
    python scripts/generate_views.py
    # Or with custom directories:
    python scripts/generate_views.py --input-dir data/processed --output-dir data/views
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd
import glob

PROJECT_ROOT = Path(__file__).parent.parent


def find_latest_csv(directory: Path, prefix: str) -> Path | None:
    """Find the most recently modified CSV file with the given prefix."""
    pattern = str(directory / f"{prefix}_*.csv")
    files = glob.glob(pattern)
    if not files:
        return None
    return Path(sorted(files, key=lambda x: Path(x).stat().st_mtime, reverse=True)[0])


def load_data(input_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load the latest contacts, events, and guests CSVs."""
    contacts_path = find_latest_csv(input_dir, "contacts")
    events_path = find_latest_csv(input_dir, "events")
    guests_path = find_latest_csv(input_dir, "guests")
    
    missing = []
    if not contacts_path:
        missing.append("contacts")
    if not events_path:
        missing.append("events")
    if not guests_path:
        missing.append("guests")
    
    if missing:
        raise FileNotFoundError(
            f"Could not find CSV files for: {', '.join(missing)} in {input_dir}"
        )
    
    print(f"Loading data from:")
    print(f"  Contacts: {contacts_path.name}")
    print(f"  Events:   {events_path.name}")
    print(f"  Guests:   {guests_path.name}")
    
    contacts = pd.read_csv(contacts_path)
    events = pd.read_csv(events_path)
    guests = pd.read_csv(guests_path)
    
    print(f"\nData loaded:")
    print(f"  {len(contacts):,} contacts")
    print(f"  {len(events):,} events")
    print(f"  {len(guests):,} guests")
    
    return contacts, events, guests


def create_ticket_sales_view(
    guests: pd.DataFrame, 
    contacts: pd.DataFrame, 
    events: pd.DataFrame
) -> pd.DataFrame:
    """
    Create a ticket-sales view comparable to Eventbrite export format.
    
    Each row is a guest/ticket with:
    - Order info (order_number, ticket_number, order_date)
    - Buyer info (first_name, last_name, email) from contacts
    - Event info (title, date, time, location) from events
    - Pricing info (estimated ticket price) from events
    """
    
    # --- Prepare contacts data ---
    contact_cols = ['contact_id', 'first_name', 'last_name', 'full_name', 'primary_email']
    contacts_subset = contacts[[c for c in contact_cols if c in contacts.columns]].copy()
    
    # --- Prepare events data ---
    event_cols = [
        'event_id', 'title', 'start_date', 'start_time', 'end_date', 'end_time',
        'timezone', 'location_name', 'location_address', 'location_city',
        'currency', 'lowest_price', 'highest_price', 'primary_category', 'status'
    ]
    events_subset = events[[c for c in event_cols if c in events.columns]].copy()
    
    # Calculate average ticket price as estimate (midpoint of lowest/highest)
    if 'lowest_price' in events_subset.columns and 'highest_price' in events_subset.columns:
        events_subset['estimated_ticket_price'] = (
            (events_subset['lowest_price'].fillna(0) + events_subset['highest_price'].fillna(0)) / 2
        ).round(2)
    
    # --- Join guests with contacts ---
    result = guests.merge(
        contacts_subset,
        on='contact_id',
        how='left',
        suffixes=('', '_contact')
    )
    
    # --- Join with events ---
    result = result.merge(
        events_subset,
        on='event_id',
        how='left',
        suffixes=('', '_event')
    )
    
    # --- Select and rename columns to match Eventbrite-like format ---
    # Use contact name/email if guest name/email is empty
    result['buyer_first_name'] = result['first_name_contact'].fillna(result.get('first_name', ''))
    result['buyer_last_name'] = result['last_name_contact'].fillna(result.get('last_name', ''))
    result['buyer_email'] = result['primary_email'].fillna(result.get('email', ''))
    
    # Build the final output with comparable columns
    output_cols = {
        # Order/Ticket info
        'order_number': 'order_number',
        'ticket_number': 'ticket_number', 
        'guest_id': 'guest_id',
        'guest_type': 'guest_type',
        'created_date': 'order_date',
        'created_time': 'order_time',
        
        # Buyer info (from contacts)
        'buyer_first_name': 'buyer_first_name',
        'buyer_last_name': 'buyer_last_name',
        'buyer_email': 'buyer_email',
        
        # Event info
        'title': 'event_name',
        'event_id': 'event_id',
        'start_date': 'event_start_date',
        'start_time': 'event_start_time',
        'end_date': 'event_end_date',
        'end_time': 'event_end_time',
        'timezone': 'event_timezone',
        'location_name': 'event_location',
        'location_city': 'event_city',
        'primary_category': 'event_category',
        'status': 'event_status',
        
        # Pricing
        'currency': 'currency',
        'lowest_price': 'ticket_price_low',
        'highest_price': 'ticket_price_high',
        'estimated_ticket_price': 'estimated_ticket_price',
        
        # Attendance
        'attendance_status': 'attendance_status',
        'checked_in': 'checked_in',
        
        # Reference IDs for joins
        'contact_id': 'contact_id',
    }
    
    # Select columns that exist and rename
    final_cols = {}
    for old_col, new_col in output_cols.items():
        if old_col in result.columns:
            final_cols[old_col] = new_col
    
    output = result[list(final_cols.keys())].rename(columns=final_cols)
    
    # Sort by order date (most recent first), then by event
    if 'order_date' in output.columns:
        output = output.sort_values(['order_date', 'event_name'], ascending=[False, True])
    
    return output


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate unified ticket sales view from Wix data"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default=None,
        help="Input directory with processed CSVs (default: data/processed)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for view CSVs (default: data/views)"
    )
    return parser.parse_args()


def main():
    """Generate the ticket sales view."""
    args = parse_args()
    
    input_dir = Path(args.input_dir) if args.input_dir else PROJECT_ROOT / "data" / "processed"
    output_dir = Path(args.output_dir) if args.output_dir else PROJECT_ROOT / "data" / "views"
    
    print("=" * 60)
    print("GENERATING TICKET SALES VIEW")
    print("=" * 60)
    print(f"\nInput:  {input_dir}")
    print(f"Output: {output_dir}\n")
    
    try:
        # Load data
        contacts, events, guests = load_data(input_dir)
        
        # Create the unified view
        print("\nCreating ticket sales view...")
        ticket_sales = create_ticket_sales_view(guests, contacts, events)
        
        # Save output
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"ticket_sales_{timestamp}.csv"
        
        # Save with UTF-8 BOM for Excel compatibility
        ticket_sales.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        print(f"\n✓ Saved {len(ticket_sales):,} rows to {output_path.name}")
        
        # Show sample of columns
        print(f"\nColumns in output ({len(ticket_sales.columns)}):")
        for col in ticket_sales.columns:
            print(f"  • {col}")
        
        print("\n" + "=" * 60)
        print("VIEW GENERATED SUCCESSFULLY")
        print("=" * 60)
        print(f"\nOutput: {output_path}")
        print("\nThis view can be compared with Eventbrite exports like:")
        print("  data/other/invite_only_cleaned.csv")
        
        return 0
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you've run 'python scripts/pull_all.py' first.")
        return 1
    except Exception as e:
        print(f"\n❌ Error generating view: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
