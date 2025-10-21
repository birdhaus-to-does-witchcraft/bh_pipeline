"""
Historical data backfill script - one-time extraction of historical data.

This script performs a one-time extraction of historical data for a specific
date range, useful for initial setup or recovering missing data.

Usage:
    python scripts/backfill_historical.py --start-date 2024-01-01 --end-date 2025-01-01
    # Or if installed: wix-backfill --start-date 2024-01-01 --end-date 2025-01-01
"""

import sys
import argparse
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.logger import setup_logging
from utils.config import load_config


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Backfill historical data from Wix APIs"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        required=True,
        help="Start date for historical extraction (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date",
        type=str,
        required=True,
        help="End date for historical extraction (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--entities",
        type=str,
        nargs="+",
        default=["events", "guests", "tickets", "contacts", "transactions"],
        help="Entity types to backfill (default: all)"
    )
    return parser.parse_args()


def main():
    """Main entry point for historical data backfill."""
    # Parse arguments
    args = parse_args()

    # Set up logging
    logger = setup_logging(log_dir="logs", log_level="INFO")
    logger.info("=" * 60)
    logger.info("Starting historical data backfill from Wix APIs")
    logger.info(f"Date range: {args.start_date} to {args.end_date}")
    logger.info(f"Entities: {', '.join(args.entities)}")
    logger.info("=" * 60)

    try:
        # Validate dates
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d")

        if start_date >= end_date:
            logger.error("Start date must be before end date")
            return 1

        # Load configuration
        config = load_config()
        logger.info("Configuration loaded successfully")

        # TODO: Implement in Phase 4
        # - Create API client
        # - For each entity type:
        #   - Query data within date range
        #   - Save raw data
        #   - Transform and save processed data
        # - Create archive snapshot
        # - Log completion metrics

        logger.warning("Historical backfill not yet implemented (Phase 4)")
        logger.info("This is a placeholder script. Implementation coming in Phase 4.")

    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        logger.info("Please use YYYY-MM-DD format for dates")
        return 1
    except Exception as e:
        logger.error(f"Backfill failed: {e}", exc_info=True)
        return 1

    logger.info("Historical data backfill completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
