# Birdhaus Data Pipeline

A Python ETL pipeline that extracts event, guest, contact, and sales data from Wix REST APIs, transforms nested JSON into flat CSV files, and outputs Excel-compatible spreadsheets for analysis.

Built for **Birdhaus Shibari Studio** to replace manual Wix CSV exports with automated, repeatable data pulls.

## Architecture

```
Wix REST APIs              Python Pipeline                              Output
 ──────────────           ────────────────                              ──────
 Events API V3  ──┐
 Guests API V2  ──┤
 RSVP API V2    ──┤  Extract     Transform        Load        Join
 Tickets V1     ──┤──────────►──────────────►──────────►─────────────►  Timestamped
 Contacts V4    ──┤  API calls   Flatten JSON     Silver CSV  Gold CSV  CSV files
 Members V1     ──┤  Pagination  Date conversion  per entity  attendance (UTF-8 BOM)
 Orders API V1  ──┤  Rate limit  Enrichment       (UTF-8 BOM) _fact
 Transactions V1──┤  Retry       Field selection
 Cashier Pay v2 ──┤
 Forms V4       ──┤
 Coupons V2     ──┤
 Automations V2 ──┘
```

### Module Structure

```
src/
├── wix_api/                    # API client and endpoint wrappers
│   ├── client.py               # Core HTTP client (auth, rate limiting, retries)
│   ├── events.py               # Events API V3 wrapper
│   ├── guests.py               # Event Guests API V2 wrapper
│   ├── rsvp.py                 # RSVP API V2 wrapper
│   ├── tickets.py              # Tickets API V1 wrapper (sold tickets)
│   ├── ticket_definitions.py   # Ticket Definitions API V3 wrapper (templates)
│   ├── contacts.py             # Contacts API V4 wrapper
│   ├── members.py              # Members API V1 wrapper
│   ├── orders.py               # Event Orders API V1 wrapper
│   ├── transactions.py         # eCommerce Transactions API V1 wrapper
│   ├── payments.py             # Cashier Payments API wrapper (dashboard "Payments" data)
│   ├── forms.py                # Form Submissions API V4 wrapper
│   ├── coupons.py              # Coupons API V2 wrapper
│   └── automations.py          # Automations API V2 wrapper
│
├── transformers/               # Data transformation layer
│   ├── base.py                 # Shared utilities (encoding, dates, CSV export)
│   ├── events.py               # Events transformer (~55 output fields)
│   ├── guests.py               # Guests transformer (~31 fields + enrichment)
│   ├── rsvps.py                # RSVPs transformer
│   ├── tickets.py              # Tickets transformer (joins with ticket definitions)
│   ├── ticket_definitions.py   # Ticket Definitions transformer
│   ├── contacts.py             # Contacts transformer (~36 fields)
│   ├── members.py              # Members transformer
│   ├── order_summaries.py      # Sales summary transformer (12 fields)
│   ├── event_orders.py         # Individual orders transformer (~38 fields)
│   ├── transactions.py         # eCommerce transactions transformer
│   ├── payments.py             # Cashier transactions transformer (per-payment grain)
│   ├── form_submissions.py     # Form submissions (wide + long format)
│   ├── coupons.py              # Coupons transformer
│   ├── automations.py          # Automations transformer
│   └── attendance_fact.py      # Gold layer: one row per attendee, all dims joined
│
└── utils/                      # Infrastructure
    ├── config.py               # Pydantic-validated configuration
    ├── logger.py               # Dual file/console logging
    ├── pagination.py           # Offset-based and cursor-based pagination
    ├── raw_storage.py          # Bronze layer: date-partitioned JSON dumps
    ├── manifest.py             # Per-run observability manifest
    └── retry.py                # Retry decorators, rate limiting, exceptions
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

Extracts all entity types and writes both a raw bronze layer (JSON) and a flattened silver layer (CSV):

```bash
python scripts/pull_all.py

# With custom output directories
python scripts/pull_all.py --output-dir /path/to/silver --raw-dir /path/to/bronze

# Or via CLI entry point (after pip install -e .)
wix-pull-all
```

All files from a single run share the same `<timestamp>` for snapshot identification.

#### Bronze layer (raw JSON, date-partitioned)

Unmodified API responses, useful for re-deriving views, schema-drift insurance, and querying with DuckDB / Spark / pandas:

```
data/raw/
├── events/year=2026/month=02/day=11/snapshot_20260211_143022.json
├── members/year=2026/month=02/day=11/snapshot_20260211_143022.json
├── payments/year=2026/month=02/day=11/snapshot_20260211_143022.json
├── tickets/year=2026/month=02/day=11/snapshot_20260211_143022.json
├── ticket_definitions/year=.../snapshot_20260211_143022.json
└── ... (one folder per entity)
```

Example query with DuckDB:

```sql
SELECT name, soldCount FROM 'data/raw/ticket_definitions/year=2026/**/*.json';
```

#### Silver layer (flat CSVs)

Excel-friendly, transformed CSVs:

```
data/processed/
├── events_20260211_143022.csv
├── rsvp_events_20260211_143022.csv
├── contacts_20260211_143022.csv
├── members_20260211_143022.csv
├── guests_20260211_143022.csv                (RSVP-event guests filtered out)
├── tickets_20260211_143022.csv               (joined with ticket definitions)
├── ticket_definitions_20260211_143022.csv    (NEW)
├── order_summaries_20260211_143022.csv
├── event_orders_20260211_143022.csv
├── payments_20260211_143022.csv              (cashier transactions; one row per payment)
├── form_submissions_20260211_143022.csv      (wide format - one row per submission)
├── form_submissions_long_20260211_143022.csv (long format - one row per field)
├── coupons_20260211_143022.csv
├── automations_20260211_143022.csv
├── attendance_fact_20260211_143022.csv       (GOLD: one row per attendee, all dims joined)
├── payments_fact_20260211_143022.csv         (GOLD: one row per payment, event/member dims joined)
└── manifest_20260211_143022.json             (per-run observability)
```

#### Run manifest

Each run produces a `manifest_<timestamp>.json` with row counts, file paths, durations, and errors per entity. Useful for monitoring data freshness, detecting silent failures, and tracking schema growth.

```json
{
  "snapshot_id": "20260211_143022",
  "duration_ms": 716000,
  "total_records": 1842,
  "summary": {"successful": 13, "failed": 0, "skipped": 0, "total_entities": 13},
  "entities": {
    "events": {"status": "success", "row_count": 47, "raw_path": "...", "csv_path": "...", "duration_ms": 4200},
    "members": {"status": "success", "row_count": 247, ...}
  }
}
```

### Upcoming Events Only

Pulls only upcoming ticketing events (used by the GitHub Actions weekly schedule):

```bash
python scripts/pull_upcoming_events.py
```

### Execution Flow

`pull_all.py` follows this sequence. Every step writes a raw JSON dump to the bronze layer first, then transforms to silver CSV, then records stats in the run manifest:

1. Initialize `WixAPIClient` and `RunManifest`
2. Extract all events via `EventsAPI.get_all_events()`, split into TICKETING and RSVP
3. Extract all contacts via `ContactsAPI.get_all_contacts()`
4. Extract all site members via `MembersAPI.get_all_members()`
5. Extract all guests via `GuestsAPI.get_all_guests()`, filtering out guests tied to RSVP events for the silver CSV (raw bronze JSON keeps the full unfiltered response)
6. Extract ticket definitions (templates) via `TicketDefinitionsAPI.get_all_ticket_definitions(fieldsets=["SALES_DETAILS"])`
7. Extract all sold tickets via `TicketsAPI.get_all_tickets()` and join with definitions for `def_fee_type`, `def_sale_status`, `def_sold_count`
8. Extract order summaries per event via `OrdersAPI.get_summary_by_event()` (parallel, 10 workers, ticketing events only)
9. Extract all event orders via `OrdersAPI.get_all_orders()`
10. Extract every cashier payment via `PaymentsAPI.get_all_transactions(include_refunds=True)` — this is the same data Wix's dashboard exports as the manual `Payments` CSV
11. Extract form submissions across all namespaces via `FormsAPI.get_all_submissions_for_namespaces()` -- saves both wide and long format CSVs
12. Extract all coupons (active + expired) via `CouponsAPI.get_all_coupons()`
13. Extract automation configurations via `AutomationsAPI.get_all_automations()`
14. **Build the gold `attendance_fact` view** by joining all in-memory transformed silver dicts (`AttendanceFactTransformer.build()`) — no extra API calls
15. **Build the gold `payments_fact` view** by joining payments + event_orders + events + contacts + members + order_summaries (`PaymentsFactTransformer.build()`) — no extra API calls
16. Save the run manifest to `data/processed/manifest_<timestamp>.json`

**Note on RSVPs:** Per-event RSVP attendance fetching (`RSVPAPI.get_all_rsvps_for_event()` looped over each RSVP event) is intentionally disabled in `pull_all.py` because it's slow at scale. The RSVP events themselves are still captured in `rsvp_events_<ts>.csv`. The `RSVPAPI` wrapper and `extract_rsvps()` helper remain available — re-enable the call in `main()` if RSVP attendance data is needed.

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
- **Categories**: `category_names` (comma-joined) and `category_count`. We deliberately do not emit a `primary_category` because the API order of `categories[]` is not editorially significant and would be a misleading signal.

### Contacts

Source: Contacts API V4 (`GET /contacts/v4/contacts`)

Transforms contact records into ~36 columns. Contacts contain PII (emails, phones) -- handle according to privacy regulations.

- **Email handling**: Extracts primary email, email tag, and email count from the nested emails array
- **Member info**: Flattens site membership details (signup date, role, verification status)
- **Extended fields**: Extracts display names and membership status from Wix extended fields

### Guests

Source: Event Guests API V2 (`POST /events/v2/guests/query`)

Transforms guest records into ~31 columns. Requires the `GUEST_DETAILS` fieldset for full data.

The silver CSV (`guests_<ts>.csv`) excludes guests tied to RSVP-type events (these aren't useful since RSVP attendance fetching is disabled for performance). The bronze raw JSON (`data/raw/guests/...`) keeps the **full unfiltered API response** for completeness and re-derivation.

- **Guest types**: RSVP, BUYER, or TICKET_HOLDER (RSVP types still appear if their event is TICKETING, e.g. waitlist)
- **Ticket flattening**: Ticket arrays are flattened to `ticket_count`, `ticket_names`, `ticket_numbers`, plus a `primary_ticket_*` set
- **Contact enrichment**: The Guests API returns minimal name/email data. The pipeline joins guests with contacts via `contactId` to populate `first_name`, `last_name`, `email`, and `phone` fields.
- **Order status (`order_status`, `rsvp_status`, `additional_details_archived`)**: extracted from `additionalDetails`. `order_status` carries Wix's authoritative `PAID` / `FREE` / `UNKNOW_ORDER_STATUS` (sic) flag — this is the only place the API exposes the comp-vs-paid signal, including discount-coded and console-marked-free tickets. Null when Wix did not populate the block.
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

### Payments (cashier transactions)

Source: Wix Cashier Payments API (`GET /payments/api/merchant/v2/transactions`).

This is the **same data** Wix exports when you click *Dashboard > Sales >
Payments > Export CSV*. It's **not** the eCommerce Orders API and **not**
the Events Orders API — it's the financial-transactions layer underneath
both, recording every Stripe / PayPal / in-person charge attempt.

Why we keep it as its own entity:
- Per-payment grain (one row per Stripe `pi_xxx`), so refunds, chargebacks,
  and declined attempts each get their own row. This is finer than the
  per-order grain in `event_orders_<ts>.csv`.
- Carries the buyer's billing name + email even when `event_orders` returns
  anonymized buyer fields, so we can join real attendee identity onto orders
  Wix has anonymized.
- Includes the `wix_app_order_id` field, which equals
  `event_orders.order_number` — that's the join key for any downstream gold
  view that needs to enrich payments with event title, category, etc.

Validated against the manual `payments (14).csv` export on 2026-04-22:

- 2675 / 2675 Stripe `Provider Payment ID`s match (100% overlap)
- 2628 / 2628 dashboard `Order ID`s match (100% overlap)
- Status counts match exactly (`Refunded` 69, `Declined` 68, `Chargeback` 1,
  `Partially refunded` 1) and the API surfaces +48 `BUYER_CANCELED` rows
  that the dashboard CSV silently filters out.

Schema (~71 columns), grouped:

| Group | Columns |
|---|---|
| Grain / IDs | `transaction_id`, `provider_transaction_id` (Stripe `pi_xxx`), `order_id` (cashier UUID), `wix_app_order_id` (events `order_number` join key), `wix_app_buyer_id`, `app_id`, `app_name` |
| Money | `amount`, `currency`, `platform_fee` (Wix's processing fee), `service_fee_line_amount` (the `SERVICE_FEE` line item), `net_amount` (= amount - platform_fee - succeeded refunds), `tax`, `shipping`, `discount` |
| Status | `status` (raw enum), `transaction_status` (friendly label matching the dashboard CSV), `transaction_type` (SALE/RECURRING), `is_refundable`, `failure_code` |
| Provider / method | `payment_provider`, `payment_provider_friendly`, `payment_method`, `payment_method_type`, `provider_dashboard_link` |
| Card detail | `card_network`, `card_last_four`, `card_masked`, `card_expiry`, `card_holder_name`, `card_bin`, `installments` |
| Refunds | `refund_count`, `refund_succeeded_count`, `refund_total_amount`, `refund_status`, `refund_type`, `refund_reason`, `refund_provider_id`, `refund_date`, `refund_time` |
| Buyer / billing | `billing_first_name`, `billing_last_name`, `billing_full_name`, `billing_email`, `billing_phone`, `billing_company`, `billing_address`, `billing_city`, `billing_state`, `billing_zip`, `billing_country` |
| Shipping | `shipping_first_name`, `shipping_last_name`, `shipping_email`, `shipping_city`, `shipping_country` |
| Order line items | `product_name`, `product_count`, `total_quantity`, `primary_product_name`, `primary_product_unit_price`, `primary_product_quantity` |
| Subscription | `subscription_status`, `subscription_frequency`, `subscription_interval`, `subscription_billing_cycles` |
| Timing | `payment_date`, `payment_time`, `payment_datetime` |

### Site Members

Source: Members API V1 (`GET /members/v1/members`)

Users who have registered accounts on the site. Every Member is also a Contact, but not all Contacts are Members. Pulling both gives you the join to identify which customers have site logins.

- Profile info (nickname, slug, photo, title)
- Login email, status, privacy/activity status
- Contact ID link for joining with Contacts data
- Login and signup dates

### Tickets

Source: Tickets API V1 (`GET /events/v1/tickets`), joined with Ticket Definitions V3 for fee/sale metadata.

Individual sold ticket records, distinct from guest records and order summaries.

- Ticket number, order number, event ID, ticket definition ID
- Guest/buyer details (name, email, member/contact ID)
- Pricing (`price_value`, `price_currency`)
- Status (`order_status`, `archived`, `order_archived`, `free`)
- Check-in details (`checked_in`, `check_in_date`, `check_in_time`, `check_in_url`)
- Custom registration form responses (flattened as `form_*` columns)
- Joined columns from Ticket Definition: `def_pricing_type`, `def_fee_type`, `def_sale_status`, `def_sold_count`, `def_sold_out`

### Ticket Definitions

Source: Ticket Definitions API V3 (`POST /events/v3/ticket-definitions/query` with `SALES_DETAILS` fieldset)

Reusable templates for ticket types available for an event. Sold Tickets reference these by ID.

- Definition ID, event ID, name, description
- Pricing method (`pricing_type`: STANDARD/DONATION, `fixed_price_value`, `guest_price_value`)
- Multiple pricing tiers (`pricing_options_count`, `pricing_option_names`)
- Fee handling (`fee_type`: FEE_INCLUDED / FEE_ADDED_AT_CHECKOUT / NO_FEE)
- Sale period (`sale_start_date`, `sale_end_date`, `sale_status`)
- Inventory (`initial_limit`, `actual_limit`, `sold_count`, `unsold_count`, `sold_out`, `reserved_count`)

### RSVPs (currently disabled)

Source: RSVP API V2 (`POST /events/v2/rsvps/query`)

RSVP attendance data for RSVP-type events. **This extraction is currently disabled in `pull_all.py`** because it requires looping per-event (one paginated call per RSVP event), which is slow at scale. The RSVP events themselves are still captured in `rsvp_events_<ts>.csv`.

The `RSVPAPI` wrapper and `extract_rsvps()` function in `scripts/pull_all.py` remain available — re-enable the call in `main()` to start producing `rsvps_<ts>.csv` again. Output would include:

- RSVP status (YES, NO, WAITING, PENDING)
- Check-in status, guest names, additional guests
- Contact/member ID for joining
- Custom form responses from registration

### Form Submissions

Source: Form Submissions API V4 (`POST /v4/submissions/namespace/query`)

Submissions from Wix Forms, event registration forms, and other form-based apps. Dynamic fields vary per form, so we save **two CSVs**:

**Wide format** (`form_submissions_<ts>.csv`): one row per submission with dynamic `field_*` columns. Convenient in Excel, but the schema grows whenever a new form is added.

- Submission ID, form ID, namespace
- Submitter contact/member ID, status, seen flag
- Dynamic form fields (flattened as `field_*` columns)

**Long format** (`form_submissions_long_<ts>.csv`): one row per (submission, field) pair with a stable schema that doesn't grow:

- `submission_id`, `form_id`, `namespace`, `submitter_contact_id`, `submitter_member_id`, `status`, `created_date`
- `field_name`, `field_value`

Use long format for cross-snapshot analytics (DuckDB / Spark / pandas pivots); use wide format for ad-hoc Excel browsing.

### Coupons

Source: Coupons API V2 (`POST /stores/v2/coupons/query`)

Discount coupons applied to events, bookings, or store purchases.

- Coupon code, name, active/expired status
- Discount type (money off, percent off, fixed price, free shipping)
- Scope (which app/namespace the coupon applies to)
- Usage limits and current usage count
- Start and expiration dates

### Automations

Source: Automations API V2 (`POST /v2/automations/query`)

Automation configurations showing triggers and actions. Returns config only, not execution history.

- Automation name, status, origin
- Trigger key and app ID
- Action keys and count
- Created/updated dates

### Attendance Fact (gold layer)

Source: derived — joins the silver layer in memory at the end of `pull_all.py`.
No extra API calls.

`attendance_fact_<timestamp>.csv` is a denormalized analytics table with **one
row per attendee** designed to answer questions like *"who shows up at events,
what categories are most popular, and what did each attendee pay (or get for
free as a membership benefit)?"* without writing any joins.

**Grain rules** (validated against the 2026-04-22 snapshot):

- Wix's Guest API returns one `BUYER` row per order PLUS one `TICKET_HOLDER`
  row per ticket. A person buying one ticket for themselves shows up twice.
- This view keeps one row per actual attendee:
  - All `TICKET_HOLDER` rows are kept (the canonical attendee record)
  - All `RSVP` rows are kept
  - `BUYER` rows are dropped when a `TICKET_HOLDER` exists for the same order
  - `BUYER`-only orders (no `TICKET_HOLDER`) are skipped entirely — empirically
    these correlate with failed/cancelled checkouts (empty `payment.method`,
    only `ARCHIVE` available action). They're logged at `WARNING` level so we
    can revisit once the per-event order extraction returns real status fields.
- Buyer context is preserved on the surviving rows via derived columns
  (`was_buyer`, `buyer_contact_id`, `tickets_in_order`).

**Schema (~50 columns)**:

| Group | Columns |
|---|---|
| Grain | `guest_id`, `event_id`, `contact_id`, `order_number`, `ticket_number`, `ticket_definition_id` |
| Attendee role | `guest_type`, `was_buyer`, `buyer_contact_id`, `tickets_in_order`, `attendance_status`, `order_status`, `checked_in`, `check_in_date`, `check_in_time` |
| Event dims | `event_title`, `event_slug`, `event_status`, `registration_type`, `category_names`, `category_count`, `start_date`, `start_time`, `start_datetime`, `day_of_week`, `is_weekend`, `location_name`, `location_city`, `event_lowest_price`, `event_highest_price`, `event_currency` |
| Pricing | `ticket_name`, `price_value`, `price_currency`, `price_source`, `paid_bucket`, `free`, `def_pricing_type`, `def_fee_type`, `def_sale_status` |
| Identity | `first_name`, `last_name`, `full_name`, `email`, `phone`, `is_member`, `member_id`, `member_signup_date`, `member_last_login_date` |
| Timing | `registered_date`, `registered_time` |

`order_status` is the canonical paid-vs-free flag from Wix
(`guests[].additionalDetails.orderStatus`): `PAID`, `FREE`,
`UNKNOW_ORDER_STATUS` (Wix's spelling), or null. When `null`, Wix didn't
populate the additional-details block (older records or rows the API
anonymized) — treat as unknown, not as paid.

`price_source` documents how `price_value` was resolved per row:
`order_status` (Wix said FREE, so $0), `ticket` (per-ticket data — only
once the per-event tickets API is fixed), `ticket_definition` (template
fixed price), `event_average` (fallback from order_summaries), or
`unknown`.

`paid_bucket` is a derived band for filtering: `Free`, `0-25`, `25-50`,
`50-100`, `100+`, or `Unknown`. The `free` flag is the membership-benefit
signal — resolution order: `order_status == 'FREE'` → ticket-level free →
definition free → derived (`price_value == 0`).

#### Why a snapshot can have fewer events than `events_*.csv`

`attendance_fact` has one row per *attendee*, so events that have no
attendees yet (upcoming with zero sales, or canceled events) produce zero
rows and are absent from the gold table by design. To see those, look at
`events_<timestamp>.csv` (always one row per event) or
`order_summaries_<timestamp>.csv` (always one row per ticketing event,
including events with `has_sales=False`).

**Example questions this enables (single-table, no joins):**

```sql
-- Most popular event categories
SELECT split_part(category_names, ',', 1) AS primary_cat, COUNT(*) AS attendees
FROM attendance_fact GROUP BY 1 ORDER BY 2 DESC;

-- Comp / membership benefit usage (uses Wix's authoritative FREE flag)
SELECT is_member, free, COUNT(*) FROM attendance_fact
WHERE order_status IS NOT NULL  -- exclude rows where Wix didn't populate the field
GROUP BY 1, 2 ORDER BY 1, 2;

-- Repeat attendees (people who came to >= 3 events)
SELECT email, COUNT(DISTINCT event_id) AS events_attended
FROM attendance_fact GROUP BY email HAVING COUNT(DISTINCT event_id) >= 3
ORDER BY 2 DESC;

-- Who showed up at play parties this year
SELECT full_name, email, event_title, start_date, paid_bucket
FROM attendance_fact
WHERE category_names LIKE '%play%' AND start_date >= '2026-01-01';
```

### Payments Fact (gold layer)

Source: derived — joins the silver layer in memory at the end of `pull_all.py`. No extra API calls.

`payments_fact_<timestamp>.csv` is the financial counterpart to
`attendance_fact`. Where `attendance_fact` answers "*who showed up*",
`payments_fact` answers "*who paid, how much, when, for which event,
and through which payment method*" — without writing any joins.

Grain: one row per Wix cashier transaction (sales, refunds, declines,
chargebacks, cancelled checkouts). This is the same grain as the
silver `payments_<ts>.csv` — gold just denormalizes the event /
contact / member dimensions onto every row.

**Join key chain:**

```
payments.wix_app_order_id (e.g. "3088-CBPT-789")
    -> event_orders.order_number
        -> event_orders.event_id          -> events.event_id
        -> event_orders.contact_id        -> contacts.contact_id
                                          -> members.contact_id
                                          -> order_summaries.event_id
```

Validated against the 2026-04-22 snapshot: **2733 / 2735 rows
fully_enriched (99.93%)**. The 2 unmatched rows are test/manual
transactions with no `wix_app_order_id` — `enrichment_status` documents
the join outcome on every row so analysts can filter to clean data
or audit the gaps.

**Schema (~69 columns), grouped:**

| Group | Columns |
|---|---|
| Grain / IDs | `transaction_id`, `provider_transaction_id`, `order_id`, `wix_app_order_id`, `event_id`, `contact_id`, `member_id`, `enrichment_status` |
| Money | `amount`, `currency`, `platform_fee`, `net_amount`, `tax`, `discount`, `amount_bucket` |
| Status | `status` (raw), `transaction_status` (friendly), `transaction_type`, `is_refundable`, `failure_code` |
| Provider / method | `payment_provider`, `payment_method`, `card_network`, `card_last_four` |
| Refunds | `refund_count`, `refund_succeeded_count`, `refund_total_amount`, `refund_status`, `refund_reason`, `refund_date` |
| Order line items | `product_name`, `product_count`, `total_quantity` |
| Event dims | `event_title`, `event_slug`, `event_status`, `registration_type`, `category_names`, `category_count`, `event_start_date`, `event_start_time`, `event_start_datetime`, `event_day_of_week`, `event_is_weekend`, `location_name`, `location_city`, `event_lowest_price`, `event_highest_price` |
| Event-level revenue | `event_total_orders`, `event_total_tickets`, `event_total_sales`, `event_avg_ticket_price` |
| Order context | `order_channel`, `order_status`, `order_tickets_quantity`, `order_ticket_names` |
| Buyer / member | `first_name`, `last_name`, `full_name`, `email`, `phone`, `is_member`, `member_signup_date`, `member_last_login_date`, `billing_city`, `billing_country` |
| Timing | `payment_date`, `payment_time`, `payment_datetime` |

**`enrichment_status` values** — populated for every row so you can
audit join outcomes:

- `fully_enriched` — payment, order, event, and contact all matched
- `no_order_id` — cashier txn has no `wix_app_order_id` (manual / test)
- `order_not_found` — order_id refers to an order not in this snapshot
- `event_not_found` — order joined but its event is not in this snapshot
- `no_contact_link` — order joined but had no contact_id

**Example questions this enables (single-table, no joins):**

```sql
-- Top 10 events by gross revenue (excluding refunds/declines)
SELECT event_title, SUM(amount) AS revenue, COUNT(*) AS payment_count
FROM payments_fact WHERE transaction_status = 'Successful'
GROUP BY event_title ORDER BY revenue DESC LIMIT 10;

-- Which categories pull the most $ and bodies?
SELECT category_names, COUNT(*) AS payments, SUM(amount) AS gross
FROM payments_fact WHERE transaction_status = 'Successful'
GROUP BY category_names ORDER BY gross DESC;

-- Member vs non-member spend
SELECT is_member, COUNT(*) AS payments, SUM(amount) AS gross,
       AVG(amount) AS avg_ticket
FROM payments_fact WHERE transaction_status = 'Successful'
GROUP BY is_member;

-- Repeat buyers for a given series
SELECT email, COUNT(DISTINCT event_id) AS events, SUM(amount) AS lifetime_value
FROM payments_fact
WHERE transaction_status = 'Successful' AND category_names LIKE '%rope%'
GROUP BY email HAVING COUNT(DISTINCT event_id) >= 3
ORDER BY lifetime_value DESC;

-- Refund / chargeback monitoring per event
SELECT event_title, transaction_status, COUNT(*) AS rows,
       SUM(refund_total_amount) AS refunded
FROM payments_fact
WHERE transaction_status IN ('Refunded','Partially refunded','Chargeback')
GROUP BY event_title, transaction_status ORDER BY refunded DESC;

-- Day-of-week revenue patterns
SELECT event_day_of_week, COUNT(*) AS payments, SUM(amount) AS gross
FROM payments_fact WHERE transaction_status = 'Successful'
GROUP BY event_day_of_week
ORDER BY CASE event_day_of_week
  WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3
  WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6
  WHEN 'Sunday' THEN 7 END;
```

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
| `rebuild_silver_views.py` | Re-emit silver CSVs from existing bronze JSON (no API calls). Use after a transformer schema change so silver matches the new transformer logic. |
| `build_gold_views.py` | Rebuild the gold `attendance_fact` CSV from existing silver CSVs (no API calls). Useful for backfilling old snapshots or iterating on gold-layer schema. |
| `analyze_data_coverage.py` | Shows raw vs. transformed field counts |
| `show_new_fields.py` | Documents calculated/enriched fields added by transformers |
| `check_event_dates.py` | Validates event date data |
| `generate_views.py` | Generates data views |
| `clean_csv.py` | CSV post-processing (column removal, filtering, merging) |

```bash
# Re-emit silver CSVs (e.g. after a transformer schema change)
python scripts/rebuild_silver_views.py            # latest snapshot
python scripts/rebuild_silver_views.py --all      # every snapshot on disk

# Build gold view for the latest snapshot
python scripts/build_gold_views.py

# Build gold for a specific snapshot, or for every snapshot on disk
python scripts/build_gold_views.py --snapshot 20260422_205516
python scripts/build_gold_views.py --all
```

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
