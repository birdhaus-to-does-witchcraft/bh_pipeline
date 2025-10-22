"""
Unified pipeline testing script.

Consolidates functionality from:
- test_setup.py
- test_wix_client.py
- test_phase2.py

This script performs comprehensive testing of the entire data pipeline in stages.

Usage:
    # Test everything
    python scripts/test_pipeline.py --stage all

    # Test only setup (dependencies)
    python scripts/test_pipeline.py --stage setup

    # Test client configuration
    python scripts/test_pipeline.py --stage client

    # Test API wrappers
    python scripts/test_pipeline.py --stage wrappers

    # Test transformers
    python scripts/test_pipeline.py --stage transformers
"""

import sys
import argparse
import logging
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_section(title):
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(f"{title}")
    print("=" * 80)


def test_imports():
    """Test that all required dependencies can be imported."""
    print_section("STAGE 1: Testing Dependencies")

    dependencies = [
        ('requests', 'requests'),
        ('pyrate_limiter', 'pyrate_limiter'),
        ('tenacity', 'tenacity'),
        ('pandas', 'pandas'),
        ('numpy', 'numpy'),
        ('pydantic', 'pydantic'),
        ('python-dotenv', 'dotenv'),
        ('pyyaml', 'yaml'),
    ]

    all_passed = True
    for name, module in dependencies:
        try:
            __import__(module)
            print(f"  ✓ {name}")
        except ImportError as e:
            print(f"  ✗ {name}: {e}")
            all_passed = False

    return all_passed


def test_internal_modules():
    """Test that internal modules can be imported."""
    print("\nTesting Internal Modules...")

    modules = [
        ('utils.logger', 'setup_logging'),
        ('utils.config', 'load_config, PipelineConfig'),
        ('utils.retry', 'create_rate_limiter, create_retry_decorator'),
        ('wix_api.client', 'WixAPIClient'),
        ('wix_api.events', 'EventsAPI'),
        ('wix_api.guests', 'GuestsAPI'),
        ('wix_api.contacts', 'ContactsAPI'),
        ('wix_api.orders', 'OrdersAPI'),
        ('transformers.events', 'EventsTransformer'),
        ('transformers.guests', 'GuestsTransformer'),
        ('transformers.contacts', 'ContactsTransformer'),
        ('transformers.order_summaries', 'OrderSummariesTransformer'),
    ]

    all_passed = True
    for module, items in modules:
        try:
            __import__(module)
            print(f"  ✓ {module}")
        except ImportError as e:
            print(f"  ✗ {module}: {e}")
            all_passed = False

    return all_passed


def test_config_files():
    """Test that configuration files exist."""
    print("\nTesting Configuration Files...")

    config_dir = project_root / "config"
    files = [
        "credentials.env.template",
        "pipeline_config.yaml",
        "logging.yaml"
    ]

    all_exist = True
    for file in files:
        file_path = config_dir / file
        if file_path.exists():
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} (not found)")
            all_exist = False

    return all_exist


def test_config_loading():
    """Test loading configuration from .env file."""
    print_section("STAGE 2: Testing Configuration & Client")

    try:
        from utils.config import PipelineConfig

        # Load config from .env
        config = PipelineConfig.from_env()

        # Check required fields
        assert config.wix_api.api_key, "API key is missing"
        assert config.wix_api.account_id, "Account ID is missing"
        assert config.wix_api.site_id, "Site ID is missing"

        # Print masked values
        api_key_preview = config.wix_api.api_key[:20] + "..." if len(config.wix_api.api_key) > 20 else "***"

        print(f"\n  ✓ Configuration loaded successfully")
        print(f"  ✓ API Key: {api_key_preview}")
        print(f"  ✓ Account ID: {config.wix_api.account_id}")
        print(f"  ✓ Site ID: {config.wix_api.site_id}")
        print(f"  ✓ Base URL: {config.wix_api.base_url}")
        print(f"  ✓ Rate Limit: {config.rate_limit.max_calls} calls per {config.rate_limit.period}s")

        return True, config

    except Exception as e:
        print(f"\n  ✗ Configuration loading failed: {e}")
        logger.exception("Configuration error")
        return False, None


def test_client_instantiation(config):
    """Test instantiating WixAPIClient."""
    print("\nTesting WixAPIClient Instantiation...")

    try:
        from wix_api.client import WixAPIClient

        client = WixAPIClient.from_config(config)

        print(f"  ✓ Client created successfully")
        print(f"  ✓ Base URL: {client.base_url}")
        print(f"  ✓ Session configured with headers")
        print(f"  ✓ Rate limiter initialized")

        return True, client

    except Exception as e:
        print(f"  ✗ Client instantiation failed: {e}")
        logger.exception("Client error")
        return False, None


def test_api_connection(client):
    """Test making a real API call."""
    print("\nTesting API Connection...")

    try:
        response = client.post(
            "/events/v3/events/query",
            json={"query": {"paging": {"limit": 1}}}
        )

        print(f"  ✓ API call successful!")

        if "events" in response:
            event_count = len(response.get("events", []))
            total_count = response.get("pagingMetadata", {}).get("total", 0)
            print(f"  ✓ Response contains events data")
            print(f"  ✓ Events returned: {event_count}")
            print(f"  ✓ Total events available: {total_count}")

        return True

    except Exception as e:
        print(f"  ✗ API call failed: {e}")
        logger.exception("API connection error")

        # Provide helpful hints
        error_str = str(e).lower()
        if "401" in error_str or "authentication" in error_str:
            print("\n  Hint: Check that your API key is correct in .env file")
        elif "403" in error_str or "forbidden" in error_str:
            print("\n  Hint: Check that your account_id and site_id are correct")
        elif "404" in error_str:
            print("\n  Hint: The API endpoint may have changed")
        elif "429" in error_str or "rate limit" in error_str:
            print("\n  Hint: Rate limit exceeded, wait and try again")

        return False


def test_api_wrappers(client):
    """Test all API wrapper classes."""
    print_section("STAGE 3: Testing API Wrappers")

    from wix_api.events import EventsAPI
    from wix_api.guests import GuestsAPI
    from wix_api.contacts import ContactsAPI
    from wix_api.orders import OrdersAPI

    results = []

    # Test Events API
    print("\nTesting EventsAPI...")
    try:
        events_api = EventsAPI(client)
        response = events_api.query_events(limit=5)
        events = response.get("events", [])
        print(f"  ✓ EventsAPI working - retrieved {len(events)} events")
        results.append(True)
    except Exception as e:
        print(f"  ✗ EventsAPI failed: {e}")
        results.append(False)

    # Test Guests API
    print("\nTesting GuestsAPI...")
    try:
        guests_api = GuestsAPI(client)
        response = guests_api.query_guests(limit=5)
        guests = response.get("guests", [])
        print(f"  ✓ GuestsAPI working - retrieved {len(guests)} guests")
        results.append(True)
    except Exception as e:
        print(f"  ✗ GuestsAPI failed: {e}")
        results.append(False)

    # Test Contacts API
    print("\nTesting ContactsAPI...")
    try:
        contacts_api = ContactsAPI(client)
        response = contacts_api.list_contacts(limit=5)
        contacts = response.get("contacts", [])
        print(f"  ✓ ContactsAPI working - retrieved {len(contacts)} contacts")
        results.append(True)
    except Exception as e:
        print(f"  ✗ ContactsAPI failed: {e}")
        results.append(False)

    # Test Orders API
    print("\nTesting OrdersAPI...")
    try:
        orders_api = OrdersAPI(client)
        summary = orders_api.get_summary()
        print(f"  ✓ OrdersAPI working - retrieved sales summary")
        results.append(True)
    except Exception as e:
        print(f"  ✗ OrdersAPI failed: {e}")
        results.append(False)

    return all(results)


def test_transformers():
    """Test all transformer classes."""
    print_section("STAGE 4: Testing Transformers")

    from transformers.events import EventsTransformer
    from transformers.guests import GuestsTransformer
    from transformers.contacts import ContactsTransformer
    from transformers.order_summaries import OrderSummariesTransformer

    results = []

    # Test Events Transformer
    print("\nTesting EventsTransformer...")
    try:
        sample_event = {
            'id': 'test-id',
            'title': 'Test Event',
            'status': 'SCHEDULED',
            'categories': {'categories': [{'name': 'Test'}]}
        }
        transformed = EventsTransformer.transform_event(sample_event)
        assert 'event_id' in transformed
        assert 'title' in transformed
        print(f"  ✓ EventsTransformer working - {len(transformed)} fields output")
        results.append(True)
    except Exception as e:
        print(f"  ✗ EventsTransformer failed: {e}")
        results.append(False)

    # Test Guests Transformer
    print("\nTesting GuestsTransformer...")
    try:
        sample_guest = {
            'id': 'test-id',
            'eventId': 'event-id',
            'contactId': 'contact-id'
        }
        transformed = GuestsTransformer.transform_guest(sample_guest)
        assert 'guest_id' in transformed
        print(f"  ✓ GuestsTransformer working - {len(transformed)} fields output")
        results.append(True)
    except Exception as e:
        print(f"  ✗ GuestsTransformer failed: {e}")
        results.append(False)

    # Test Contacts Transformer
    print("\nTesting ContactsTransformer...")
    try:
        sample_contact = {
            'id': 'test-id',
            'info': {'name': {'first': 'Test', 'last': 'User'}}
        }
        transformed = ContactsTransformer.transform_contact(sample_contact)
        assert 'contact_id' in transformed
        print(f"  ✓ ContactsTransformer working - {len(transformed)} fields output")
        results.append(True)
    except Exception as e:
        print(f"  ✗ ContactsTransformer failed: {e}")
        results.append(False)

    # Test Order Summaries Transformer
    print("\nTesting OrderSummariesTransformer...")
    try:
        sample_summary = {'sales': []}
        transformed = OrderSummariesTransformer.transform_summary(
            'event-id', 'Test Event', sample_summary
        )
        assert 'event_id' in transformed
        print(f"  ✓ OrderSummariesTransformer working - {len(transformed)} fields output")
        results.append(True)
    except Exception as e:
        print(f"  ✗ OrderSummariesTransformer failed: {e}")
        results.append(False)

    return all(results)


def main():
    """Run pipeline tests."""
    parser = argparse.ArgumentParser(description='Test Birdhaus Data Pipeline')
    parser.add_argument(
        '--stage',
        choices=['setup', 'client', 'wrappers', 'transformers', 'all'],
        default='all',
        help='Testing stage to run (default: all)'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("BIRDHAUS DATA PIPELINE - TESTING")
    print("=" * 80)

    results = {}
    client = None

    try:
        # Stage 1: Setup
        if args.stage in ['setup', 'all']:
            deps_ok = test_imports()
            modules_ok = test_internal_modules()
            files_ok = test_config_files()
            results['setup'] = deps_ok and modules_ok and files_ok

            if not results['setup'] and args.stage == 'all':
                print("\n✗ Setup tests failed. Cannot proceed.")
                return 1

        # Stage 2: Client
        if args.stage in ['client', 'all']:
            config_ok, config = test_config_loading()
            if not config_ok:
                results['client'] = False
                if args.stage == 'all':
                    print("\n✗ Client configuration failed. Cannot proceed.")
                    return 1
            else:
                client_ok, client = test_client_instantiation(config)
                if not client_ok:
                    results['client'] = False
                    if args.stage == 'all':
                        print("\n✗ Client instantiation failed. Cannot proceed.")
                        return 1
                else:
                    api_ok = test_api_connection(client)
                    results['client'] = api_ok

        # Stage 3: Wrappers
        if args.stage in ['wrappers', 'all']:
            if client is None:
                from wix_api.client import WixAPIClient
                client = WixAPIClient.from_env()

            results['wrappers'] = test_api_wrappers(client)

        # Stage 4: Transformers
        if args.stage in ['transformers', 'all']:
            results['transformers'] = test_transformers()

    finally:
        if client:
            client.close()

    # Summary
    print_section("TEST SUMMARY")

    for stage, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        symbol = "✓" if passed else "✗"
        print(f"{symbol} {stage.capitalize()}: {status}")

    all_passed = all(results.values())

    if all_passed:
        print("\n✓ All tests passed! Pipeline is ready to use.")
        return 0
    else:
        print("\n✗ Some tests failed. Please check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
