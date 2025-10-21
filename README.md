# Birdhaus Data Pipeline

Python-based data pipeline for extracting event, ticket, guest, payment, and customer data from the Wix platform via REST APIs.

## Overview

This pipeline automates the extraction and transformation of data from Wix Events & Tickets platform, replacing manual CSV exports with real-time API access. It provides richer, more granular data for analytics and reporting.

## Features

- **Automated Data Extraction**: Scheduled pulls from Wix APIs
- **Rich Data Access**: Individual-level records (events, guests, tickets, contacts, transactions)
- **Proper Customer Identification**: Contact IDs and emails instead of name-based matching
- **Rate Limiting**: Respects API quotas with automatic throttling
- **Retry Logic**: Automatic retries with exponential backoff for failed requests
- **Data Quality**: Validation, logging, and error handling throughout
- **Multiple Storage Formats**: Raw JSON and processed CSV/Parquet

## Project Structure

```
birdhaus_data_pipeline/
├── src/
│   ├── wix_api/              # API client and endpoint wrappers
│   │   ├── client.py         # Core API client
│   │   ├── events.py         # Events API wrapper
│   │   ├── guests.py         # Guests API wrapper
│   │   ├── tickets.py        # Tickets API wrapper
│   │   ├── contacts.py       # Contacts API wrapper
│   │   └── transactions.py   # Transactions API wrapper
│   ├── extractors/           # Data extraction logic
│   ├── transformers/         # Data cleaning and transformation
│   └── utils/                # Utilities (config, logging, retry)
├── scripts/                  # Orchestration scripts
│   ├── pull_all.py          # Full data extraction
│   ├── pull_incremental.py # Delta updates only
│   └── backfill_historical.py
├── tests/                   # Unit and integration tests
├── config/                  # Configuration files
│   ├── credentials.env.template
│   ├── pipeline_config.yaml
│   └── logging.yaml
└── requirements.txt         # Python dependencies
```

## Installation

### Prerequisites

- Python 3.8 or higher
- Wix API credentials (API key, account ID, site ID)

### Setup

1. **Clone or navigate to the project:**
   ```bash
   cd /mnt/c/Users/saaku/the-lab/technologist/birdhaus_projects/birdhaus_data_pipeline
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows WSL
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up credentials:**
   ```bash
   # Copy template
   cp config/credentials.env.template .env

   # Edit .env and add your Wix API credentials
   nano .env
   ```

5. **Install package in development mode:**
   ```bash
   pip install -e .
   ```

## Configuration

### Environment Variables

Create a `.env` file in the project root with your Wix API credentials:

```bash
# Required
WIX_API_KEY=your_api_key_here
WIX_ACCOUNT_ID=your_account_id_here
WIX_SITE_ID=your_site_id_here

# Optional - Override defaults
DATA_BASE_PATH=/path/to/birdhaus_data
LOG_LEVEL=INFO
RATE_LIMIT_MAX_CALLS=100
RATE_LIMIT_PERIOD=60
```

### Getting Wix API Credentials

1. Go to https://dev.wix.com/
2. Create or log into your developer account
3. Register an app or generate API keys
4. Obtain your API key, account ID, and site ID

See: https://dev.wix.com/docs/build-apps/get-started/authentication

## Usage

### Basic Usage

```python
from src.wix_api.client import WixAPIClient
from src.utils.config import load_config

# Load configuration from .env
config = load_config()

# Create API client
with WixAPIClient.from_config(config) as client:
    # Query events
    response = client.post("/v3/events/query", json={
        "query": {
            "filter": {"status": ["PUBLISHED"]},
            "paging": {"limit": 100}
        }
    })

    events = response.get("events", [])
    print(f"Found {len(events)} events")
```

### Running Scripts

```bash
# Full data extraction (all entities)
python scripts/pull_all.py

# Incremental update (new data only)
python scripts/pull_incremental.py

# Historical backfill
python scripts/backfill_historical.py --start-date 2024-01-01 --end-date 2025-01-01
```

## API Endpoints

This pipeline uses the following Wix API versions (as of October 2025):

| API | Version | Endpoint |
|-----|---------|----------|
| Events | V3 | `/v3/events/query` |
| Event Guests | V2 | `/events-guests/v2/guests/query` |
| Tickets | V1 | `/events/v1/tickets` |
| Contacts | V4 | `/v4/contacts/query` |
| Transactions | V1 | `/v1/orders/transactions/query` |
| RSVP | V2 | `/v2/rsvps` |

For full API documentation, see: https://dev.wix.com/docs/rest

## Data Storage

Data is stored in the `birdhaus_data/` directory (configurable):

```
birdhaus_data/
├── raw/                  # Raw API responses (JSON)
│   ├── events/
│   ├── guests/
│   ├── tickets/
│   ├── contacts/
│   └── transactions/
├── processed/            # Cleaned data (CSV/Parquet)
│   ├── events.csv
│   ├── guests.csv
│   ├── tickets.csv
│   ├── contacts.csv
│   └── transactions.csv
├── archive/              # Historical snapshots
└── metadata/             # Pipeline run logs
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_wix_api.py
```

### Code Quality

```bash
# Type checking
mypy src/

# Linting
pylint src/
```

## Documentation

### Quick Start Guides
- **[README.md](README.md)** - This file - project overview and setup
- **[API_REFERENCE.md](API_REFERENCE.md)** - Wix API endpoints, authentication, pagination
- **[TRANSFORMERS.md](TRANSFORMERS.md)** - Data transformation guide
- **[MCP Server Setup](mcp_server/SETUP.md)** - MCP server installation and configuration

### Additional Documentation
- **[MCP Development Workflow](mcp_server/DEVELOPMENT_WORKFLOW.md)** - Using MCP server during development
- **[Changelog](docs/CHANGELOG.md)** - Historical bug fixes and improvements
- **[Developer Instructions](CLAUDE.md)** - Notes for AI assistants working on this project

### Archived Documentation
For historical planning documents and detailed fix analyses, see `docs/archive/`

## Roadmap

- [x] **Phase 1**: Foundation (API client, authentication, logging) ✅ COMPLETE
- [x] **Phase 2**: Core endpoints (events, guests, tickets, contacts, transactions) ✅ COMPLETE
- [x] **Phase 3**: Data transformation (transformers, encoding, enrichment) ✅ COMPLETE
- [ ] **Phase 4**: Orchestration scripts (full pull, incremental, backfill) 🚧 IN PROGRESS
- [ ] **Phase 5**: Integration with analytics notebooks
- [ ] **Phase 6**: Automation and monitoring
- [x] **Bonus**: MCP Server for real-time validation ✅ COMPLETE

## Privacy & Security

### PII Handling

This pipeline accesses personally identifiable information (PII) including:
- Email addresses
- Phone numbers
- Physical addresses
- Names

**Important:**
- Store `.env` file securely and never commit to version control
- Restrict access to raw data directory
- Use contact IDs instead of emails in analytics where possible
- Comply with PIPEDA (Canada) and GDPR (if applicable)
- Implement data retention policies

### Security Best Practices

- API keys stored in `.env` (gitignored)
- No credentials committed to version control
- Encrypted storage for sensitive data
- Regular credential rotation
- Audit logs for data access

## Troubleshooting

### Common Issues

**Authentication Error:**
```
AuthenticationError: Invalid API key or authentication failed
```
- Check that `WIX_API_KEY` is set correctly in `.env`
- Verify API key is valid and not expired
- Ensure proper permissions are granted

**Rate Limit Error:**
```
RateLimitError: API rate limit exceeded
```
- Pipeline will automatically retry after waiting
- Reduce `RATE_LIMIT_MAX_CALLS` in `.env` if persistent
- Check Wix API documentation for current rate limits

**Import Error:**
```
ModuleNotFoundError: No module named 'src'
```
- Install package in development mode: `pip install -e .`
- Verify virtual environment is activated

## Contributing

This is an internal project for Birdhaus Shibari Studio. For questions or issues, contact the project maintainer.

## License

Private - Internal Use Only

## References

- [Wix API Documentation](https://dev.wix.com/docs/rest)
- [Events API V3](https://dev.wix.com/docs/rest/business-solutions/events/wix-events/event)
- [Event Guests API V2](https://dev.wix.com/docs/rest/business-solutions/events/event-guests)
- [Contacts API V4](https://dev.wix.com/docs/rest/crm/members-contacts/contacts/introduction)

---

**Version:** 1.2
**Last Updated:** 2025-10-18
**Status:** Phase 3 Complete - Data Transformation & Documentation Consolidation Complete
