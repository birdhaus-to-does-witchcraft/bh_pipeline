"""
Test script to verify WixAPIClient configuration and basic functionality.

This script:
1. Loads configuration from .env file
2. Instantiates WixAPIClient
3. Makes a test API call to verify credentials

Usage:
    python scripts/test_wix_client.py
"""

import sys
from pathlib import Path

# Enable detailed logging for testing
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def test_config_loading():
    """Test loading configuration from .env file."""
    print("\n" + "=" * 60)
    print("Test 1: Configuration Loading")
    print("=" * 60)

    try:
        from utils.config import PipelineConfig

        # Load config from .env
        config = PipelineConfig.from_env()

        # Check that required fields are present
        assert config.wix_api.api_key, "API key is missing"
        assert config.wix_api.account_id, "Account ID is missing"
        assert config.wix_api.site_id, "Site ID is missing"

        # Print masked values for verification
        api_key_preview = config.wix_api.api_key[:20] + "..." if len(config.wix_api.api_key) > 20 else "***"

        print(f"  ✓ Configuration loaded successfully")
        print(f"  ✓ API Key: {api_key_preview}")
        print(f"  ✓ Account ID: {config.wix_api.account_id}")
        print(f"  ✓ Site ID: {config.wix_api.site_id}")
        print(f"  ✓ Base URL: {config.wix_api.base_url}")
        print(f"  ✓ Rate Limit: {config.rate_limit.max_calls} calls per {config.rate_limit.period}s")

        return True, config

    except Exception as e:
        print(f"  ✗ Configuration loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_client_instantiation(config):
    """Test instantiating WixAPIClient."""
    print("\n" + "=" * 60)
    print("Test 2: WixAPIClient Instantiation")
    print("=" * 60)

    try:
        from wix_api.client import WixAPIClient

        # Create client from config
        client = WixAPIClient.from_config(config)

        print(f"  ✓ Client created successfully")
        print(f"  ✓ Base URL: {client.base_url}")
        print(f"  ✓ Session configured with headers")
        print(f"  ✓ Rate limiter initialized")

        return True, client

    except Exception as e:
        print(f"  ✗ Client instantiation failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_api_connection(client):
    """Test making a real API call to verify credentials."""
    print("\n" + "=" * 60)
    print("Test 3: API Connection Test")
    print("=" * 60)

    try:
        # Try to query events (limit to 1 to minimize API usage)
        # Using Events V3 API (V1 deprecated November 2024)
        print("  Making test API call to /events/v3/events/query...")

        response = client.post(
            "/events/v3/events/query",
            json={
                "paging": {
                    "limit": 1,
                    "offset": 0
                }
            }
        )

        print(f"  ✓ API call successful!")

        # Check if we got events data
        if "events" in response:
            event_count = len(response.get("events", []))
            total_count = response.get("pagingMetadata", {}).get("total", 0)
            print(f"  ✓ Response contains events data")
            print(f"  ✓ Events returned in this call: {event_count}")
            print(f"  ✓ Total events available: {total_count}")
        else:
            print(f"  ℹ Response structure: {list(response.keys())}")

        return True

    except Exception as e:
        print(f"  ✗ API call failed: {e}")
        import traceback
        traceback.print_exc()

        # Provide helpful error messages
        error_str = str(e).lower()
        if "401" in error_str or "authentication" in error_str:
            print("\n  Hint: Check that your API key is correct in .env file")
        elif "403" in error_str or "forbidden" in error_str:
            print("\n  Hint: Check that your account_id and site_id are correct")
        elif "404" in error_str:
            print("\n  Hint: The API endpoint may have changed or be incorrect")
        elif "429" in error_str or "rate limit" in error_str:
            print("\n  Hint: Rate limit exceeded, wait a moment and try again")

        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Birdhaus Data Pipeline - Phase 1 Testing")
    print("Wix API Client Verification")
    print("=" * 60)

    # Test 1: Configuration loading
    success, config = test_config_loading()
    if not success:
        print("\n✗ Configuration test failed. Cannot proceed.")
        return 1

    # Test 2: Client instantiation
    success, client = test_client_instantiation(config)
    if not success:
        print("\n✗ Client instantiation test failed. Cannot proceed.")
        return 1

    # Test 3: API connection
    success = test_api_connection(client)

    # Clean up
    client.close()

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    if success:
        print("\n✓ All tests passed! Phase 1 is complete.")
        print("\nThe Wix API client is working correctly and can:")
        print("  - Load configuration from .env file")
        print("  - Create authenticated API client")
        print("  - Make successful API calls to Wix")
        print("\n" + "=" * 60)
        print("Ready for Phase 2: Endpoint Wrappers")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Implement Events API wrapper (wix_api/events.py)")
        print("2. Implement Guests API wrapper (wix_api/guests.py)")
        print("3. Implement Tickets API wrapper (wix_api/tickets.py)")
        print("4. Implement Contacts API wrapper (wix_api/contacts.py)")
        print("5. Implement Transactions API wrapper (wix_api/transactions.py)")
        return 0
    else:
        print("\n✗ API connection test failed.")
        print("\nPlease check:")
        print("1. Your .env file has correct credentials")
        print("2. The Wix API key has proper permissions")
        print("3. The account_id and site_id are correct")
        print("4. Your internet connection is working")
        return 1


if __name__ == "__main__":
    sys.exit(main())
