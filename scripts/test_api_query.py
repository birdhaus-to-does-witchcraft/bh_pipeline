"""
Wix API Query Tester - Test different query parameters and filter syntaxes.

This tool helps validate API query syntax before using in production code.
Useful for debugging filter issues, date ranges, and pagination.

Usage:
    # Test events with no filter (see what's returned by default)
    python scripts/test_api_query.py --endpoint events

    # Test a specific filter
    python scripts/test_api_query.py --endpoint events --filter '{"status": ["PUBLISHED"]}'

    # Test date range for historical events
    python scripts/test_api_query.py --endpoint events --from-date 2020-01-01 --to-date 2025-12-31

    # Test raw payload (full control)
    python scripts/test_api_query.py --endpoint events --raw-payload '{"query": {"paging": {"limit": 5}}}'

    # Show full response (not truncated)
    python scripts/test_api_query.py --endpoint events --full

    # Test different filter syntaxes for events
    python scripts/test_api_query.py --endpoint events --test-filters
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from wix_api.client import WixAPIClient


def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_response(response, full=False):
    """Print API response."""
    response_str = json.dumps(response, indent=2, default=str)
    if full or len(response_str) < 2000:
        print(response_str)
    else:
        print(response_str[:2000] + "\n... (truncated, use --full to see all)")


def test_events_query(client, payload, label="Query"):
    """Test an events query and show results."""
    print(f"\n[{label}]")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("-" * 40)
    
    try:
        response = client.post("/events/v3/events/query", json=payload)
        events = response.get("events", [])
        paging = response.get("pagingMetadata", {})
        
        print(f"✓ Success!")
        print(f"  Events returned: {len(events)}")
        print(f"  Total: {paging.get('total', 'N/A')}")
        print(f"  Offset: {paging.get('offset', 'N/A')}")
        print(f"  Has Next: {paging.get('hasNext', 'N/A')}")
        
        if events:
            # Show date range of returned events
            dates = []
            for e in events:
                start = e.get('scheduling', {}).get('config', {}).get('startDate')
                if start:
                    dates.append(start)
            
            if dates:
                dates.sort()
                print(f"\n  Date range of returned events:")
                print(f"    Earliest: {dates[0]}")
                print(f"    Latest: {dates[-1]}")
            
            # Show registration types
            reg_types = {}
            for e in events:
                reg_type = e.get('registration', {}).get('type', 'UNKNOWN')
                reg_types[reg_type] = reg_types.get(reg_type, 0) + 1
            print(f"\n  Registration types: {reg_types}")
        
        return response
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def test_filter_syntaxes(client):
    """Test various filter syntaxes to find what works."""
    print_section("TESTING FILTER SYNTAXES FOR EVENTS API")
    
    # List of filters to test
    filters_to_test = [
        # Basic - no filter
        {
            "label": "No filter (baseline)",
            "payload": {"query": {"paging": {"limit": 5}}}
        },
        # Status filter (known to work)
        {
            "label": "Filter by status (array)",
            "payload": {"query": {"paging": {"limit": 5}, "filter": {"status": ["PUBLISHED"]}}}
        },
        # Date filters - various syntaxes
        {
            "label": "Filter by scheduling.config.startDate (gte)",
            "payload": {"query": {"paging": {"limit": 5}, "filter": {"scheduling.config.startDate": {"$gte": "2020-01-01T00:00:00Z"}}}}
        },
        {
            "label": "Filter by startDate (gte) - no nesting",
            "payload": {"query": {"paging": {"limit": 5}, "filter": {"startDate": {"$gte": "2020-01-01T00:00:00Z"}}}}
        },
        # Date range at query level
        {
            "label": "fromLocalDate/toLocalDate at query level",
            "payload": {
                "query": {"paging": {"limit": 5}},
                "fromLocalDate": "2020-01-01",
                "toLocalDate": "2025-12-31"
            }
        },
        # Date range inside query
        {
            "label": "fromLocalDate/toLocalDate inside query",
            "payload": {
                "query": {
                    "paging": {"limit": 5},
                    "fromLocalDate": "2020-01-01",
                    "toLocalDate": "2025-12-31"
                }
            }
        },
        # Recurrence filter
        {
            "label": "Filter by recurrenceStatus",
            "payload": {"query": {"paging": {"limit": 5}, "filter": {"recurrenceStatus": ["ONE_TIME", "RECURRING"]}}}
        },
        # Registration type
        {
            "label": "Filter by registration.type (might fail)",
            "payload": {"query": {"paging": {"limit": 5}, "filter": {"registration.type": "TICKETING"}}}
        },
    ]
    
    results = []
    for test in filters_to_test:
        response = test_events_query(client, test["payload"], test["label"])
        results.append({
            "label": test["label"],
            "success": response is not None,
            "count": len(response.get("events", [])) if response else 0,
            "total": response.get("pagingMetadata", {}).get("total") if response else None
        })
    
    # Summary
    print_section("FILTER TEST SUMMARY")
    print(f"\n{'Label':<50} {'Status':<10} {'Count':<10} {'Total':<10}")
    print("-" * 80)
    for r in results:
        status = "✓ OK" if r["success"] else "✗ FAILED"
        print(f"{r['label']:<50} {status:<10} {r['count']:<10} {str(r['total']):<10}")


def query_events_with_options(client, args):
    """Query events with command-line options."""
    print_section("EVENTS API QUERY")
    
    # Build payload
    query_obj = {
        "paging": {"limit": args.limit}
    }
    
    if args.filter:
        try:
            filter_dict = json.loads(args.filter)
            query_obj["filter"] = filter_dict
        except json.JSONDecodeError as e:
            print(f"Error parsing filter JSON: {e}")
            return
    
    payload = {"query": query_obj}
    
    # Add date range if specified
    if args.from_date:
        payload["fromLocalDate"] = args.from_date
    if args.to_date:
        payload["toLocalDate"] = args.to_date
    
    # Use raw payload if provided
    if args.raw_payload:
        try:
            payload = json.loads(args.raw_payload)
        except json.JSONDecodeError as e:
            print(f"Error parsing raw payload JSON: {e}")
            return
    
    response = test_events_query(client, payload, "Custom Query")
    
    if response and args.full:
        print("\n--- Full Response ---")
        print_response(response, full=True)
    elif response and args.show_sample:
        events = response.get("events", [])
        if events:
            print("\n--- Sample Event ---")
            print(json.dumps(events[0], indent=2, default=str))


def query_generic(client, endpoint_path, args):
    """Query a generic endpoint."""
    print_section(f"QUERYING: {endpoint_path}")
    
    payload = {"query": {"paging": {"limit": args.limit}}}
    
    if args.raw_payload:
        try:
            payload = json.loads(args.raw_payload)
        except json.JSONDecodeError as e:
            print(f"Error parsing raw payload JSON: {e}")
            return
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("-" * 40)
    
    try:
        response = client.post(endpoint_path, json=payload)
        print("✓ Success!")
        print_response(response, full=args.full)
    except Exception as e:
        print(f"✗ Error: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Test Wix API query parameters and filters',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Test what events are returned by default
    python scripts/test_api_query.py --endpoint events
    
    # Test all filter syntaxes to see what works
    python scripts/test_api_query.py --endpoint events --test-filters
    
    # Test with a specific filter
    python scripts/test_api_query.py --endpoint events --filter '{"status": ["PUBLISHED"]}'
    
    # Test date range
    python scripts/test_api_query.py --endpoint events --from-date 2020-01-01 --to-date 2025-12-31
    
    # Test raw payload with full control
    python scripts/test_api_query.py --endpoint events --raw-payload '{"query": {"paging": {"limit": 10}}}'
        """
    )
    
    parser.add_argument(
        '--endpoint',
        choices=['events', 'guests', 'contacts', 'orders'],
        default='events',
        help='API endpoint to test (default: events)'
    )
    parser.add_argument(
        '--filter',
        type=str,
        help='JSON filter object (e.g., \'{"status": ["PUBLISHED"]}\')'
    )
    parser.add_argument(
        '--from-date',
        type=str,
        help='Start date for date range filter (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--to-date',
        type=str,
        help='End date for date range filter (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--raw-payload',
        type=str,
        help='Raw JSON payload (overrides other options)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Number of results to return (default: 10)'
    )
    parser.add_argument(
        '--full',
        action='store_true',
        help='Show full response (not truncated)'
    )
    parser.add_argument(
        '--show-sample',
        action='store_true',
        help='Show a sample record from the response'
    )
    parser.add_argument(
        '--test-filters',
        action='store_true',
        help='Test various filter syntaxes to find what works'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("WIX API QUERY TESTER")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Initialize client
    print("\nInitializing Wix API client...")
    client = WixAPIClient.from_env()
    print("✓ Client initialized")
    
    try:
        if args.test_filters:
            if args.endpoint == 'events':
                test_filter_syntaxes(client)
            else:
                print(f"\n--test-filters not implemented for {args.endpoint}")
        elif args.endpoint == 'events':
            query_events_with_options(client, args)
        elif args.endpoint == 'guests':
            query_generic(client, "/events/v2/guests/query", args)
        elif args.endpoint == 'contacts':
            query_generic(client, "/contacts/v4/contacts", args)
        elif args.endpoint == 'orders':
            # Orders uses a different format
            payload = {"search": {"paging": {"limit": args.limit}}}
            if args.raw_payload:
                payload = json.loads(args.raw_payload)
            print_section("ORDERS API QUERY")
            print(f"Payload: {json.dumps(payload, indent=2)}")
            try:
                response = client.post("/ecom/v1/orders/search", json=payload)
                print("✓ Success!")
                print_response(response, full=args.full)
            except Exception as e:
                print(f"✗ Error: {e}")
    finally:
        client.close()
    
    print("\n" + "=" * 80)
    print("QUERY TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()

