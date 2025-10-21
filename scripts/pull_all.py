"""
Full data extraction script - pulls all data from Wix APIs.

This script extracts complete datasets for all entity types:
- Events
- Event Guests
- Tickets
- Contacts
- Transactions
- RSVPs

Usage:
    python scripts/pull_all.py
    # Or if installed: wix-pull-all
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.logger import setup_logging
from utils.config import load_config


def main():
    """Main entry point for full data extraction."""
    # Set up logging
    logger = setup_logging(log_dir="logs", log_level="INFO")
    logger.info("=" * 60)
    logger.info("Starting full data extraction from Wix APIs")
    logger.info("=" * 60)

    try:
        # Load configuration
        config = load_config()
        logger.info("Configuration loaded successfully")

        # TODO: Implement in Phase 4
        # - Create API client
        # - Extract events
        # - Extract guests
        # - Extract tickets
        # - Extract contacts
        # - Extract transactions
        # - Extract RSVPs
        # - Save raw data
        # - Transform and save processed data
        # - Create archive snapshot
        # - Log completion metrics

        logger.warning("Full data extraction not yet implemented (Phase 4)")
        logger.info("This is a placeholder script. Implementation coming in Phase 4.")

    except Exception as e:
        logger.error(f"Data extraction failed: {e}", exc_info=True)
        return 1

    logger.info("Full data extraction completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
