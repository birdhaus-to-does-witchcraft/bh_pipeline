# Birdhaus Data Pipeline

A Python ETL pipeline that extracts event, guest, contact, and sales data from Wix REST APIs, transforms nested JSON into flat CSV files, and outputs Excel-compatible spreadsheets for analysis.

Built for **Birdhaus Shibari Studio** to replace manual Wix CSV exports with automated, repeatable data pulls.

## Architecture

```
Wix REST APIs                  Python Pipeline                    Output
 ──────────────                ────────────────                   ──────
 Events API V3  ──┐
 Guests API V2  ──┤  Extract    Transform       Load
 Contacts V4    ──┼──────────►──────────────►──────────►  Timestamped
 Orders API V1  ──┤  API calls   Flatten JSON     CSV      CSV files
 Tickets V1     ──┤  Pagination  Date conversion   Export   (UTF-8 BOM)
 Transactions V1──┤  Rate limit  Enrichment
 RSVP API V2    ──┘  Retry       Field selection
```

### Module Structure

```
src/
├── wix_api/            # API client and endpoint wrappers
│   ├── client.py       # Core HTTP client (auth, rate limiting, retries)
│   ├── events.py       # Events API V3 wrapper
│   ├── guests.py       # Event Guests API V2 wrapper
│   ├── contacts.py     # Contacts API V4 wrapper
│   ├── orders.py       # Event Orders API V1 wrapper
│   ├── tickets.py      # Tickets API V1 wrapper
│   ├── transactions.py # eCommerce Transactions API V1 wrapper
│   └── rsvp.py         # RSVP API V2 wrapper
│
├── transformers/       # Data transformation layer
│   ├── base.py         # Shared utilities (encoding, dates, CSV export)
│   ├── events.py       # Events transformer (~55 output fields)
│   ├── guests.py       # Guests transformer (~31 fields + enrichment)
│   ├── contacts.py     # Contacts transformer (~36 fields)
│   ├── order_summaries.py  # Sales summary transformer (12 fields)
│   ├── event_orders.py     # Individual orders transformer (~38 fields)
│   └── transactions.py     # eCommerce transactions transformer
│
└── utils/              # Infrastructure
    ├── config.py        # Pydantic-validated configuration
    ├── logger.py        # Dual file/console logging
    ├── pagination.py    # Generic offset-based pagination
    └── retry.py         # Retry decorators, rate limiting, custom exceptions
```

## Setup

### Prerequisites

- Python 3.8+
- A Wix API key with access to Events, Contacts, and eCommerce APIs

### Installation

```bash
# Clone and set up virtual environment
cd birdhaus_data_pipeline
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Or install as a package (enables CLI commands)
pip install -e .
```

### Credentials

Copy the template and fill in your Wix API credentials:

```bash
cp config/credentials.env.template .env
```

Edit `.env` with your values:

```bash
# Required
WIX_API_KEY=your_api_key_here

# Optional but recommended
WIX_ACCOUNT_ID=your_account_id_here
WIX_SITE_ID=your_site_id_here
```

## Configuration

Configuration loads from a `.env` file (default) or a YAML file, validated by Pydantic models.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `WIX_API_KEY` | *(required)* | Wix API key for authentication |
| `WIX_ACCOUNT_ID` | `None` | Wix account ID |
| `WIX_SITE_ID` | `None` | Wix site ID |
| `WIX_BASE_URL` | `https://www.wixapis.com` | API base URL |
| `DATA_BASE_PATH` | `birdhaus_data` | Base path for data storage |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `LOG_DIR` | `logs` | Directory for log files |
| `RATE_LIMIT_MAX_CALLS` | `100` | Max API calls per period |
| `RATE_LIMIT_PERIOD` | `60` | Rate limit period in seconds |
| `RETRY_MAX_ATTEMPTS` | `3` | Max retry attempts per request |
| `RETRY_MIN_WAIT` | `4` | Minimum retry wait (seconds) |
| `RETRY_MAX_WAIT` | `10` | Maximum retry wait (seconds) |

### YAML Configuration

Alternatively, use `config/pipeline_config.yaml` for the same settings in structured format:

```python
from utils.config import PipelineConfig

config = PipelineConfig.from_yaml("config/pipeline_config.yaml")
# or
config = PipelineConfig.from_env()  # loads from .env
```

## Usage

### Full Data Pull

Extracts all entity types (Events, Contacts, Guests, Order Summaries, Event Orders) into timestamped CSV files:

```bash
python scripts/pull_all.py

# With custom output directory
python scripts/pull_all.py --output-dir /path/to/output

# Or via CLI entry point (after pip install -e .)
wix-pull-all
```

Output files share a timestamp so you know which files belong to the same run:

```
data/processed/
├── events_20260211_143022.csv
├── contacts_20260211_143022.csv
├── guests_20260211_143022.csv
├── order_summaries_20260211_143022.csv
└── event_orders_20260211_143022.csv
```

### Upcoming Events Only

Pulls only upcoming ticketing events (used by the GitHub Actions weekly schedule):

```bash
python scripts/pull_upcoming_events.py
```

### Execution Flow

`pull_all.py` follows this sequence:

1. Initialize `WixAPIClient` from `.env` credentials
2. Extract all events via `EventsAPI.get_all_events()`, filter to TICKETING type
3. Extract all contacts via `ContactsAPI.get_all_contacts()`
4. Extract all guests via `GuestsAPI.get_all_guests()`
5. Extract order summaries per event via `OrdersAPI.get_summary_by_event()` (parallel, 10 workers)
6. Extract all event orders via `OrdersAPI.get_all_orders()`
7. Transform each dataset through its respective Transformer class
8. Save all output to timestamped CSV files with UTF-8 BOM encoding

## Data Entities

### Events

Source: Events API V3 (`POST /events/v3/events/query`)

The events transformer flattens deeply nested event data into ~55 columns covering identification, scheduling, location, registration, pricing, images, descriptions, and metadata. Key transformations:

- **Date/time splitting**: ISO datetime strings are split into separate `start_date`, `start_time`, `end_date`, `end_time` columns
- **Timezone conversion**: UTC times are converted to the event's local timezone (e.g., `America/Toronto`)
- **Day-of-week derivation**: `day_of_week`, `day_of_week_num`, and `is_weekend` are calculated from the start date
- **Location flattening**: Nested address objects become `location_city`, `location_country`, `location_latitude`, etc.
- **Description extraction**: Plain text is extracted from Wix rich text nodes; a `description_full` field provides the best available description
- **Price range**: `lowest_price` and `highest_price` from ticket definitions

### Contacts

Source: Contacts API V4 (`GET /contacts/v4/contacts`)

Transforms contact records into ~36 columns. Contacts contain PII (emails, phones) -- handle according to privacy regulations.

- **Email handling**: Extracts primary email, email tag, and email count from the nested emails array
- **Member info**: Flattens site membership details (signup date, role, verification status)
- **Extended fields**: Extracts display names and membership status from Wix extended fields

### Guests

Source: Event Guests API V2 (`POST /events/v2/guests/query`)

Transforms guest records into ~31 columns. Requires the `GUEST_DETAILS` fieldset for full data.

- **Guest types**: RSVP, BUYER, or TICKET_HOLDER
- **Ticket flattening**: Ticket arrays are flattened to `ticket_count`, `ticket_names`, `ticket_numbers`, plus a `primary_ticket_*` set
- **Contact enrichment**: The Guests API returns minimal name/email data. The pipeline joins guests with contacts via `contactId` to populate `first_name`, `last_name`, `email`, and `phone` fields.
- **Form responses**: Custom registration form fields (phone, company, dietary notes) are extracted when present

### Order Summaries

Source: Orders API V1 (`GET /events/v1/orders/summary`)

Provides per-event sales aggregates (12 columns):

- `total_sales_amount` / `revenue_amount` -- gross sales vs. net revenue (after Wix fees)
- `wix_fees_amount` / `wix_fees_percentage` -- calculated fee breakdown
- `total_orders` / `total_tickets` -- volume counts
- `avg_ticket_price` -- calculated average

### Event Orders

Source: Orders API V1 (`GET /events/v1/orders`)

Individual ticket purchase records (~38 columns):

- Buyer details (name, email, contact ID)
- Order status, channel (ONLINE/OFFLINE), confirmation
- Ticket breakdown (names, numbers, prices per ticket in the order)
- Payment details (transaction ID, method, subtotal, total, tax, discount, fees)
- Timestamps (created, updated)

## Transformers

All transformers extend `BaseTransformer`, which provides:

- **`clean_special_characters()`** -- Replaces Unicode characters (curly quotes, em dashes, etc.) with ASCII equivalents
- **`extract_date_and_time()`** -- Splits ISO datetime strings into date and time components with optional timezone conversion
- **`flatten_price()`** -- Extracts value, currency, and formatted amount from nested price objects
- **`save_to_csv()`** -- Exports to CSV with UTF-8 BOM encoding (default) for Excel compatibility. Also supports plain UTF-8 and ASCII-only modes.

Each entity transformer follows the same pattern:

```python
# Transform raw API data
transformed = EventsTransformer.transform_events(raw_events)

# Or transform and save in one step
EventsTransformer.save_to_csv(raw_events, "output/events.csv")
```

## Scripts Reference

### Production Scripts

| Script | Purpose | Usage |
|---|---|---|
| `pull_all.py` | Full extraction of all entity types | `python scripts/pull_all.py [--output-dir PATH]` |
| `pull_upcoming_events.py` | Upcoming ticketing events only | `python scripts/pull_upcoming_events.py [--output-dir PATH]` |
| `pull_incremental.py` | Delta updates (placeholder) | Not yet implemented |
| `backfill_historical.py` | Historical data backfill (placeholder) | Not yet implemented |

### Testing Scripts

| Script | Purpose |
|---|---|
| `test_pipeline.py` | Staged pipeline testing (setup, client, wrappers, transformers) |
| `test_all_transformers.py` | Tests all transformers with real API data |
| `test_api_query.py` | Tests API query syntax, filters, pagination |
| `test_encoding_fix.py` | Validates UTF-8 BOM encoding for Excel compatibility |

### Debugging Scripts

| Script | Purpose |
|---|---|
| `debug_api.py` | Tests API response structure, pagination, fieldsets |
| `diagnose_guests_issue.py` | Diagnoses guest data retrieval problems |

### Analysis and Utility Scripts

| Script | Purpose |
|---|---|
| `analyze_data_coverage.py` | Shows raw vs. transformed field counts |
| `show_new_fields.py` | Documents calculated/enriched fields added by transformers |
| `check_event_dates.py` | Validates event date data |
| `generate_views.py` | Generates data views |
| `clean_csv.py` | CSV post-processing (column removal, filtering, merging) |

### CLI Entry Points

After `pip install -e .`, these commands are available:

```bash
wix-pull-all            # → scripts/pull_all.py
wix-pull-incremental    # → scripts/pull_incremental.py (placeholder)
wix-backfill            # → scripts/backfill_historical.py (placeholder)
```

## CI/CD

A GitHub Actions workflow runs weekly to pull upcoming events:

- **Schedule**: Every Sunday at 12 PM Eastern (5 PM UTC)
- **Trigger**: Also supports manual `workflow_dispatch`
- **Runner**: `ubuntu-latest` with Python 3.12
- **Output**: CSV files uploaded as artifacts with 90-day retention
- **Secrets required**: `WIX_API_KEY`, `WIX_ACCOUNT_ID`, `WIX_SITE_ID`

See `.github/workflows/pull-upcoming-events.yml` for details.

## Error Handling

The pipeline uses a layered error handling approach:

- **Connection level**: `urllib3.Retry` handles transient connection failures (retries on 500, 502, 503, 504)
- **Application level**: `tenacity` retry decorator with exponential backoff (3 attempts, 4-10s wait)
- **Rate limiting**: `pyrate-limiter` enforces 100 requests per 60 seconds; respects `Retry-After` headers on 429 responses
- **Custom exceptions**: `AuthenticationError`, `RateLimitError`, `APIError` for clear error categorization
- **Script level**: Each extraction step catches exceptions independently so one failure doesn't stop the others

## Project Structure

```
birdhaus_data_pipeline/
├── .github/workflows/
│   └── pull-upcoming-events.yml   # Weekly GitHub Actions workflow
├── config/
│   ├── credentials.env.template   # Environment variable template
│   ├── logging.yaml               # Logging handler configuration
│   └── pipeline_config.yaml       # YAML-based pipeline configuration
├── docs/
│   ├── archive/                   # Historical investigation notes
│   └── CHANGELOG.md               # Project changelog
├── notebooks/
│   ├── analysis.ipynb             # Data analysis notebook
│   └── attendee_crossover.ipynb   # Attendee overlap analysis
├── scripts/                       # Executable scripts (see Scripts Reference)
├── src/
│   ├── wix_api/                   # API client and endpoint wrappers
│   ├── transformers/              # Data transformation layer
│   └── utils/                     # Configuration, logging, pagination, retry
├── tests/                         # Test directory (pytest)
├── .env                           # Credentials (not committed)
├── CLAUDE.md                      # AI assistant instructions
├── API_REFERENCE.md               # Wix API endpoint reference
├── requirements.txt               # Python dependencies
└── setup.py                       # Package configuration
```

## Dependencies

**Runtime:**
- `requests` -- HTTP client
- `pandas` -- DataFrame processing and CSV export
- `pydantic` -- Configuration validation
- `pyrate-limiter` -- API rate limiting
- `tenacity` -- Retry logic with exponential backoff
- `python-dotenv` -- Environment variable loading
- `pyyaml` -- YAML configuration parsing

**Development:**
- `pytest`, `pytest-cov`, `pytest-mock` -- Testing
- `responses` -- HTTP response mocking
- `mypy`, `types-requests`, `types-PyYAML` -- Type checking
- `structlog` -- Structured logging (optional)
