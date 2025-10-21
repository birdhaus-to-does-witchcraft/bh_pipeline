"""
Quick script to test different endpoint paths for Wix Events API.

This helps identify the correct endpoint structure.
"""

import logging
from wix_api.client import WixAPIClient
from utils.config import PipelineConfig

logging.basicConfig(level=logging.INFO)

def test_endpoint(client, endpoint, payload):
    """Test a single endpoint and report the result."""
    try:
        print(f"\nTesting: POST {endpoint}")
        response = client.post(endpoint, json=payload)
        print(f"  ✓ SUCCESS! Response keys: {list(response.keys())}")
        return True, response
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            print(f"  ✗ 404 Not Found")
        elif "400" in error_msg:
            print(f"  ✗ 400 Bad Request")
        elif "401" in error_msg:
            print(f"  ✗ 401 Unauthorized (check API key)")
        elif "403" in error_msg:
            print(f"  ✗ 403 Forbidden (check permissions)")
        else:
            print(f"  ✗ Error: {e}")
        return False, None


def main():
    print("=" * 60)
    print("Testing Wix API Endpoints")
    print("=" * 60)

    # Load config and create client
    config = PipelineConfig.from_env()
    client = WixAPIClient.from_config(config)

    # Test payload for events query
    query_payload = {
        "query": {
            "paging": {
                "limit": 1
            }
        }
    }

    # List of endpoint variations to test
    endpoints_to_test = [
        "/v3/events/query",
        "/events/v3/events/query",
        "/events/v3/query",
        "/v1/events/query",
        "/events/v1/query",
    ]

    print("\nTesting different endpoint paths...")
    print("(This will help us identify the correct endpoint structure)\n")

    for endpoint in endpoints_to_test:
        success, response = test_endpoint(client, endpoint, query_payload)
        if success:
            print(f"\n{'=' * 60}")
            print(f"FOUND WORKING ENDPOINT: {endpoint}")
            print(f"{'=' * 60}")
            print(f"\nSample response structure:")
            import json
            print(json.dumps(response, indent=2)[:500] + "...")
            client.close()
            return

    print("\n" + "=" * 60)
    print("None of the tested endpoints worked.")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Check the Wix API documentation for the correct endpoint")
    print("2. Verify API key has Events permissions")
    print("3. Check if the Wix Events app is installed on the site")

    client.close()


if __name__ == "__main__":
    main()
