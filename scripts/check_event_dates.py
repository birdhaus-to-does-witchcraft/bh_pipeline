"""Quick script to check event date range and statuses."""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wix_api.client import WixAPIClient
from wix_api.events import EventsAPI

client = WixAPIClient.from_env()
events_api = EventsAPI(client)

# Get all events
print("Fetching all events...")
all_events = events_api.get_all_events()
print(f"Total events: {len(all_events)}")

# Analyze dates and statuses
dates = []
statuses = {}
reg_types = {}

for e in all_events:
    # Try different date field locations
    start = (
        e.get('dateAndTimeSettings', {}).get('startDate') or
        e.get('scheduling', {}).get('config', {}).get('startDate')
    )
    status = e.get('status', 'UNKNOWN')
    reg_type = e.get('registration', {}).get('type', 'UNKNOWN')
    
    statuses[status] = statuses.get(status, 0) + 1
    reg_types[reg_type] = reg_types.get(reg_type, 0) + 1
    
    if start:
        dates.append(start)

dates.sort()

print(f"\nEvent statuses: {statuses}")
print(f"Registration types: {reg_types}")
print(f"\nDate range:")
print(f"  Earliest event: {dates[0] if dates else 'N/A'}")
print(f"  Latest event: {dates[-1] if dates else 'N/A'}")

# Count events before/after today
today = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
past_count = sum(1 for d in dates if d < today)
future_count = sum(1 for d in dates if d >= today)

print(f"\nPast events (before today): {past_count}")
print(f"Future events (today onwards): {future_count}")

print(f"\nFirst 5 dates (earliest): {dates[:5]}")
print(f"Last 5 dates (latest): {dates[-5:]}")

client.close()

