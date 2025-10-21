"""Test pagination to see why it stops at 100 events."""

import sys
from wix_api.client import WixAPIClient
from wix_api.events import EventsAPI

client = WixAPIClient.from_env()
events_api = EventsAPI(client)

print("Testing pagination...")
print("\nPage 1 (offset=0, limit=100):")
response = events_api.query_events(limit=100, offset=0)
print(f"  Count: {response['pagingMetadata']['count']}")
print(f"  Total: {response['pagingMetadata']['total']}")
print(f"  Offset: {response['pagingMetadata']['offset']}")
print(f"  Has Next: {response['pagingMetadata'].get('hasNext', 'N/A')}")
print(f"  Actual events returned: {len(response['events'])}")

print("\nPage 2 (offset=100, limit=100):")
response = events_api.query_events(limit=100, offset=100)
print(f"  Count: {response['pagingMetadata']['count']}")
print(f"  Total: {response['pagingMetadata']['total']}")
print(f"  Offset: {response['pagingMetadata']['offset']}")
print(f"  Has Next: {response['pagingMetadata'].get('hasNext', 'N/A')}")
print(f"  Actual events returned: {len(response['events'])}")

client.close()
