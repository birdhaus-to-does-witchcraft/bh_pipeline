"""
Generate enriched CSV views by joining contacts, events, and guests data.

This script reads the latest processed CSVs and creates joined "views" for 
pivot table analysis and exploration. It does NOT make any API calls.

Views generated:
- guests_enriched.csv: Guests with full contact and event details
- contact_event_history.csv: Each contact's complete event attendance
- event_attendance.csv: Events with attendance counts and attendee details

Usage:
    python scripts/generate_views.py
    # Or with custom input/output directories:
    python scripts/generate_views.py --input-dir data/processed --output-dir data/views
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd
import glob

# Project root for default paths
PROJECT_ROOT = Path(__file__).parent.parent


def find_latest_csv(directory: Path, prefix: str) -> Path | None:
    """Find the most recently modified CSV file with the given prefix."""
    pattern = str(directory / f"{prefix}_*.csv")
    files = glob.glob(pattern)
    if not files:
        return None
    # Sort by modification time, newest first
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


def create_guests_enriched(
    guests: pd.DataFrame, 
    contacts: pd.DataFrame, 
    events: pd.DataFrame
) -> pd.DataFrame:
    """
    Create enriched guests view with contact and event details.
    
    Each row is a guest record with their contact info and the event they attended.
    """
    # Select relevant columns from contacts
    contact_cols = [
        'contact_id', 'primary_email', 'first_name', 'last_name', 'full_name',
        'is_member', 'member_status', 'source_type', 'created_date'
    ]
    # Only include columns that exist
    contact_cols = [c for c in contact_cols if c in contacts.columns]
    contacts_subset = contacts[contact_cols].copy()
    contacts_subset = contacts_subset.add_prefix('contact_')
    contacts_subset = contacts_subset.rename(columns={'contact_contact_id': 'contact_id'})
    
    # Select relevant columns from events
    event_cols = [
        'event_id', 'title', 'status', 'short_description', 'category_names',
        'primary_category', 'start_date', 'start_time', 'start_datetime',
        'end_date', 'end_time', 'location_name', 'location_city',
        'lowest_price', 'highest_price', 'currency'
    ]
    event_cols = [c for c in event_cols if c in events.columns]
    events_subset = events[event_cols].copy()
    events_subset = events_subset.add_prefix('event_')
    events_subset = events_subset.rename(columns={'event_event_id': 'event_id'})
    
    # Join guests with contacts
    enriched = guests.merge(
        contacts_subset,
        on='contact_id',
        how='left'
    )
    
    # Join with events
    enriched = enriched.merge(
        events_subset,
        on='event_id',
        how='left'
    )
    
    # Reorder columns for better usability
    # Guest info first, then contact, then event
    guest_cols = [c for c in guests.columns if c in enriched.columns]
    contact_cols_final = [c for c in enriched.columns if c.startswith('contact_')]
    event_cols_final = [c for c in enriched.columns if c.startswith('event_')]
    
    ordered_cols = guest_cols + contact_cols_final + event_cols_final
    # Add any remaining columns
    remaining = [c for c in enriched.columns if c not in ordered_cols]
    ordered_cols.extend(remaining)
    
    return enriched[ordered_cols]


def create_contact_event_history(
    guests: pd.DataFrame,
    contacts: pd.DataFrame,
    events: pd.DataFrame
) -> pd.DataFrame:
    """
    Create a contact-centric view showing each contact's event history.
    
    Each row is a contact with aggregated info about their event attendance.
    """
    # Get event titles mapped to event_id
    event_titles = events.set_index('event_id')['title'].to_dict()
    event_dates = events.set_index('event_id')['start_date'].to_dict()
    event_categories = events.set_index('event_id')['primary_category'].to_dict()
    
    # Group guests by contact
    contact_events = guests.groupby('contact_id').agg({
        'event_id': list,
        'guest_id': 'count',
        'guest_type': lambda x: list(x.unique()),
        'created_date': 'min',  # First attendance
    }).reset_index()
    
    contact_events.columns = [
        'contact_id', 'event_ids', 'total_attendances', 
        'guest_types', 'first_attendance_date'
    ]
    
    # Add event count and event titles
    contact_events['unique_events_count'] = contact_events['event_ids'].apply(
        lambda x: len(set(x))
    )
    contact_events['event_titles'] = contact_events['event_ids'].apply(
        lambda ids: '; '.join(set(event_titles.get(eid, 'Unknown') for eid in ids))
    )
    contact_events['event_categories'] = contact_events['event_ids'].apply(
        lambda ids: '; '.join(set(str(event_categories.get(eid, '')) for eid in ids if event_categories.get(eid)))
    )
    
    # Join with contact info
    contact_cols = [
        'contact_id', 'primary_email', 'first_name', 'last_name', 'full_name',
        'is_member', 'member_status', 'source_type', 'created_date'
    ]
    contact_cols = [c for c in contact_cols if c in contacts.columns]
    contacts_subset = contacts[contact_cols].copy()
    
    result = contacts_subset.merge(
        contact_events,
        on='contact_id',
        how='left'
    )
    
    # Fill NaN for contacts with no events
    result['total_attendances'] = result['total_attendances'].fillna(0).astype(int)
    result['unique_events_count'] = result['unique_events_count'].fillna(0).astype(int)
    
    # Sort by most active attendees first
    result = result.sort_values('total_attendances', ascending=False)
    
    # Drop the event_ids list column (not useful in CSV)
    result = result.drop(columns=['event_ids'], errors='ignore')
    
    return result


def create_event_attendance(
    guests: pd.DataFrame,
    contacts: pd.DataFrame,
    events: pd.DataFrame
) -> pd.DataFrame:
    """
    Create an event-centric view showing attendance stats per event.
    
    Each row is an event with aggregated attendance information.
    """
    # Get contact names mapped to contact_id
    contact_names = contacts.set_index('contact_id')['full_name'].to_dict()
    contact_emails = contacts.set_index('contact_id')['primary_email'].to_dict()
    
    # Group guests by event
    event_guests = guests.groupby('event_id').agg({
        'contact_id': list,
        'guest_id': 'count',
        'guest_type': lambda x: dict(x.value_counts()),
        'attendance_status': lambda x: dict(x.value_counts()) if x.notna().any() else {},
    }).reset_index()
    
    event_guests.columns = [
        'event_id', 'contact_ids', 'total_guests',
        'guest_type_breakdown', 'attendance_status_breakdown'
    ]
    
    # Calculate unique contacts and attendee names
    event_guests['unique_contacts'] = event_guests['contact_ids'].apply(
        lambda x: len(set(x))
    )
    event_guests['buyer_count'] = event_guests['guest_type_breakdown'].apply(
        lambda x: x.get('BUYER', 0)
    )
    event_guests['ticket_holder_count'] = event_guests['guest_type_breakdown'].apply(
        lambda x: x.get('TICKET_HOLDER', 0)
    )
    event_guests['attendee_names'] = event_guests['contact_ids'].apply(
        lambda ids: '; '.join(
            list(set(
                contact_names.get(cid, 'Unknown') 
                for cid in ids 
                if contact_names.get(cid)
            ))[:20]  # Limit to first 20 unique names
        )
    )
    
    # Join with event info
    event_cols = [
        'event_id', 'title', 'status', 'short_description', 'category_names',
        'primary_category', 'start_date', 'start_time', 'start_datetime',
        'end_date', 'location_name', 'location_city',
        'lowest_price', 'highest_price', 'currency', 'sold_out'
    ]
    event_cols = [c for c in event_cols if c in events.columns]
    events_subset = events[event_cols].copy()
    
    result = events_subset.merge(
        event_guests,
        on='event_id',
        how='left'
    )
    
    # Fill NaN for events with no guests
    result['total_guests'] = result['total_guests'].fillna(0).astype(int)
    result['unique_contacts'] = result['unique_contacts'].fillna(0).astype(int)
    result['buyer_count'] = result['buyer_count'].fillna(0).astype(int)
    result['ticket_holder_count'] = result['ticket_holder_count'].fillna(0).astype(int)
    
    # Sort by start date
    result = result.sort_values('start_date', ascending=False)
    
    # Drop columns not useful in CSV
    result = result.drop(
        columns=['contact_ids', 'guest_type_breakdown', 'attendance_status_breakdown'],
        errors='ignore'
    )
    
    return result


def save_view(df: pd.DataFrame, output_path: Path, name: str) -> None:
    """Save a DataFrame to CSV with UTF-8 BOM encoding for Excel compatibility."""
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save with UTF-8 BOM for Excel
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"  ✓ {name}: {len(df):,} rows → {output_path.name}")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate enriched CSV views from Wix data"
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
    """Generate all enriched views."""
    args = parse_args()
    
    # Set up directories
    input_dir = Path(args.input_dir) if args.input_dir else PROJECT_ROOT / "data" / "processed"
    output_dir = Path(args.output_dir) if args.output_dir else PROJECT_ROOT / "data" / "views"
    
    print("=" * 60)
    print("GENERATING ENRICHED DATA VIEWS")
    print("=" * 60)
    print(f"\nInput:  {input_dir}")
    print(f"Output: {output_dir}\n")
    
    try:
        # Load data
        contacts, events, guests = load_data(input_dir)
        
        # Generate timestamp for output files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print("\nGenerating views...")
        
        # 1. Guests Enriched View
        guests_enriched = create_guests_enriched(guests, contacts, events)
        save_view(
            guests_enriched,
            output_dir / f"guests_enriched_{timestamp}.csv",
            "Guests Enriched"
        )
        
        # 2. Contact Event History View
        contact_history = create_contact_event_history(guests, contacts, events)
        save_view(
            contact_history,
            output_dir / f"contact_event_history_{timestamp}.csv",
            "Contact Event History"
        )
        
        # 3. Event Attendance View
        event_attendance = create_event_attendance(guests, contacts, events)
        save_view(
            event_attendance,
            output_dir / f"event_attendance_{timestamp}.csv",
            "Event Attendance"
        )
        
        print("\n" + "=" * 60)
        print("VIEWS GENERATED SUCCESSFULLY")
        print("=" * 60)
        print(f"\nAll views saved to: {output_dir}")
        print("\nViews created:")
        print("  • guests_enriched - Each guest with contact + event details")
        print("  • contact_event_history - Contacts with their event attendance")
        print("  • event_attendance - Events with attendance counts")
        
        return 0
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you've run 'python scripts/pull_all.py' first.")
        return 1
    except Exception as e:
        print(f"\n❌ Error generating views: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

