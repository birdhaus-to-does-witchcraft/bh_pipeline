# Pricing Data Discovery - Ticket Definitions API

**Date:** October 18, 2025
**Status:** ✅ PRICING DATA FOUND

---

## Summary

**Ticket pricing data IS available** through the Wix Events Ticket Definitions API.

**Endpoint:** `GET /events/v1/ticket-definitions`

**Data Available:**
- Ticket type names
- Prices (amount + currency)
- Event linkage
- Sale status
- Free/paid status

---

## API Endpoint Details

### Ticket Definitions API

**Endpoint:** `GET https://www.wixapis.com/events/v1/ticket-definitions`

**Parameters:**
- `limit`: Number of definitions per request (tested with 100)

**Response Structure:**
```json
{
  "metaData": {},
  "definitions": [...],
  "facets": {}
}
```

**Note:** Response uses `definitions` (not `ticketDefinitions`)

---

## Ticket Definition Object

### Complete Structure (Observed)

```json
{
  "id": "53de6534-6479-4b85-8f4f-522ddf46f4fe",
  "name": "Class plus open space",
  "eventId": "0e320707-bac2-43b8-ac39-e8371b4e2cb4",
  "price": {
    "amount": "35.00",
    "currency": "CAD",
    "value": "35.00"
  },
  "pricing": {
    "fixedPrice": {
      "amount": "35.00",
      "currency": "CAD",
      "value": "35.00"
    },
    "pricingType": "STANDARD"
  },
  "free": false,
  "description": "This ticket includes a spot in our workshop...",
  "orderIndex": 0,
  "limitPerCheckout": 0,
  "saleStatus": "SALE_ENDED",
  "state": [],
  "policy": "",
  "wixFeeConfig": {...}
}
```

### Key Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | string | Ticket definition GUID | "53de6534-6479..." |
| `name` | string | Ticket type name | "Class plus open space" |
| `eventId` | string | Linked event GUID | "0e320707-bac2..." |
| `price.amount` | string | Ticket price | "35.00" |
| `price.currency` | string | Currency code | "CAD" |
| `free` | boolean | Is free ticket | false |
| `saleStatus` | string | Sale status | "SALE_ENDED" |
| `description` | string | Ticket description | "This ticket includes..." |

---

## Test Results

### Total Available
- **Ticket Definitions Retrieved:** 100 (first page)
- **API Response:** ✅ HTTP 200
- **Pricing Data:** ✅ Fully populated

### Sample Data

**Event:** 0e320707-bac2-43b8-ac39-e8371b4e2cb4

**Ticket Types:**
1. "Class plus open space" - $35.00 CAD
2. "Open space *only*" - $20.00 CAD

**Guests for Event:**
- Total: 2 buyers
- Guest type: BUYER (2), TICKET_HOLDER (0)

---

## Data Relationships

### What Can Be Linked

```
Ticket Definitions (100+)
  ├─ eventId → Events (111)
  └─ price.amount → Pricing data

Events (111)
  └─ eventId → Guests (2,871)

Guests (2,871)
  ├─ eventId → Events
  └─ orderNumber → Orders (1,354)
```

### What CANNOT Be Linked (Data Gap)

**Missing Link:** Guest/Order → Ticket Definition

- Guests have `tickets` array → EMPTY
- Orders have `tickets` array → EMPTY
- No `ticketDefinitionId` in Guest object
- No `ticketDefinitionId` in Order object

**Impact:** Cannot determine which specific ticket type a buyer purchased.

---

## Pricing Calculation Options

### Option 1: Event-Level Aggregate

**Method:** Count buyers per event × ticket prices

**Example:**
- Event has 2 ticket types: $35 and $20
- Event has 2 buyers
- **Cannot determine:** Which buyer bought which ticket

**Possible:** Calculate min/max revenue range
- Min: 2 × $20 = $40
- Max: 2 × $35 = $70
- Actual: Unknown

### Option 2: Single Ticket Type Events

**Method:** If event has only 1 ticket type, price is known

**Example:**
- Event has 1 ticket type: $35
- Event has 5 buyers
- Revenue: 5 × $35 = $175 ✅ Accurate

**Limitation:** Only works for single-ticket events

### Option 3: Average Price

**Method:** Calculate average of all ticket prices for event

**Example:**
- Event has 2 tickets: $35 and $20
- Average: $27.50
- Estimated revenue: 2 × $27.50 = $55

**Limitation:** Assumes equal distribution

---

## Current API Coverage

### What We Have

✅ **Ticket Prices** (Ticket Definitions API)
- All ticket types
- Prices per type
- Linked to events

✅ **Order Count** (Orders API)
- 1,354 orders total
- Order numbers
- Event linkage
- Transaction IDs

✅ **Buyer Count** (Guests API)
- 2,871 guests total
- Guest types (BUYER/TICKET_HOLDER/RSVP)
- Event linkage
- Order numbers

### What's Missing

❌ **Individual Ticket Purchases**
- Which ticket type each buyer purchased
- Actual price paid per order
- Ticket quantity per type

**Root Cause:**
- `tickets` array in Orders → Empty
- `tickets` array in Guests → Empty
- No ticket definition ID linkage

---

## Comparison with Dashboard Data

### Dashboard Shows (Expected)

- Order number
- Buyer name
- Event name
- Ticket type purchased ← NOT in API
- Quantity
- Price paid ← NOT in API
- Total amount ← NOT in API

### API Provides (Actual)

- Order number ✅
- Buyer name ✅ (via Contacts)
- Event name ✅ (via Events)
- Ticket type purchased ❌ (missing link)
- Quantity ⚠️ (ticketsQuantity shows 0)
- Price paid ❌ (not in Order object)
- Total amount ❌ (not in Order object)

**Coverage:** ~50% of dashboard data

---

## Recommended Approach

### Immediate: Use What's Available

**Data Sources:**
1. **Ticket Definitions** - Get all ticket prices by event
2. **Orders** - Get order counts by event
3. **Guests** - Get buyer counts by event (more granular than orders)

**Export Structure:**

```csv
event_id, event_name, ticket_type, ticket_price, currency, buyer_count_for_event
```

**Limitations:**
- Cannot show price per individual order
- Cannot calculate exact revenue (only estimates)
- Can only show ticket prices available, not which were purchased

### Future: Investigate Alternative Endpoints

**Potential Sources:**

1. **Reservations API**
   - Check if reservation objects link tickets to purchases
   - Search for `/events/v1/reservations` endpoint

2. **Checkout API**
   - Check if checkout response includes ticket details
   - Search for `/events/v1/checkout` endpoint

3. **Summary/Analytics API**
   - Check if there's a sales summary endpoint
   - Search for `/events/v1/summary` or `/events/v1/analytics`

4. **Wix Data Collections**
   - Dashboard may use Wix Data API
   - Collections: "Events/Orders", "Events/Tickets"
   - Endpoint: `/wix-data/v2/collections/data/query`

---

## Next Steps

### 1. Create Ticket Definitions API Wrapper

**File:** `src/wix_api/ticket_definitions.py`

**Methods:**
- `list_ticket_definitions()` - Get definitions with pagination
- `get_ticket_definition()` - Get single definition
- `get_definitions_by_event()` - Filter by event ID
- `get_all_definitions()` - Auto-paginate all

### 2. Create Ticket Definitions Transformer

**File:** `src/transformers/ticket_definitions.py`

**Output Fields:**
- ticket_definition_id
- ticket_name
- event_id
- price_amount
- price_currency
- is_free
- sale_status
- description

### 3. Add Event-Level Revenue Estimates

**Method:**
- Join Ticket Definitions with Guests
- Calculate min/max/avg revenue per event
- Flag accuracy level (exact/estimated/range)

### 4. Research Additional Endpoints

**Search for:**
- Wix Data Collections API
- Events sales summary endpoint
- Reservation details endpoint
- Alternative ticket purchase tracking

---

## API Endpoints Summary

### Working - Full Data

```
GET /events/v1/ticket-definitions
├─ Returns: 100+ definitions (first page)
├─ Pricing: ✅ Complete (amount + currency)
├─ Event Link: ✅ eventId provided
└─ Pagination: Uses metaData object
```

### Working - Partial Data

```
GET /events/v1/orders
├─ Returns: 1,354 orders
├─ Pricing: ❌ No price fields
├─ Tickets: ❌ tickets array empty
└─ Links: ✅ eventId, orderNumber, contactId

POST /events/v2/guests/query
├─ Returns: 2,871 guests
├─ Pricing: ❌ No price fields
├─ Tickets: ❌ tickets array empty
└─ Links: ✅ eventId, orderNumber, contactId

POST /events/v3/events/query
├─ Returns: 111 events
├─ Pricing: ❌ No ticket prices
└─ Links: ✅ eventId
```

---

## Documentation References

**Ticket Definitions API:**
- https://dev.wix.com/api/rest/wix-events/wix-events/ticket-definitions/list-ticket-definitions
- https://dev.wix.com/docs/rest/business-solutions/events/ticket-definitions-v1/list-ticket-definitions

**API Notes:**
- V3 version exists but V1 tested successfully
- Default fields include: id, price, free, name, limitPerCheckout, orderIndex, eventId
- Pricing types: STANDARD, dynamic pricing options available

---

**Last Updated:** October 18, 2025
**API Tested:** Production with increased permissions
**Key Finding:** Pricing data exists but individual purchase linkage missing
