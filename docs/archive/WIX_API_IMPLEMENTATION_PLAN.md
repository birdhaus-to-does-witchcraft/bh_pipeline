# Wix API Data Pipeline Implementation Plan

**Project:** Birdhaus Shibari Studio Analytics
**Purpose:** Automated data extraction from Wix platform via REST APIs
**Status:** Phase 2 Complete - Core API Implementation Working
**Created:** 2025-10-18
**Last Updated:** 2025-10-18 (Phase 2 completed, all API endpoints implemented and tested)

---

## ⚠️ CRITICAL API VERSION UPDATES

**This document has been updated to use the latest Wix API versions as of October 2025:**

| API | Old Version (Deprecated) | Current Version | Status |
|-----|-------------------------|-----------------|--------|
| **Events API** | V1 | **V3** | V1 removed November 6, 2024 |
| **Event Guests API** | V1 | **V2** | V2 current as of 2025 |
| **RSVP API** | V1 | **V2** | V1 deprecated July 1, 2025 |
| **Tickets API** | - | **V1** | Current version |
| **Contacts API** | - | **V4** | Current version ✓ |
| **Order Transactions** | - | **V1** | Current version |

**Key Changes:**

- Events V3 now uses different endpoint structure and response format
- Guest API V2 requires explicit `guestDetails` fieldset to retrieve full guest information
- RSVP V2 replaces Rich Content with description field
- All query endpoints use standardized pagination with `hasNext` boolean
- Ticketed events cannot be converted to RSVP events and vice versa
- Site must have Wix Events & Tickets app installed

**Action Required Before Implementation:**

1. Use V3 endpoints for all Events API calls
2. Update query payloads to match new V3 structure
3. Include fieldsets in Guest API queries to retrieve detailed data
4. Test all endpoints with actual credentials to verify exact paths

---

## Executive Summary

This document outlines the complete plan for building a Python-based data pipeline to extract event, ticket, guest, payment, and customer data from the Wix platform via REST APIs. This will replace the current manual dashboard export workflow and unlock richer, real-time data access.

### Current State
- **Manual workflow:** Export CSV files from Wix dashboard
- **Limited data:** Summary-level events and payment transactions only
- **Customer identification:** Name-based `customer_id` (first_name + last_name) with limitations
- **Data freshness:** Manual exports, static snapshots
- **No API integration:** All data sourced from dashboard UI

### Future State
- **Automated workflow:** Scheduled API pulls via Python scripts
- **Rich data:** Events, guests, tickets, contacts, transactions with full detail
- **Customer identification:** Contact IDs, emails, phone numbers (proper PII handling)
- **Data freshness:** Real-time or near-real-time automated updates
- **API integration:** Direct REST API access to Wix platform

---

## Technology Decision: Python vs JavaScript SDK

### Recommendation: **Python with REST APIs**

**Rationale:**
1. **No Official Python SDK** - Wix only provides JavaScript SDK, not Python
2. **Existing Stack is Python** - Analytics project uses pandas, numpy, matplotlib, jupyter
3. **REST APIs Work Great** - Wix REST APIs are well-documented, standard HTTPS/JSON
4. **Better Integration** - Direct HTTP requests integrate seamlessly with pandas pipeline
5. **Less Complexity** - No need to bridge JavaScript ↔ Python or maintain separate runtimes

**Implementation Approach:**
- Use Python `requests` library for HTTP calls
- Build reusable API client wrapper class
- Return pandas DataFrames for seamless analysis integration

---

## Available Wix REST API Endpoints

### 1. Events API 📅

**Purpose:** Query event details, scheduling, status, and configuration

**Current Version:** V3 (V1 deprecated and removed November 6, 2024)

**Base URL:** `https://www.wixapis.com/events/v3`

**Key Endpoints:**
- `POST /events/v3/events/query` - Query events with filtering and pagination
- `GET /events/v3/events/{eventId}` - Get detailed event info by ID
- `GET /events/v3/events/by-slug/{slug}` - Get detailed event info by slug
- `GET /events/v3/events/by-category/{categoryId}` - List events by category
- `POST /events/v3/events` - Create new event
- `POST /events/v3/events/{eventId}/clone` - Clone existing event
- `PATCH /events/v3/events/{eventId}` - Update event
- `POST /events/v3/events/{eventId}/publish` - Publish draft event
- `POST /events/v3/events/{eventId}/cancel` - Cancel event
- `POST /events/v3/events/cancel` - Bulk cancel events by filter
- `DELETE /events/v3/events/{eventId}` - Delete event
- `POST /events/v3/events/delete` - Bulk delete events by filter
- `POST /events/v3/events/count-by-status` - Count events by status

**Available Data:**
- Event title, description, and status (published, draft, canceled)
- Start/end dates and recurrence patterns
- Location details (online/offline venues)
- Registration form configurations
- Online conferencing session details
- SEO settings and custom URLs
- Images and custom fields
- Ticket configuration per event

**Current Limitation (Dashboard Export):**
- Only summary-level event data
- Limited to visible fields in dashboard

**API Advantage:**
- Full event metadata and custom fields
- Real-time status updates
- Default registration form with first name, last name, and email fields
- Can filter by date ranges, categories, status
- Webhook support for event lifecycle (created, published, started, ended, canceled, cloned)
- **Note:** Ticketed events cannot be converted to RSVP events and vice versa
- **Requirement:** Site must have Wix Events & Tickets app installed

---

### 2. Event Guests API 👥

**Purpose:** Track individual attendees, RSVPs, and check-in status

**Current Version:** V2

**Base URL:** `https://www.wixapis.com/events/v2`

**Key Endpoints:**
- `POST /events/v2/guests/query` - Query all guests (default limit: 100, sorted by createdDate ASC)
- `GET /events/v2/guests/{guestId}` - Individual guest details

**Important:** Must include `fieldsets: ["GUEST_DETAILS"]` in request to retrieve full guest information

**Webhooks Available:**
- Event Guest Created
- Event Guest Updated
- Event Guest Deleted
- Guest Checked In
- Guest Event Canceled
- Guest Event Starts
- Guest Order Canceled

**Available Data:**
- **Individual ticket buyer information** (not aggregated)
- Guest attendance status (checked-in, not-checked-in, pending)
- RSVP details and responses
- **Registration form answers** (custom fields)
- Contact information linked to guests
- Guest check-in timestamps
- Member vs non-member identification

**Current Limitation (Dashboard Export):**
- No individual guest-level data
- Only aggregate counts (tickets sold, attendance)

**API Advantage:**
- Track repeat attendees across events
- Analyze individual customer attendance patterns
- Access registration form responses for deeper insights
- Build customer journey maps
- Calculate actual no-show rates (purchased but not attended)

---

### 3. Tickets API 🎫

**Purpose:** Manage ticket inventory, pricing, and check-in status

**Current Version:** V1

**Base URL:** `https://www.wixapis.com/events/v1`

**Key Endpoints:**
- `GET /events/v1/tickets` - List all tickets with filtering
- `GET /events/v1/tickets/{ticketNumber}` - Specific ticket details
- `POST /events/v1/tickets/query` - Query available tickets for checkout
- `POST /events/v1/tickets/check-in` - Check-in one or more tickets
- `DELETE /events/v1/tickets/check-in` - Delete check-in for one or more tickets

**Permission Required:** "Manage Guest List" scope

**Webhooks:** Triggers "Ticket Order Updated" event when check-in operations occur

**Available Data:**
- Individual ticket details (unique ticket numbers)
- Ticket inventory and availability tracking
- Ticket pricing tiers and variations
- Check-in status per ticket
- Ticket transfer/assignment history
- Reserved vs purchased ticket status
- Ticket-to-event relationships

**Current Limitation (Dashboard Export):**
- Only payment transaction summaries
- No ticket-level granularity
- No inventory or check-in data

**API Advantage:**
- Track ticket inventory in real-time
- Analyze pricing tier preferences
- Monitor sell-out patterns by event
- Identify no-shows (ticket purchased but not checked-in)
- Track ticket transfers or reassignments

---

### 4. Contacts/Members API 📇

**Purpose:** Access customer profiles, contact information, and member data

**Key Endpoints:**
- `POST /v4/contacts/query` - Query up to 1,000 contacts with filtering
- `GET /v4/contacts/{contactId}` - Individual contact profile
- `POST /v4/contacts` - Create new contact
- `PATCH /v4/contacts/{contactId}` - Update contact
- `GET /v4/contacts/{contactId}/extended-fields` - Custom contact fields

**Available Data:**
- **Contact ID** (unique, stable identifier)
- **Email addresses** (primary and secondary)
- **Phone numbers** (with type: mobile, home, work)
- **Physical addresses** (street, city, province, postal code, country)
- Name (first, last, full)
- Member status and member ID
- Creation and last modified timestamps
- **Extended custom fields** (tags, preferences, custom attributes)
- Contact labels and segmentation
- Member activity history

**Current Limitation (Dashboard Export):**
- **Only first_name + last_name in exports** (PII removed)
- Customer identification via name concatenation (`customer_id = first_name + last_name`)
- **Problems:**
  - Name duplicates merge distinct customers
  - Name changes split customer history
  - No email/phone for marketing analysis

**API Advantage:**
- ✅ **Fixes customer identification problem!** Use contact_id or email
- ✅ Access email for proper customer LTV and cohort analysis
- ✅ Phone numbers for communication preferences
- ✅ Address data for geographic analysis
- ✅ Custom fields for segmentation (if configured in Wix)
- ✅ Member vs guest distinction
- **Note:** Must handle PII responsibly (privacy compliance, secure storage)

---

### 5. Order Transactions API 💳

**Purpose:** Track payments, refunds, and transaction history

**Key Endpoints:**
- `POST /v1/orders/transactions/query` - List transactions for multiple orders
- `POST /v1/orders/{orderId}/payments` - Add/update payment records
- `PATCH /v1/orders/{orderId}/transactions/{transactionId}` - Update payment status

**Available Data:**
- Detailed payment transaction records
- **Payment status tracking** (authorized, captured, voided, refunded)
- Multiple payment methods per order (split payments)
- Gift card and discount code usage
- **Refund history** (full and partial refunds)
- Transaction timestamps (authorization, capture, refund times)
- Payment provider details (PayPal, credit card, etc.)
- Currency and amount details
- Service fees and net revenue

**Current Limitation (Dashboard Export):**
- Payment export shows completed transactions
- Limited refund detail
- No authorization vs capture distinction

**API Advantage:**
- Track refund patterns and calculate refund rates
- Analyze payment method preferences at granular level
- Monitor authorization vs capture timing (revenue recognition)
- Detect partial refunds and disputes
- Link payments to specific orders and events

---

### 6. RSVP API ✉️

**Purpose:** Manage free event RSVPs (non-ticketed events)

**Current Version:** V2 (V1 deprecated as of July 1, 2025)

**Key Endpoints:**
- `GET /v2/rsvps` - List RSVPs with filtering
- `POST /v2/rsvps` - Create RSVP
- `POST /v2/rsvps/{rsvpId}/checkin` - Check-in RSVP guest
- `PATCH /v2/rsvps/{rsvpId}` - Update RSVP status

**Important:** Rich Content field replaced by description field in Events V3 API

**Available Data:**
- RSVP status (yes, no, maybe, waitlist)
- Guest counts for RSVP events
- RSVP check-in data
- Contact information for RSVP guests

**Current Limitation (Dashboard Export + Analysis):**
- **RSVP events filtered out as "Wix platform artifacts"**
- Assumed all RSVPs are non-revenue placeholders
- No RSVP analysis in current notebook

**API Advantage:**
- Can distinguish real RSVP events from platform placeholders
- Track RSVP conversion to attendance
- Analyze no-show rates for free events
- Compare paid (ticketing) vs free (RSVP) event performance

**Important Note:**
- Need to clarify with Birdhaus: Are there legitimate free RSVP events to track?
- Or are all events ticketed (current assumption in analysis)?

---

## API Capabilities Comparison

| Feature | Dashboard Export (Current) | API Access (Proposed) |
|---------|---------------------------|----------------------|
| **Data Freshness** | Manual export, static snapshot | Real-time, automated pulls |
| **Data Granularity** | Aggregated summaries | Individual records (guests, tickets, transactions) |
| **Customer Identification** | Name only (`first_name + last_name`) | Contact ID, email, phone (proper identifiers) |
| **Historical Data** | Limited to export date range | Full historical query capability |
| **Automation** | Manual download required | Fully automated pipelines |
| **Custom Fields** | Not always included | Full access to extended fields |
| **Data Relationships** | Separate CSV files, manual joins | Linked data (contact→guest→ticket→event) |
| **Filtering** | Export everything, filter in Python | Filter at source (reduce data transfer) |
| **Check-in Data** | Not available | Per-ticket and per-guest check-in status |
| **Refund Details** | Limited | Full refund history and partial refunds |
| **Ticket Inventory** | Not available | Real-time availability tracking |
| **Registration Forms** | Not available | Custom field responses per guest |

---

## Project Structure Recommendation

### Decision: **Separate Data Pipeline Project (Phase 2 Approach)**

**Recommendation:** Create a structured data pipeline **within the existing repository** as a separate Python package, with the option to extract to a standalone repo later.

### Rationale

**Why Separate Pipeline from Analytics?**

1. **Separation of Concerns**
   - Pipeline: ETL (Extract, Transform, Load) logic
   - Analytics: Analysis, visualization, reporting
   - Clear boundaries = easier maintenance

2. **Reusability**
   - Pipeline becomes library for multiple consumers
   - Can serve Jupyter notebooks, dashboards, reports
   - Installable as Python package

3. **Testing & Quality**
   - Unit test API client independently
   - Mock API responses for testing
   - Validate data schemas before analysis
   - Catch errors early in pipeline

4. **Scheduling & Automation**
   - Standalone scripts for cron/scheduled runs
   - Incremental update logic
   - Logging and alerting
   - Not tied to notebook execution

5. **Dependency Management**
   - Pipeline: `requests`, `pydantic`, `tenacity` (production-focused)
   - Analytics: `pandas`, `matplotlib`, `jupyter` (analysis-focused)
   - Avoid bloated environments

6. **Version Control**
   - Pipeline changes tracked separately from analysis
   - Different release cycles
   - Clear git history

7. **Data Lineage**
   - Clear provenance (when pulled, from which API version)
   - Immutable raw data layer
   - Versioned data outputs
   - Reproducible analyses

### Proposed Folder Structure

```
birdhaus_projects/
│
├── birdhaus_data_pipeline/              # NEW - Data extraction project
│   ├── src/
│   │   ├── wix_api/
│   │   │   ├── __init__.py
│   │   │   ├── client.py                # Core API client (auth, rate limiting)
│   │   │   ├── events.py                # Events endpoint wrapper
│   │   │   ├── guests.py                # Guests endpoint wrapper
│   │   │   ├── tickets.py               # Tickets endpoint wrapper
│   │   │   ├── contacts.py              # Contacts endpoint wrapper
│   │   │   ├── transactions.py          # Payments/transactions wrapper
│   │   │   └── rsvps.py                 # RSVP endpoint wrapper
│   │   ├── extractors/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                  # Base extractor class
│   │   │   └── wix_extractor.py         # Wix-specific extraction logic
│   │   ├── transformers/
│   │   │   ├── __init__.py
│   │   │   └── data_cleaner.py          # Data cleaning/transformation
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── config.py                # Configuration management
│   │       ├── logger.py                # Logging setup
│   │       └── retry.py                 # Retry/rate limit logic
│   ├── scripts/
│   │   ├── pull_all.py                  # Main orchestration script
│   │   ├── pull_incremental.py         # Incremental updates only
│   │   └── backfill_historical.py      # One-time historical pull
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_wix_api.py             # API client tests
│   │   ├── test_extractors.py          # Extractor tests
│   │   └── fixtures/                    # Mock API responses
│   ├── config/
│   │   ├── credentials.env.template     # Template for API keys (not committed)
│   │   ├── pipeline_config.yaml         # Pipeline settings (endpoints, filters)
│   │   └── logging.yaml                 # Logging configuration
│   ├── requirements.txt                 # Pipeline dependencies
│   ├── setup.py                         # Makes package installable
│   ├── README.md                        # Pipeline documentation
│   ├── .gitignore                       # Ignore credentials, cache
│   └── .env                             # Actual credentials (gitignored)
│
├── birdhaus_data/                       # EXISTING - Data storage (shared)
│   ├── raw/                             # Raw API responses (JSON)
│   │   ├── events/
│   │   ├── guests/
│   │   ├── tickets/
│   │   ├── contacts/
│   │   └── transactions/
│   ├── processed/                       # Cleaned data (CSV or Parquet)
│   │   ├── events.csv
│   │   ├── tickets.csv
│   │   ├── guests.csv
│   │   ├── contacts.csv
│   │   └── transactions.csv
│   ├── archive/                         # Historical snapshots (timestamped)
│   └── metadata/                        # Data lineage, pull logs
│
└── birdhaus_data_analysis/              # EXISTING - Analytics project
    ├── birdhaus_analysis.ipynb          # Main analysis notebook
    ├── data_cleaning.ipynb              # May become simpler with API data
    ├── requirements.txt                 # Analysis dependencies
    ├── CLAUDE.md                        # Project instructions (existing)
    ├── PROJECT_ANALYSIS.md              # Project overview (existing)
    ├── WIX_API_IMPLEMENTATION_PLAN.md   # This document
    └── data_pull.py                     # OLD - will be replaced by pipeline
```

### Migration Path

**Phase 1: Initial Extraction (SKIP - Jump to Phase 2)**
- ~~Simple folder separation within repo~~

**Phase 2: Structured Package (START HERE)** ⭐
- Create `birdhaus_data_pipeline/` as proper Python package
- Separate dependencies (`requirements.txt` for pipeline)
- Make importable in notebooks
- Can still iterate quickly within same repo

**Phase 3: Separate Repository (FUTURE)**
- Extract `birdhaus_data_pipeline/` to standalone repo
- Publish as installable package (private PyPI or git+https)
- Analytics project imports via `pip install`

---

## Technical Implementation Details

### Authentication & Authorization

**Wix API Authentication Methods:**
1. **API Keys** - Simple, recommended for server-to-server access
2. **OAuth 2.0** - For apps requiring user-specific access (optional)

**API Key Approach (Recommended for this project):**
- Simpler setup for internal/private data pipelines
- Direct server-to-server authentication
- No user consent flow required
- Ideal for automated data extraction scripts

**Permission Scopes Needed:**
- **Events Management:** Read access to events data
- **Manage Guest List:** Read access for guest and ticket check-in data
- **Contacts:** Read access to contact information
- **eCommerce Orders:** Read access to order transactions

**Important Security Notes:**
- Store API keys in `.env` file (never commit to version control)
- Use environment variables in production
- Keep credentials secure and rotate periodically
- Restrict file system access to credential files

**Implementation:**
```python
# config/credentials.env.template
WIX_API_KEY=your_api_key_here
WIX_ACCOUNT_ID=your_account_id_here
WIX_SITE_ID=your_site_id_here
```

**Client Implementation:**
```python
import os
import requests
from typing import Dict, Any

class WixAPIClient:
    BASE_URL = "https://www.wixapis.com"

    def __init__(self, api_key: str, account_id: str = None, site_id: str = None):
        self.api_key = api_key
        self.account_id = account_id
        self.site_id = site_id
        self.session = requests.Session()

        # Standard headers for all requests
        headers = {
            "Authorization": api_key,
            "Content-Type": "application/json"
        }

        # Optional headers for specific account/site context
        if account_id:
            headers["wix-account-id"] = account_id
        if site_id:
            headers["wix-site-id"] = site_id

        self.session.headers.update(headers)

    @classmethod
    def from_env(cls):
        """Load credentials from environment variables"""
        return cls(
            api_key=os.getenv("WIX_API_KEY"),
            account_id=os.getenv("WIX_ACCOUNT_ID"),
            site_id=os.getenv("WIX_SITE_ID")
        )

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[Any, Any]:
        """Make authenticated request with error handling"""
        url = f"{self.BASE_URL}{endpoint}"
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
```

### Rate Limiting & Retries

**Wix API Rate Limits:**
- Typically 100-200 requests per minute (verify in docs)
- Need to implement exponential backoff

**Implementation (using pyrate-limiter):**
```python
from tenacity import retry, stop_after_attempt, wait_exponential
from pyrate_limiter import Duration, Rate, Limiter
import time

# Configure rate limiter: 100 requests per 60 seconds
rate = Rate(100, Duration.MINUTE)
limiter = Limiter(rate)

class WixAPIClient:
    def __init__(self, api_key: str, account_id: str = None, site_id: str = None):
        # ... existing initialization code
        self.limiter = limiter

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def _request(self, method: str, endpoint: str, **kwargs):
        """Make authenticated request with rate limiting and error handling"""
        # Apply rate limiting
        self.limiter.try_acquire("wix_api")

        url = f"{self.BASE_URL}{endpoint}"
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
```

**Alternative: Simple Rate Limiting with tenacity only:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential, wait_fixed
import time
from functools import wraps

class RateLimiter:
    """Simple rate limiter using timestamps"""
    def __init__(self, max_calls: int, period: int):
        self.max_calls = max_calls
        self.period = period
        self.calls = []

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            # Remove calls outside the time window
            self.calls = [call for call in self.calls if call > now - self.period]

            if len(self.calls) >= self.max_calls:
                sleep_time = self.period - (now - self.calls[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
                self.calls = self.calls[1:]

            self.calls.append(time.time())
            return func(*args, **kwargs)
        return wrapper

# Usage
rate_limiter = RateLimiter(max_calls=100, period=60)

class WixAPIClient:
    @rate_limiter
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def _request(self, method: str, endpoint: str, **kwargs):
        # ... existing request logic
```

### Pagination Handling

**Wix APIs use cursor-based pagination:**
```python
def query_all_events(self, filters: dict = None) -> pd.DataFrame:
    """Query all events with automatic pagination (Events V3 API)"""
    all_events = []
    cursor = None

    while True:
        # Build query payload for V3 API
        query_payload = {
            "query": {
                "paging": {"limit": 100}  # Max per request
            }
        }

        if cursor:
            query_payload["query"]["paging"]["cursor"] = cursor

        if filters:
            query_payload["query"]["filter"] = filters

        # Use V3 endpoint
        response = self._request("POST", "/v3/events/query", json=query_payload)
        all_events.extend(response.get("events", []))

        # Check for more pages
        paging_metadata = response.get("pagingMetadata", {})
        if not paging_metadata.get("hasNext", False):
            break
        cursor = paging_metadata.get("cursor")

    return pd.DataFrame(all_events)
```

### Data Transformation Pipeline

**Raw API Response → Cleaned DataFrame:**

```python
class EventTransformer:
    def transform(self, raw_events: List[dict]) -> pd.DataFrame:
        """Transform raw Events V3 API response to cleaned DataFrame"""
        if not raw_events:
            return pd.DataFrame()

        # Flatten nested structures from V3 API
        flattened = []
        for event in raw_events:
            flat_event = {
                'id': event.get('id'),
                'title': event.get('title', '').strip(),
                'status': event.get('status'),  # PUBLISHED, DRAFT, CANCELED, SCHEDULED
                'slug': event.get('slug'),
                'description': event.get('description'),  # Replaces rich content in V1
            }

            # Extract scheduling info (nested in V3)
            scheduling = event.get('scheduling', {}).get('config', {})
            flat_event['start_date'] = scheduling.get('startDate')
            flat_event['end_date'] = scheduling.get('endDate')
            flat_event['time_zone'] = scheduling.get('timeZoneId')

            # Extract location info
            location = event.get('location', {})
            flat_event['location_name'] = location.get('name')
            flat_event['location_type'] = location.get('type')  # VENUE or TBD

            # Extract registration info
            registration = event.get('registration', {})
            flat_event['registration_status'] = registration.get('status')

            flattened.append(flat_event)

        df = pd.DataFrame(flattened)

        # Date parsing
        df['start_date'] = pd.to_datetime(df['start_date'], utc=True)
        df['end_date'] = pd.to_datetime(df['end_date'], utc=True)

        # Create temporal features
        df['year'] = df['start_date'].dt.year
        df['month'] = df['start_date'].dt.month
        df['day_of_week'] = df['start_date'].dt.day_name()
        df['is_weekend'] = df['start_date'].dt.dayofweek.isin([5, 6])

        return df
```

### Error Handling & Logging

**Comprehensive logging:**
```python
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def setup_logging(log_dir: str = "logs"):
    """Configure logging with file and console handlers"""
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"pipeline_{datetime.now():%Y%m%d_%H%M%S}.log")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    return logger

# Usage in pipeline
logger.info("Starting data extraction...")
try:
    events_df = client.query_all_events()
    logger.info(f"Extracted {len(events_df)} events")
except Exception as e:
    logger.error(f"Failed to extract events: {e}", exc_info=True)
    raise
```

### Data Storage Strategy

**Multi-format storage:**
1. **Raw API responses** → JSON (immutable, full fidelity)
2. **Processed data** → Parquet (efficient) or CSV (human-readable)
3. **Archived snapshots** → Timestamped copies for historical comparison

```python
import json
from pathlib import Path

class DataStorage:
    def __init__(self, base_path: str = "/home/saaku/the-lab/birdhaus_projects/birdhaus_data"):
        self.base_path = Path(base_path)
        self.raw_path = self.base_path / "raw"
        self.processed_path = self.base_path / "processed"
        self.archive_path = self.base_path / "archive"

        # Create directories
        for path in [self.raw_path, self.processed_path, self.archive_path]:
            path.mkdir(parents=True, exist_ok=True)

    def save_raw(self, data: dict, entity_type: str):
        """Save raw API response as JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = self.raw_path / entity_type / f"{entity_type}_{timestamp}.json"
        file_path.parent.mkdir(exist_ok=True)

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved raw {entity_type} data to {file_path}")

    def save_processed(self, df: pd.DataFrame, entity_type: str, format: str = "csv"):
        """Save processed DataFrame"""
        file_path = self.processed_path / f"{entity_type}.{format}"

        if format == "csv":
            df.to_csv(file_path, index=False)
        elif format == "parquet":
            df.to_parquet(file_path, index=False)

        logger.info(f"Saved processed {entity_type} data to {file_path}")

    def archive_snapshot(self, entity_type: str):
        """Create timestamped archive of current processed data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        src = self.processed_path / f"{entity_type}.csv"
        dst = self.archive_path / f"{entity_type}_{timestamp}.csv"

        if src.exists():
            import shutil
            shutil.copy2(src, dst)
            logger.info(f"Archived {entity_type} to {dst}")
```

---

## Implementation Roadmap

### Phase 1: Foundation ✅ **COMPLETE**

**Status:** Completed October 18, 2025

**Accomplished:**
- ✅ Created complete project structure with src/, scripts/, config/, tests/
- ✅ Implemented `WixAPIClient` base class with full authentication
- ✅ Set up configuration management via `.env` file
- ✅ Implemented rate limiting (100 requests/60s) with pyrate_limiter
- ✅ Added retry logic with exponential backoff using tenacity
- ✅ Created comprehensive logging infrastructure
- ✅ Successfully tested API connection to Wix Events V3 API

**Test Results:**
- API client loads configuration correctly
- Authentication headers properly set
- Successfully connects to Wix APIs
- Can retrieve all 111 events from the account

---

### Phase 2: Core Endpoints ✅ **COMPLETE**

**Status:** Completed October 18, 2025

**Accomplished:**
- ✅ Implemented `EventsAPI` - Full Events V3 wrapper with query, get, and count methods
- ✅ Implemented `GuestsAPI` - Guests V2 wrapper with fieldsets support
- ✅ Implemented `RSVPAPI` - RSVP V2 endpoint wrapper
- ✅ Implemented `ContactsAPI` - Contacts V4 wrapper with list and get methods
- ✅ Implemented `TransactionsAPI` - Transactions V1 wrapper structure
- ✅ Created centralized pagination utility (`utils/pagination.py`)
- ✅ Fixed Events API V3 query structure (wrapped in `{"query": {...}}`)
- ✅ Fixed pagination detection (using count/total instead of hasNext)
- ✅ Successfully exports events and guests to CSV files

**Key Improvements:**
- Eliminated 141 lines of duplicated pagination code (87% reduction)
- All endpoints properly handle pagination
- Export script successfully pulls all 111 events (not limited to 100)
- Rate limiting and retry logic working across all endpoints

---

### Phase 3: Data Transformation (Week 3) 🚧 **IN PROGRESS**

**Goals:**
- Transform API responses to pandas DataFrames
- Clean and normalize data
- Match existing CSV schema (for backward compatibility)

**Tasks:**
1. Implement `EventTransformer` class
2. Implement `GuestTransformer` class
3. Implement `TicketTransformer` class
4. Implement `ContactTransformer` class
5. Implement `TransactionTransformer` class
6. Handle nested JSON fields (flatten structures)
7. Create temporal features (year, month, day_of_week)
8. Create derived flags (is_successful, has_discount, etc.)
9. Save processed DataFrames as CSV/Parquet

**Deliverables:**
- Cleaned DataFrames matching current CSV schema
- Processed data saved to `birdhaus_data/processed/`
- Documentation of schema mapping (API → DataFrame)

---

### Phase 4: Orchestration Scripts (Week 4)

**Goals:**
- Create end-to-end data pull scripts
- Implement incremental update logic
- Add data quality checks

**Tasks:**
1. Create `pull_all.py` - Full data extraction script
2. Create `pull_incremental.py` - Delta updates only
3. Implement date filtering (pull only new data since last run)
4. Add data quality checks (row counts, null checks, schema validation)
5. Add metadata tracking (last pull timestamp, record counts)
6. Implement archiving logic (snapshot before overwrite)
7. Create `backfill_historical.py` for one-time historical pull
8. Add command-line arguments (date ranges, entity types)

**Deliverables:**
- `scripts/pull_all.py` working end-to-end
- Incremental update logic functional
- Data quality validation in place

---

### Phase 5: Integration with Analytics (Week 5)

**Goals:**
- Update Jupyter notebook to use API-sourced data
- Leverage new data fields (contact IDs, check-ins, etc.)
- Add new analyses enabled by richer data

**Tasks:**
1. Update `data_cleaning.ipynb` to read from `birdhaus_data/processed/`
2. Replace name-based `customer_id` with contact ID or email
3. Add guest-level analysis (attendance patterns, check-ins)
4. Add ticket-level analysis (pricing tiers, inventory)
5. Add RSVP analysis (if applicable)
6. Create visualizations for new metrics (no-show rates, repeat attendance)
7. Update `birdhaus_analysis.ipynb` with new sections
8. Update `CLAUDE.md` with API data notes

**Deliverables:**
- Jupyter notebook updated to use API data
- New analyses leveraging richer data
- Documentation updated

---

### Phase 6: Automation & Monitoring (Week 6)

**Goals:**
- Set up scheduled data pulls
- Add alerting for failures
- Create monitoring dashboard

**Tasks:**
1. Create cron job or scheduled task for daily pulls
2. Implement email/Slack alerting for failures
3. Create simple monitoring dashboard (record counts, last pull time)
4. Set up log rotation and cleanup
5. Document operational procedures (how to run, troubleshoot)
6. Create backup and disaster recovery plan
7. Set up test environment (separate API keys, test data)

**Deliverables:**
- Automated daily data pulls
- Alerting for failures
- Operational documentation

---

### Bonus: MCP Server Integration ✅ **COMPLETE**

**Status:** Completed October 18, 2025 (Not in original plan)

**Accomplished:**
- ✅ Created full MCP (Model Context Protocol) server implementation
- ✅ Exposed 9 powerful tools to Claude for data access and validation
- ✅ Integrated seamlessly with existing pipeline infrastructure
- ✅ Enables real-time API data validation and debugging
- ✅ Supports both API queries and local data access
- ✅ Created comprehensive documentation (README, QUICKSTART, INSTALLATION guides)

**MCP Server Tools Available:**
1. `query_events` - Query Wix events with filters (status, date range)
2. `get_event_details` - Get detailed event information by ID
3. `query_guests` - Query event guests/attendees with RSVP filters
4. `get_tickets` - Get ticket information by event
5. `query_contacts` - Query Wix contacts/customers
6. `get_transactions` - Get payment transactions with filters
7. `get_pipeline_status` - Get operational status and last update times
8. `query_local_data` - Access locally stored raw/processed data
9. `get_api_stats` - Get API usage statistics and rate limit info

**Benefits:**
- Real-time validation of data extraction
- Natural language queries for debugging
- Direct comparison between API and local data
- Immediate feedback on pipeline health
- No additional API calls needed (uses existing client)

---

## Data Schema Mapping

### Events Schema

**API Response → DataFrame Mapping:**

| API Field | DataFrame Column | Type | Notes |
|-----------|-----------------|------|-------|
| `id` | `event_id` | str | Unique event identifier |
| `title` | `title` | str | Event name |
| `status` | `status` | str | PUBLISHED, DRAFT, CANCELED, SCHEDULED |
| `scheduling.config.startDate` | `start_date` | datetime | Event start timestamp |
| `scheduling.config.endDate` | `end_date` | datetime | Event end timestamp |
| `location.name` | `location` | str | Venue name |
| `location.type` | `location_type` | str | VENUE or TBD |
| `registration.status` | `registration_status` | str | OPEN, CLOSED, OPEN_EXTERNAL |
| `registration.ticketsSettings.tickets` | `ticket_count` | int | Number of ticket types |
| `dashboard.status` | `dashboard_status` | str | Computed status |
| *(computed)* | `year` | int | Extracted from start_date |
| *(computed)* | `month` | int | Extracted from start_date |
| *(computed)* | `day_of_week` | str | Monday-Sunday |
| *(computed)* | `is_weekend` | bool | Saturday or Sunday |

---

### Guests Schema

**API Response → DataFrame Mapping:**

| API Field | DataFrame Column | Type | Notes |
|-----------|-----------------|------|-------|
| `id` | `guest_id` | str | Unique guest identifier |
| `eventId` | `event_id` | str | Links to events table |
| `contactId` | `contact_id` | str | Links to contacts table |
| `firstName` | `first_name` | str | Guest first name |
| `lastName` | `last_name` | str | Guest last name |
| `email` | `email` | str | Guest email (if available) |
| `status` | `attendance_status` | str | ATTENDING, NOT_ATTENDING, WAITLIST |
| `checkedIn` | `checked_in` | bool | Check-in status |
| `checkInDate` | `checkin_date` | datetime | Check-in timestamp |
| `rsvpStatus` | `rsvp_status` | str | YES, NO, MAYBE |
| `member` | `is_member` | bool | Site member vs guest |
| `form` | `registration_answers` | json | Custom form responses |

---

### Tickets Schema

**API Response → DataFrame Mapping:**

| API Field | DataFrame Column | Type | Notes |
|-----------|-----------------|------|-------|
| `ticketNumber` | `ticket_number` | str | Unique ticket identifier |
| `eventId` | `event_id` | str | Links to events table |
| `orderId` | `order_id` | str | Links to transactions |
| `ticketDefinitionId` | `ticket_type_id` | str | Ticket pricing tier |
| `name` | `ticket_name` | str | Ticket type name |
| `price` | `price` | float | Ticket price |
| `currency` | `currency` | str | CAD, USD, etc. |
| `status` | `ticket_status` | str | ISSUED, CANCELLED, REFUNDED |
| `checkIn.checkedIn` | `checked_in` | bool | Check-in status |
| `checkIn.created` | `checkin_date` | datetime | Check-in timestamp |
| `assignee.contactId` | `contact_id` | str | Ticket holder contact ID |

---

### Contacts Schema

**API Response → DataFrame Mapping:**

| API Field | DataFrame Column | Type | Notes |
|-----------|-----------------|------|-------|
| `id` | `contact_id` | str | Unique contact identifier |
| `info.name.first` | `first_name` | str | First name |
| `info.name.last` | `last_name` | str | Last name |
| `info.emails[0].email` | `email` | str | Primary email |
| `info.phones[0].phone` | `phone` | str | Primary phone |
| `info.addresses[0].*` | `address_*` | str | Street, city, province, postal |
| `primaryInfo.email` | `primary_email` | str | Fallback email field |
| `primaryInfo.phone` | `primary_phone` | str | Fallback phone field |
| `createdDate` | `created_date` | datetime | Contact creation |
| `lastActivity.activityDate` | `last_activity` | datetime | Last interaction |
| `extendedFields` | *(custom)* | varies | Custom contact fields |

**PII Handling Note:**
- Email, phone, address are **sensitive PII**
- Must be stored securely (encrypted storage or restricted access)
- Privacy compliance (PIPEDA in Canada, GDPR if EU customers)
- Consider anonymization for non-essential analytics

---

### Transactions Schema

**API Response → DataFrame Mapping:**

| API Field | DataFrame Column | Type | Notes |
|-----------|-----------------|------|-------|
| `id` | `transaction_id` | str | Unique transaction ID |
| `orderId` | `order_id` | str | Links to order |
| `eventId` | `event_id` | str | Links to event |
| `paymentMethod` | `payment_method` | str | CREDIT_CARD, PAYPAL, etc. |
| `status` | `transaction_status` | str | SUCCESSFUL, PENDING, FAILED |
| `amount.amount` | `amount` | float | Transaction amount |
| `amount.currency` | `currency` | str | CAD, USD, etc. |
| `refund.amount` | `refund_amount` | float | Refunded amount (if any) |
| `created` | `payment_date` | datetime | Transaction timestamp |
| `providerTransactionId` | `provider_transaction_id` | str | External payment ID |

---

## Privacy & Security Considerations

### PII Data Handling

**Current State:**
- Dashboard exports have PII removed (no email, phone, address)
- Name-based customer identification to avoid PII exposure

**Future State with API:**
- API provides full PII (email, phone, address)
- **Must handle responsibly!**

**Security Measures:**

1. **Credentials Management**
   - API keys stored in `.env` (gitignored)
   - Never commit credentials to version control
   - Use environment variables in production
   - Rotate API keys periodically

2. **Data Storage**
   - Raw data with PII: Restricted access, encrypted at rest
   - Processed data: Consider anonymization or pseudonymization
   - Analytics data: Use contact IDs instead of emails where possible

3. **Access Control**
   - Limit who can run data pipeline scripts
   - Restrict access to `birdhaus_data/raw/` folder
   - Audit logs for data access

4. **Privacy Compliance**
   - **PIPEDA** (Canada): Obtain consent, limit collection, protect data
   - **GDPR** (if EU customers): Right to erasure, data portability
   - Document what PII is collected and why
   - Implement data retention policies

5. **Anonymization for Analytics**
   - Use hashed contact IDs for analysis where names aren't needed
   - Aggregate data where possible (avoid individual-level exports)
   - Remove PII from visualizations and reports

**Recommendation:**
- Store full PII in `birdhaus_data/raw/` (restricted access)
- Create anonymized version in `birdhaus_data/processed/` for analytics
- Use contact_id (UUID) as identifier, drop email/phone from processed CSVs
- Only retrieve PII when specifically needed (e.g., marketing campaigns)

---

## Testing Strategy

### Unit Tests

**Test API Client:**
- Authentication headers set correctly
- Rate limiting respected
- Retry logic on failures
- Pagination handling

```python
import pytest
from unittest.mock import Mock, patch
from wix_api.client import WixAPIClient

def test_authentication_headers():
    client = WixAPIClient(
        api_key="test_key",
        account_id="test_account",
        site_id="test_site"
    )
    assert client.session.headers["Authorization"] == "test_key"
    assert client.session.headers["wix-account-id"] == "test_account"

@patch('requests.Session.request')
def test_rate_limiting(mock_request):
    # Simulate rapid requests, verify rate limit enforced
    pass

@patch('requests.Session.request')
def test_retry_on_failure(mock_request):
    # Simulate 500 error, verify retry with exponential backoff
    mock_request.side_effect = [
        Mock(status_code=500),
        Mock(status_code=500),
        Mock(status_code=200, json=lambda: {"events": []})
    ]
    client = WixAPIClient.from_env()
    result = client.query_events()
    assert mock_request.call_count == 3
```

**Test Endpoint Wrappers:**
- Events, Guests, Tickets, Contacts, Transactions
- Pagination handling
- Filter/query parameter construction
- Response parsing

**Test Transformers:**
- Raw JSON → DataFrame conversion
- Date parsing
- Nested field extraction
- Derived feature creation
- Schema validation

---

### Integration Tests

**Test End-to-End Pipeline:**
- Full data pull from API
- Data saved to correct locations
- Processed data matches expected schema
- Logging and error handling work

```python
def test_full_pipeline():
    # Run pull_all.py script
    # Verify files created in birdhaus_data/
    # Verify record counts match expectations
    # Verify no errors in logs
    pass
```

**Test with Mock API:**
- Use `responses` or `pytest-httpx` to mock Wix API
- Simulate different response scenarios (success, errors, pagination)
- Verify pipeline handles all cases

---

### Data Quality Tests

**Automated Checks:**
- Row count thresholds (warn if drops >10% from previous pull)
- Null value checks (critical fields shouldn't be null)
- Schema validation (column names, data types)
- Referential integrity (event_id in guests matches events table)
- Date range validation (no future dates in historical data)

```python
def validate_data_quality(df: pd.DataFrame, entity_type: str):
    """Run data quality checks on DataFrame"""
    checks = []

    # Check for nulls in critical fields
    if entity_type == "events":
        critical_fields = ["event_id", "title", "start_date"]
        for field in critical_fields:
            null_count = df[field].isnull().sum()
            checks.append({"field": field, "null_count": null_count, "passed": null_count == 0})

    # Check row count
    previous_count = get_previous_row_count(entity_type)
    current_count = len(df)
    pct_change = (current_count - previous_count) / previous_count if previous_count > 0 else 0
    checks.append({
        "check": "row_count",
        "previous": previous_count,
        "current": current_count,
        "change_pct": pct_change,
        "passed": abs(pct_change) < 0.1  # Warn if >10% change
    })

    # Log results
    for check in checks:
        if not check.get("passed", True):
            logger.warning(f"Data quality check failed: {check}")

    return all(c.get("passed", True) for c in checks)
```

---

## Dependencies

### Pipeline Requirements

**Core Dependencies (Updated October 2025):**
```
# API Client
requests>=2.32.0          # HTTP requests (security fixes in 2.32+ series)
pyrate-limiter>=3.9.0     # Rate limiting (actively maintained, replaces ratelimit)
tenacity>=8.2.0           # Retry logic

# Data Processing
pandas>=2.0.0             # DataFrames (current: 2.3.3)
numpy>=2.0.0              # Numerical operations (⚠️ breaking changes from 1.x)
pydantic>=2.0.0           # Data validation (current: 2.13.x)

# Utilities
python-dotenv>=1.0.0      # Environment variables
pyyaml>=6.0               # Config files
```

**⚠️ Important Notes:**

- **NumPy 2.0+**: Breaking changes from NumPy 1.x (released June 2024). If you encounter compatibility issues, use `numpy>=1.26.4` (last 1.x version)
- **pyrate-limiter**: Replaces deprecated `ratelimit` package. More actively maintained with modern features
- **requests 2.32+**: Contains important security fixes from August 2025

**Optional/Development:**
```
# Testing
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.11.0
responses>=0.23.0         # Mock HTTP responses

# Logging & Monitoring
structlog>=23.1.0         # Structured logging (current: 25.4.0)

# Type Checking
mypy>=1.4.0
```

### Analytics Requirements (Existing - Updated October 2025)

```
# Data Analysis
pandas>=2.0.0             # Current: 2.3.3
numpy>=2.0.0              # ⚠️ Updated from 1.24.0 (use >=1.26.4 if compatibility issues)

# Visualization
matplotlib>=3.7.0
seaborn>=0.12.0

# Jupyter
jupyter>=1.0.0
ipywidgets>=8.0.0

# File I/O
openpyxl>=3.1.0           # Excel support
```

**Note:** If upgrading from NumPy 1.x to 2.x causes compatibility issues with existing analysis notebooks, you can use `numpy>=1.26.4` as an interim solution. NumPy 2.0+ includes breaking changes but better performance and modern Python support.

---

## Open Questions & Decisions Needed

### 1. Authentication Details
- **Question:** What type of API credentials does Birdhaus Wix account have?
- **Options:** API Key, OAuth token, or need to register app?
- **Action:** User needs to obtain Wix API credentials (see: https://dev.wix.com/docs/build-apps/get-started/authentication)

### 2. RSVP Events
- **Question:** Are there legitimate free RSVP events to track, or are all events ticketed?
- **Current assumption:** All RSVPs are platform artifacts, filtered out
- **If legitimate RSVPs exist:** Need to implement RSVP analysis section

### 3. Data Retention
- **Question:** How long should historical data be retained?
- **Options:**
  - Keep all raw data indefinitely (storage cost)
  - Archive after N months (reduced storage)
  - Delete after retention period (compliance)
- **Recommendation:** Keep raw data for 2 years, archive older data

### 4. PII Data Policy
- **Question:** Who needs access to PII (email, phone, address)?
- **Use cases:**
  - Marketing campaigns (need email)
  - Customer support (need phone)
  - Analytics (only need contact_id)
- **Recommendation:** Separate PII access from analytics access

### 5. Data Pull Frequency
- **Question:** How often should data be pulled?
- **Options:**
  - Real-time (webhooks, complex)
  - Daily (scheduled, recommended)
  - Weekly (manual, simple)
- **Recommendation:** Daily automated pull at off-peak hours (e.g., 3 AM)

### 6. Production vs Development Data
- **Question:** Should we set up separate API keys for testing?
- **Recommendation:** Yes, use test Wix site/account for development

### 7. Data Format for Storage
- **Question:** CSV or Parquet for processed data?
- **CSV Pros:** Human-readable, existing workflow compatible
- **Parquet Pros:** Faster reads, smaller files, preserves types
- **Recommendation:** Save both (CSV for compatibility, Parquet for performance)

### 8. Error Handling on Pipeline Failure
- **Question:** What happens if daily pull fails?
- **Options:**
  - Retry automatically (recommended)
  - Alert admin and wait for manual intervention
  - Continue with stale data
- **Recommendation:** Retry 3 times, then alert admin, use previous day's data

---

## Success Metrics

### Pipeline Success Criteria

**Week 1-2 (Foundation):**
- ✅ API client successfully authenticates
- ✅ Can retrieve sample data from at least one endpoint
- ✅ Logging and error handling functional

**Week 3-4 (Core Implementation):**
- ✅ All 6 endpoint wrappers implemented (events, guests, tickets, contacts, transactions, RSVPs)
- ✅ Pagination working for large datasets (>100 records)
- ✅ Data saved to `birdhaus_data/raw/` and `processed/`

**Week 5-6 (Integration & Automation):**
- ✅ Jupyter notebook updated to use API data
- ✅ New analyses leveraging richer data (check-ins, contact IDs)
- ✅ Automated daily pulls running successfully
- ✅ Documentation complete and up-to-date

### Business Impact Metrics

**Operational Efficiency:**
- ⏱️ Time to pull data: Manual (30 min) → Automated (5 min)
- 🔄 Data freshness: Static snapshots → Daily updates
- 🧹 Manual effort: Weekly exports → Zero manual intervention

**Data Quality:**
- 🎯 Customer identification accuracy: Name-based (~80%) → Contact ID (99%+)
- 📊 Data completeness: Summary-level → Individual records
- 🔗 Data linkage: Manual joins → Automated relationships

**Analytics Capability:**
- 📈 New metrics enabled: Check-in rates, repeat attendance, pricing tier analysis
- 👥 Customer insights: Attendance patterns, no-show rates, LTV by segment
- 🎫 Operational insights: Ticket inventory, sell-out prediction, refund patterns

---

## Next Steps

### Immediate Actions (Before Starting Implementation)

1. **Obtain Wix API Credentials**
   - Register for Wix Developer account (if not already done)
   - Create API key or OAuth app
   - Document account ID, site ID, API key
   - Test credentials with simple API call (e.g., GET /v1/events)

2. **Clarify Open Questions**
   - Decide on RSVP event handling
   - Define PII access policy
   - Choose data pull frequency
   - Set up test environment (separate Wix site or test API keys)

3. **Set Up Development Environment**
   - Create `birdhaus_data_pipeline/` project structure
   - Initialize git repository
   - Set up virtual environment
   - Install initial dependencies

4. **Review & Approve Plan**
   - Review this document with stakeholders
   - Confirm scope and timeline
   - Adjust priorities if needed

### Implementation Start

Once credentials and decisions are in place:
1. Begin **Phase 1: Foundation** (Week 1)
2. Create branch: `feature/wix-api-pipeline`
3. Follow roadmap week by week
4. Regular check-ins to review progress

---

## References & Resources

### Wix API Documentation
- **Main API Docs:** https://dev.wix.com/docs/rest
- **Events API:** https://dev.wix.com/docs/rest/business-solutions/events/wix-events/event
- **Event Guests API:** https://dev.wix.com/docs/rest/business-solutions/events/event-guests
- **Tickets API:** https://dev.wix.com/api/rest/wix-events/wix-events/tickets
- **Contacts API:** https://dev.wix.com/docs/rest/crm/members-contacts/contacts/introduction
- **Order Transactions API:** https://dev.wix.com/docs/rest/business-solutions/e-commerce/order-transactions/introduction
- **Authentication Guide:** https://dev.wix.com/docs/build-apps/get-started/authentication

### Python Libraries
- **requests:** https://requests.readthedocs.io/
- **tenacity (retry):** https://tenacity.readthedocs.io/
- **ratelimit:** https://pypi.org/project/ratelimit/
- **pydantic:** https://docs.pydantic.dev/
- **pandas:** https://pandas.pydata.org/docs/

### Project Documentation
- **CLAUDE.md:** Current project instructions and data structure
- **PROJECT_ANALYSIS.md:** Comprehensive project overview
- **birdhaus_analysis.ipynb:** Current analytics implementation

---

## Appendix: Sample API Calls

### Example: Query Events (V3 API)

**Request:**
```http
POST https://www.wixapis.com/v3/events/query
Authorization: <API_KEY>
wix-account-id: <ACCOUNT_ID>
wix-site-id: <SITE_ID>
Content-Type: application/json

{
  "query": {
    "filter": {
      "status": ["PUBLISHED"],
      "scheduling.config.startDate": {
        "$gte": "2025-01-01T00:00:00Z"
      }
    },
    "sort": [{"fieldName": "scheduling.config.startDate", "order": "ASC"}],
    "paging": {"limit": 100}
  }
}
```

**Response:**
```json
{
  "events": [
    {
      "id": "event-123",
      "slug": "shibari-basics-workshop",
      "title": "Shibari Basics Workshop",
      "description": "Learn fundamental shibari techniques in this hands-on workshop",
      "status": "PUBLISHED",
      "scheduling": {
        "config": {
          "startDate": "2025-02-15T19:00:00Z",
          "endDate": "2025-02-15T22:00:00Z",
          "timeZoneId": "America/Toronto"
        }
      },
      "location": {
        "name": "Birdhaus Studio",
        "type": "VENUE",
        "address": {
          "city": "Toronto",
          "subdivision": "ON",
          "country": "CA"
        }
      },
      "registration": {
        "status": "OPEN",
        "type": "TICKETING",
        "initialType": "TICKETING",
        "ticketsSettings": {
          "tickets": [
            {
              "id": "ticket-type-1",
              "name": "General Admission",
              "price": {
                "amount": "75.00",
                "currency": "CAD"
              }
            }
          ]
        }
      }
    }
  ],
  "pagingMetadata": {
    "count": 1,
    "offset": 0,
    "total": 1,
    "hasNext": false
  }
}
```

---

### Example: Query Event Guests (V2 API)

**Request:**
```http
POST https://www.wixapis.com/events-guests/v2/guests/query
Authorization: <API_KEY>
wix-account-id: <ACCOUNT_ID>
wix-site-id: <SITE_ID>
Content-Type: application/json

{
  "query": {
    "fieldsets": ["GUEST_DETAILS"],
    "filter": {
      "eventId": "event-123",
      "status": ["ATTENDING"]
    },
    "sort": [{"fieldName": "createdDate", "order": "ASC"}],
    "paging": {"limit": 100, "offset": 0}
  }
}
```

**Note:** The `guestDetails` or `GUEST_DETAILS` fieldset must be included to retrieve full guest information.

**Response:**
```json
{
  "guests": [
    {
      "id": "guest-456",
      "eventId": "event-123",
      "contactId": "contact-789",
      "guestDetails": {
        "firstName": "Jane",
        "lastName": "Doe",
        "email": "jane@example.com"
      },
      "status": "ATTENDING",
      "checkedIn": true,
      "checkInDate": "2025-02-15T19:05:00Z",
      "rsvpStatus": "YES",
      "member": true,
      "createdDate": "2025-01-15T10:30:00Z"
    }
  ],
  "pagingMetadata": {
    "count": 1,
    "offset": 0,
    "total": 1,
    "hasNext": false
  }
}
```

---

### Example: Query Contacts (V4 API - Current)

**Request:**
```http
POST https://www.wixapis.com/v4/contacts/query
Authorization: <API_KEY>
wix-account-id: <ACCOUNT_ID>
wix-site-id: <SITE_ID>
Content-Type: application/json

{
  "query": {
    "filter": {
      "lastActivity.activityDate": {
        "$gte": "2025-01-01T00:00:00Z"
      }
    },
    "paging": {"limit": 100, "offset": 0}
  }
}
```

**Response:**
```json
{
  "contacts": [
    {
      "id": "contact-789",
      "revision": 5,
      "info": {
        "name": {
          "first": "Jane",
          "last": "Doe"
        },
        "emails": [
          {
            "email": "jane@example.com",
            "tag": "MAIN"
          }
        ],
        "phones": [
          {
            "phone": "+14165551234",
            "tag": "MOBILE"
          }
        ],
        "addresses": [
          {
            "street": "123 Main St",
            "city": "Toronto",
            "subdivision": "ON",
            "postalCode": "M5V 2T6",
            "country": "CA"
          }
        ]
      },
      "createdDate": "2024-05-10T14:30:00Z",
      "lastActivity": {
        "activityDate": "2025-02-15T19:05:00Z"
      }
    }
  ],
  "pagingMetadata": {
    "count": 1,
    "offset": 0,
    "total": 1,
    "cursors": {
      "next": null,
      "prev": null
    }
  }
}
```

**Note:** Contacts V4 includes a `revision` number that increments with each update. Use this for optimistic concurrency control when updating contacts.

---

## Document Metadata

**Version:** 3.0
**Created:** 2025-10-18
**Last Updated:** 2025-10-18 (Evening)
**Author:** Claude (AI Assistant)
**Purpose:** Implementation plan for Wix API data pipeline
**Status:** Phase 2 Complete - Core Implementation Working

### Changelog

**Version 2.0 (2025-10-18):**

- ✅ Updated all API endpoints to current versions (Events V3, Guests V2, RSVP V2)
- ✅ Added critical API version deprecation warnings
- ✅ Updated dependency versions (NumPy 2.0+, requests 2.32+)
- ✅ Replaced deprecated ratelimit with pyrate-limiter
- ✅ Updated code examples with correct V3/V2 endpoint structures
- ✅ Added fieldset requirements for Guest API V2
- ✅ Enhanced authentication section with permission scopes
- ✅ Updated sample API calls in appendix with V3/V2 formats
- ✅ Added package compatibility notes and warnings

**Version 1.0 (2025-10-18):**

- Initial implementation plan created

### Next Review

After obtaining Wix API credentials and stakeholder approval. Test all endpoints with live API calls to verify exact paths and authentication requirements.

---

**End of Document**
