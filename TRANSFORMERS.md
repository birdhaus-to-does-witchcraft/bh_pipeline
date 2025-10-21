# Data Transformers

**Purpose:** Transform raw Wix API responses into clean, flattened CSV files for analysis

**Status:** ✅ All 4 transformers complete (Events, Contacts, Guests, Transactions)

---

## Overview

Transformers convert nested JSON from Wix APIs into flat, analysis-ready DataFrames with:
- Flattened nested structures → simple columns
- Date/time separation (YYYY-MM-DD date + HH:MM:SS time)
- UTF-8 BOM encoding (Excel-compatible)
- Consistent field naming
- Smart fallback logic for missing data

---

## Architecture

### Base Transformer Class

**File:** `src/transformers/base.py`

All transformers inherit from `BaseTransformer` which provides:

#### 1. Encoding Management
- **Default:** UTF-8 with BOM (Excel recognizes UTF-8)
- **Option:** ASCII mode (replaces special characters: – → -, ' → ')

#### 2. Character Cleaning
Automatically handles special Unicode:
- EN DASH (–) → hyphen (-)
- SMART QUOTES ('') → regular quotes ('')
- ELLIPSIS (…) → three periods (...)

#### 3. Date/Time Extraction
```python
# Input: "2025-10-18T16:00:00Z"
date, time = BaseTransformer.extract_date_and_time(datetime_str)
# Output: ("2025-10-18", "16:00:00")
```

#### 4. Price Flattening
```python
# Input: {"amount": "75.00", "currency": "CAD"}
# Output: price=75.00, currency="CAD"
```

#### 5. Address Extraction
```python
# Input: Complex address object
# Output: formatted_address, city, country, subdivision,
#         postal_code, street_number, street_name, etc.
```

---

## Available Transformers

### 1. Events Transformer ✅

**File:** `src/transformers/events.py`
**Output Fields:** 53 clean fields (from 116 raw API fields)

**Key Features:**
- Flattened categories (nested → comma-separated string)
- Separated date and time fields
- **Day of week extraction** (based on actual calendar date)
- Detailed address breakdown
- Image dimensions
- Smart description fallback (tries rich text → detailed → short)

**Usage:**
```python
from transformers.events import EventsTransformer

# Transform and save
raw_events = events_api.get_all_events()
EventsTransformer.save_to_csv(raw_events, 'events.csv')
```

**Output Sample:**
```csv
event_id,title,start_date,start_time,day_of_week,day_of_week_num,is_weekend,category_names,location_postal_code
abc123,Shibari Workshop,2025-10-12,16:00:00,Sunday,0,true,"Rope, Education",M6K 1L5
```

---

### 2. Contacts Transformer ✅

**File:** `src/transformers/contacts.py`
**Output Fields:** 36 fields

**Key Features:**
- Name fields (first, last, full)
- Email information (primary, count, subscription status)
- Member information (site member status)
- Profile details (nickname, role, privacy)
- Signup/created dates (separated into date + time)

**Usage:**
```python
from transformers.contacts import ContactsTransformer

contacts = contacts_api.get_all_contacts()
ContactsTransformer.save_to_csv(contacts, 'contacts.csv')
```

**Output Sample:**
```csv
contact_id,full_name,email,is_member,signup_date,signup_time
guid123,Jane Doe,jane@example.com,true,2024-05-10,14:30:00
```

---

### 3. Guests Transformer ✅

**File:** `src/transformers/guests.py`
**Output Fields:** ~40 fields

**Key Features:**
- Guest types (RSVP, BUYER, TICKET_HOLDER)
- Attendance/check-in status
- Order numbers (payment identifiers)
- Ticket information
- **Guest name enrichment** (joins with Contacts API)

**Important:** Guests API doesn't return names directly - must enrich with Contacts data!

**Usage:**
```python
from transformers.guests import GuestsTransformer

# Fetch both guests and contacts
guests = guests_api.get_all_guests()
contacts = contacts_api.get_all_contacts()

# Transform and enrich
transformed_guests = GuestsTransformer.transform_guests(guests)
enriched_guests = GuestsTransformer.enrich_with_contact_data(
    transformed_guests, contacts
)

# Save
BaseTransformer.save_to_csv(enriched_guests, 'guests.csv')
```

**Output Sample:**
```csv
guest_id,event_id,full_name,email,order_number,guest_type,checked_in
guid1,evt123,Michelle Cooper,mcoop@gmail.com,2Z4T-98RG,BUYER,true
```

---

### 4. Transactions Transformer ✅

**File:** `src/transformers/transactions.py`
**Output Fields:** ~70 fields

**Key Features:**
- Order information (ID, number, checkout ID)
- Buyer information (name, email, phone)
- Billing and shipping addresses
- Payment and fulfillment status
- Order totals (subtotal, tax, shipping, discounts)
- Line items (products, quantities, prices)
- Discount codes/coupons
- Transaction details

**Usage:**
```python
from transformers.transactions import TransactionsTransformer

# Get orders
orders = client.post('/ecom/v1/orders/search', json={
    'search': {'paging': {'limit': 100}}
}).get('orders', [])

# Optionally get transactions
from collections import defaultdict
transactions_by_order = defaultdict(list)
# ... fetch transactions ...

# Transform
TransactionsTransformer.save_to_csv(
    orders, 'transactions.csv',
    transactions_by_order=dict(transactions_by_order)
)
```

---

## Common Patterns

### Encoding Options

**UTF-8 with BOM (default - recommended):**
```python
EventsTransformer.save_to_csv(events, 'events.csv')
# or explicitly:
EventsTransformer.save_to_csv(events, 'events.csv', encoding='utf-8-sig')
```
✅ Works perfectly in Excel
✅ Preserves all special characters (–, ', etc.)

**ASCII mode:**
```python
EventsTransformer.save_to_csv(events, 'events.csv', encoding='ascii')
```
✅ Pure ASCII compatibility
⚠️ Special characters replaced: – → -, ' → '

### Date/Time Fields

All transformers split dates into two fields:

```csv
start_date,start_time,timezone
2025-10-12,16:00:00,America/Toronto
```

**Benefits:**
```python
# Filter by date
june_events = df[df['start_date'].str.startswith('2025-06')]

# Filter by time
evening = df[df['start_time'] >= '18:00:00']

# Calculate duration
df['duration'] = pd.to_datetime(df['end_time']) - pd.to_datetime(df['start_time'])
```

---

## Testing

### Test All Transformers

```bash
python scripts/test_all_transformers.py
```

**Features:**
- Tests all 4 transformers in one run
- Shows configuration (Site ID, Account ID)
- Saves timestamped CSV files
- Verifies UTF-8 BOM encoding
- Provides success summary

**Output:**
```
1. TESTING EVENTS TRANSFORMER
   ✓ Retrieved 111 events
   ✓ Saved to: events_20251018_182956.csv

2. TESTING CONTACTS TRANSFORMER
   ✓ Retrieved 1363 contacts
   ✓ Saved to: contacts_20251018_182956.csv

...
```

### Individual Transformer Tests

```bash
# Events
python scripts/test_transformer.py

# Contacts
python scripts/test_contacts_transformer.py

# Encoding comparison (UTF-8 BOM vs ASCII)
python scripts/test_encoding_fix.py
```

---

## Data Quality

### Field Statistics (Events Transformer Example)

**Raw API Response:** 116 fields
**Transformed Output:** 50 fields
**Reduction:** 57% fewer columns, 100% more readable

**Field Breakdown:**
- Basic Info: 5 fields
- Categories: 3 fields (flattened from nested JSON)
- Dates & Times: 7 fields (clean dates + full datetimes)
- Location: 13 fields (including detailed address breakdown)
- Registration: 2 fields
- Pricing: 4 fields
- Images: 4 fields (including dimensions)
- Metadata: 5 fields
- Settings: 3 fields
- Descriptions: 4 fields (with smart fallback)

---

## Guest Name Enrichment

**Why Needed:** Wix Guests API V2 doesn't return names/emails in guest records

**Solution:** Join with Contacts API using `contactId`

**Implementation:**
```python
def enrich_with_contact_data(
    transformed_guests: List[Dict],
    contacts: List[Dict]
) -> List[Dict]:
    """
    Enrich guest data with contact information.

    Creates a contactId → {name, email, phone} lookup,
    then populates guest records with contact data.
    """
    # Build lookup
    contact_lookup = {}
    for contact in contacts:
        contact_id = contact.get('id')
        info = contact.get('info', {})
        name = info.get('name', {})
        ...
        contact_lookup[contact_id] = {
            'first_name': name.get('first'),
            'last_name': name.get('last'),
            'email': ...,
            'phone': ...
        }

    # Enrich guests
    for guest in transformed_guests:
        contact_id = guest.get('contact_id')
        if contact_id in contact_lookup:
            guest.update(contact_lookup[contact_id])
            guest['full_name'] = f"{guest['first_name']} {guest['last_name']}"

    return transformed_guests
```

**Result:**
- **Before enrichment:** 0% of guests had names
- **After enrichment:** 100% of guests have names

---

## Usage Examples

### Analysis-Ready Data

```python
import pandas as pd

# Load transformed data
df = pd.read_csv('events.csv')

# Date filtering (clean YYYY-MM-DD format)
upcoming = df[df['start_date'] > '2025-06-01']

# Group by month
df['month'] = df['start_date'].str[:7]  # YYYY-MM
monthly_counts = df.groupby('month').size()

# Location analysis
by_postal_code = df.groupby('location_postal_code').size()

# Category analysis
rope_events = df[df['category_names'].str.contains('Rope')]

# Day of week analysis
sunday_classes = df[df['day_of_week'] == 'Sunday']
day_counts = df['day_of_week'].value_counts()  # Which days are most popular?
weekend_events = df[df['is_weekend'] == True]

# Sort by day of week
df_sorted = df.sort_values(['day_of_week_num', 'start_time'])

# Image quality check
low_res = df[(df['main_image_width'] < 1000) |
             (df['main_image_height'] < 1000)]
```

---

## Design Principles

1. **Inheritance** - All transformers extend `BaseTransformer`
2. **Consistency** - Same method names and patterns across transformers
3. **UTF-8 BOM** - Default encoding for Excel compatibility
4. **Flat Structure** - Nested data → flat columns
5. **Date Separation** - Dates and times in separate fields
6. **Null Handling** - Graceful handling of missing data
7. **Smart Fallbacks** - Try multiple fields for best available data

---

## Production Usage

### Switch to Production Site

Update `.env` with production credentials:
```bash
WIX_SITE_ID=your-production-site-id
WIX_ACCOUNT_ID=your-production-account-id
WIX_API_KEY=your-production-api-key
```

Run comprehensive test:
```bash
python scripts/test_all_transformers.py
```

Verify output in `data/processed/`:
- CSV files open correctly in Excel
- Special characters display properly
- All expected fields are present
- Guest data is populated (production only)

---

## Troubleshooting

### Encoding Issues in Excel

**Problem:** Seeing `â€"` or `â€™` instead of dashes/quotes

**Solution:** Use UTF-8 with BOM (default)
```python
EventsTransformer.save_to_csv(events, 'events.csv')  # Already UTF-8 BOM
```

### Missing Guest Names

**Problem:** Guest CSV has empty name fields

**Solution:** Must enrich with Contacts API
```python
# Don't forget enrichment step!
enriched_guests = GuestsTransformer.enrich_with_contact_data(
    transformed_guests, contacts
)
```

### Date Formatting

**Problem:** Want different date format

**Solution:** Dates are in ISO format (YYYY-MM-DD) for sorting/filtering. Format in analysis:
```python
df['formatted_date'] = pd.to_datetime(df['start_date']).dt.strftime('%B %d, %Y')
```

---

For historical transformer development notes, see `docs/archive/`:
- `TRANSFORMERS_PROGRESS.md` - Development history
- `TRANSFORMER_UPDATES.md` - Events transformer changes
- `FINAL_TRANSFORMER_SUMMARY.md` - Final implementation summary
