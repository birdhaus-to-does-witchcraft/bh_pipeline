"""
Test querying guests for a specific event.
"""

import sys
import json
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from wix_api.client import WixAPIClient

def main():
    """Test guests query for specific event."""
    client = WixAPIClient.from_env()

    # Get a specific event
    events_response = client.post('/events/v3/events/query', json={'query': {'paging': {'limit': 1}}})
    event = events_response['events'][0]
    event_id = event['id']

    print(f'Event: {event["title"]}')
    print(f'Event ID: {event_id}')
    print(f'Status: {event["status"]}')
    print()

    # Try to get guests for this specific event
    print('Querying guests for this event...')
    response = client.post('/events-guests/v2/guests/query', json={
        'query': {
            'filter': {'eventId': {'$eq': event_id}},
            'fieldsets': ['GUEST_DETAILS'],
            'paging': {'limit': 10}
        }
    })

    guests = response.get('guests', [])
    paging = response.get('pagingMetadata', {})

    print(f'Guests found: {len(guests)}')
    print(f'Total (from paging): {paging.get("total", "unknown")}')
    print(f'\nFull response:')
    print(json.dumps(response, indent=2))

    if guests:
        print(f'\nFirst guest:')
        print(json.dumps(guests[0], indent=2))


if __name__ == "__main__":
    main()
