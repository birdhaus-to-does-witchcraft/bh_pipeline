"""
Debug script to test different query parameters for events API.
"""

import sys
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    from wix_api.client import WixAPIClient

    print("\n" + "=" * 60)
    print("Testing Events API with Different Parameters")
    print("=" * 60)

    client = WixAPIClient.from_env()

    # Test 1: With fieldsets
    print("\n[Test 1] Query with fieldsets...")
    try:
        response = client.post(
            "/events/v3/events/query",
            json={
                "query": {
                    "paging": {
                        "limit": 5,
                        "offset": 0
                    },
                    "fieldsets": ["FULL"]
                }
            }
        )
        print(f"Response keys: {list(response.keys())}")
        print(f"Number of events: {len(response.get('events', []))}")
        print(f"Paging: {response.get('pagingMetadata', {})}")
        if response.get('events'):
            print(f"First event keys: {list(response['events'][0].keys())}")
    except Exception as e:
        print(f"ERROR: {e}")

    # Test 2: Different payload structure
    print("\n[Test 2] Query with 'query' wrapper...")
    try:
        response = client.post(
            "/events/v3/events/query",
            json={
                "query": {
                    "paging": {
                        "limit": 5
                    }
                }
            }
        )
        print(f"Response keys: {list(response.keys())}")
        print(f"Number of events: {len(response.get('events', []))}")
        print(f"Paging: {response.get('pagingMetadata', {})}")
    except Exception as e:
        print(f"ERROR: {e}")

    # Test 3: With cursorPaging
    print("\n[Test 3] Query with cursorPaging...")
    try:
        response = client.post(
            "/events/v3/events/query",
            json={
                "query": {
                    "cursorPaging": {
                        "limit": 5
                    }
                }
            }
        )
        print(f"Response keys: {list(response.keys())}")
        print(f"Number of events: {len(response.get('events', []))}")
        print(f"Paging: {response.get('pagingMetadata', {})}")
        if response.get('events'):
            print(f"First event ID: {response['events'][0].get('id')}")
    except Exception as e:
        print(f"ERROR: {e}")

    # Test 4: List all events (different endpoint)
    print("\n[Test 4] Try GET /events/v3/events...")
    try:
        response = client.get(
            "/events/v3/events",
            params={"limit": 5}
        )
        print(f"Response keys: {list(response.keys())}")
        print(f"Number of events: {len(response.get('events', []))}")
    except Exception as e:
        print(f"ERROR: {e}")

    # Test 5: Simple query
    print("\n[Test 5] Minimal query structure...")
    try:
        response = client.post(
            "/events/v3/events/query",
            json={
                "query": {}
            }
        )
        print(f"Response keys: {list(response.keys())}")
        print(f"Number of events: {len(response.get('events', []))}")
        print(f"Full response:")
        print(json.dumps(response, indent=2))
    except Exception as e:
        print(f"ERROR: {e}")

    client.close()
    print("\n" + "=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
