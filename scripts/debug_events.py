"""
Debug script to check the raw API response for events.
"""

import sys
import json
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    from wix_api.client import WixAPIClient
    from wix_api.events import EventsAPI

    print("\n" + "=" * 60)
    print("Debugging Events API Response")
    print("=" * 60)

    # Initialize client
    print("\n[1] Initializing client...")
    client = WixAPIClient.from_env()
    events_api = EventsAPI(client)

    # Test 1: Raw API call
    print("\n[2] Making raw API call to /events/v3/events/query...")
    try:
        raw_response = client.post(
            "/events/v3/events/query",
            json={
                "paging": {
                    "limit": 10,
                    "offset": 0
                }
            }
        )
        print("\nRaw API Response:")
        print(json.dumps(raw_response, indent=2))
    except Exception as e:
        print(f"\nERROR with raw API call: {e}")
        logger.error("Raw API call failed", exc_info=True)

    # Test 2: Using EventsAPI query_events
    print("\n[3] Using EventsAPI.query_events()...")
    try:
        response = events_api.query_events(limit=10, offset=0)
        print("\nEventsAPI Response:")
        print(json.dumps(response, indent=2))

        events = response.get("events", [])
        print(f"\nNumber of events in response: {len(events)}")

        paging = response.get("pagingMetadata", {})
        print(f"Paging metadata: {paging}")

    except Exception as e:
        print(f"\nERROR with EventsAPI: {e}")
        logger.error("EventsAPI call failed", exc_info=True)

    # Test 3: Check count by status
    print("\n[4] Checking event counts by status...")
    try:
        counts = events_api.count_events_by_status()
        print("\nEvent counts by status:")
        print(json.dumps(counts, indent=2))
    except Exception as e:
        print(f"\nERROR with count_by_status: {e}")
        logger.error("Count by status failed", exc_info=True)

    client.close()
    print("\n" + "=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
