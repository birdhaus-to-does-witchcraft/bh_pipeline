# Payment and Order Data - API Endpoints

**Date:** October 18, 2025
**Tested Against:** Production Wix site with increased API permissions

---

## Summary

**Working Endpoints for Payment/Order Data:**
1. ✅ `GET /events/v1/orders` - Lists all orders across all events
2. ✅ `GET /events/v1/events/{eventId}/orders/{orderNumber}` - Gets single order by event + order number
3. ✅ Guests API (`POST /events/v2/guests/query`) - Provides order numbers for cross-reference

**Non-Working Endpoints:**
1. ❌ `GET /events/v1/tickets` - Returns 1,630 tickets but all data fields are empty
2. ❌ `POST /ecom/v1/orders/search` - Returns 0 results (event orders not in eCommerce system)

---

## API Endpoint Details

### 1. List All Orders

**Endpoint:** `GET https://www.wixapis.com/events/v1/orders`

**Parameters:**
- `limit` (optional): Number of orders per page (tested with 3, 5, 100)
- `offset` (optional): Pagination offset

**Response Structure:**
```json
{
  "total": 1354,
  "offset": 0,
  "limit": 100,
  "orders": [...],
  "facets": {}
}
```

**Pagination Format:**
- Uses `total`, `offset`, `limit` (not `pagingMetadata`)
- Similar to Tickets API V1 format

**Test Results:**
- Total orders available: **1,354**
- API responds: ✅ HTTP 200
- Data populated: ⚠️ Partial

### 2. Get Single Order

**Endpoint:** `GET https://www.wixapis.com/events/v1/events/{eventId}/orders/{orderNumber}`

**Parameters:**
- `eventId` (path): Event GUID
- `orderNumber` (path): Order number (e.g., "2Z4T-98RG-RNZ")

**Response Structure:**
```json
{
  "order": {...},
  "calendarLinks": {...}
}
```

**Test Results:**
- API responds: ✅ HTTP 200
- Data populated: ⚠️ Partial

---

## Order Object Structure

Based on actual API responses from production data:

### Fields Present (Non-Empty)

| Field | Type | Example Value | Description |
|-------|------|---------------|-------------|
| `orderNumber` | string | "2XM4-WCJM-VR7" | Unique order identifier |
| `eventId` | string | "0e320707-bac2-..." | Event GUID |
| `contactId` | string | "65cb5d79-4982-..." | Contact GUID |
| `transactionId` | string | "4bdb0d65-94d1-..." | Payment transaction GUID |
| `channel` | string | "ONLINE" | Order channel |
| `status` | string | "NA_ORDER_STATUS" | Order status |
| `confirmed` | boolean | false | Confirmation status |
| `archived` | boolean | false | Archive status |
| `anonymized` | boolean | false | Anonymization status |
| `fullyCheckedIn` | boolean | false | Check-in status |
| `paymentDetails` | object | {...} | Payment transaction data |
| `availableActions` | array | ["ARCHIVE"] | Available order actions |

### Fields Present (Empty)

| Field | Type | Observed Value | Expected Content |
|-------|------|----------------|------------------|
| `firstName` | string | "" | Buyer first name |
| `lastName` | string | "" | Buyer last name |
| `fullName` | string | "" | Buyer full name |
| `email` | string | "" | Buyer email |
| `method` | string | "" | Payment method |
| `reservationId` | string | "" | Reservation ID |
| `snapshotId` | string | "" | Snapshot ID |
| `memberId` | string | "" | Member ID |
| `ticketsQuantity` | number | 0 | Number of tickets |
| `ticketsPdf` | string | "" | PDF URL |
| `tickets` | array | [] | Tickets array |
| `giftCardPaymentDetails` | array | [] | Gift card payments |

### Payment Details Object

```json
{
  "transaction": {
    "transactionId": "4bdb0d65-94d1-4052-8224-ffacd71d6316",
    "method": "creditCard",
    "scheduledAction": "UNKNOWN_ACTION"
  }
}
```

**Populated Fields:**
- `transactionId`: Matches top-level field
- `method`: Payment method (e.g., "creditCard")
- `scheduledAction`: Always "UNKNOWN_ACTION" in tested samples

---

## Data Availability Analysis

### What Works

**Relationship Data:**
- ✅ `orderNumber` - Can link orders to guests
- ✅ `eventId` - Can link orders to events
- ✅ `contactId` - Can link orders to contacts
- ✅ `transactionId` - Unique payment identifier
- ✅ `paymentDetails.transaction.method` - Payment method type

**Status Data:**
- ✅ `status` - Order status (all tested show "NA_ORDER_STATUS")
- ✅ `channel` - All tested show "ONLINE"
- ✅ `confirmed` - Boolean flags
- ✅ `archived` - Boolean flags
- ✅ `fullyCheckedIn` - Boolean flags

### What's Empty

**Buyer Information:**
- ❌ `firstName`, `lastName`, `fullName` - All empty
- ❌ `email` - Empty

**Ticket Information:**
- ❌ `tickets` - Array is empty (length 0)
- ❌ `ticketsQuantity` - Shows 0
- ❌ `ticketsPdf` - Empty string

**Financial Information:**
- ❌ No price/amount fields visible
- ❌ No currency fields visible
- ❌ No tax/fee fields visible

---

## Cross-Reference with Guests API

The Guests API provides the link between guests and orders:

**Guests API Response:**
```json
{
  "id": "000360b7-3cce-4fc8-b643-1b1c5c221cb6",
  "eventId": "e56e5bd0-c3ae-4638-99bc-ffab2aaf9c9d",
  "contactId": "abb0bfd9-54f2-42bf-b406-1e322bda6c58",
  "orderNumber": "2Z4T-98RG-RNZ",
  "guestType": "BUYER",
  "tickets": []
}
```

**Match Points:**
- Guest `orderNumber` → Order `orderNumber` ✅
- Guest `eventId` → Order `eventId` ✅
- Guest `contactId` → Order `contactId` ✅

**Note:** Guest `tickets` array is also empty (same as Order `tickets` array)

---

## Tickets API V1 Status

**Endpoint:** `GET /events/v1/tickets`

**Current Status:** Returns data structure but all fields empty

**Test Results:**
- Total tickets: **1,630**
- Response format: Valid JSON
- Data fields: All empty strings/zeros/false

**Sample Response:**
```json
{
  "ticketNumber": "",
  "orderNumber": "",
  "ticketDefinitionId": "",
  "name": "",
  "orderFullName": "",
  "guestFullName": "",
  "free": false,
  "orderStatus": "NA_ORDER_STATUS",
  "channel": "ONLINE"
}
```

**Tested with:**
- ✅ Increased API permissions
- ✅ Different fieldsets: `['FULL']`, `['DETAILS']`, `['FULL', 'DETAILS']`
- ✅ Result: No change - data still empty

---

## Comparison: Orders vs Guests vs Tickets

| Data Point | Orders API | Guests API | Tickets API |
|-----------|------------|------------|-------------|
| Total Count | 1,354 | 2,871 | 1,630 |
| Order Number | ✅ Populated | ✅ Populated | ❌ Empty |
| Event ID | ✅ Populated | ✅ Populated | ❌ Empty |
| Contact ID | ✅ Populated | ✅ Populated | ❌ Empty |
| Buyer Name | ❌ Empty | ❌ Empty* | ❌ Empty |
| Transaction ID | ✅ Populated | ❌ Not present | ❌ Empty |
| Payment Method | ✅ Populated | ❌ Not present | ❌ Empty |
| Tickets Array | ❌ Empty | ❌ Empty | N/A |
| Guest Type | ❌ Not present | ✅ Populated | ❌ Empty |

*Guests API names can be populated via Contacts enrichment

---

## Data Completeness Assessment

### Available Through API Combination

**By joining Orders + Guests + Contacts:**

✅ **Order Information:**
- Order number
- Event ID
- Transaction ID
- Payment method (type only, no amount)
- Order status
- Channel

✅ **Buyer Information:**
- Contact ID
- Name (via Contacts API)
- Email (via Contacts API)
- Phone (via Contacts API)

✅ **Guest Information:**
- Guest type (BUYER/TICKET_HOLDER/RSVP)
- Attendance status
- Purchase date/time

### Not Available Through APIs

❌ **Financial Data:**
- Order total amount
- Ticket prices
- Currency
- Taxes
- Fees
- Discounts
- Refund amounts

❌ **Ticket Details:**
- Ticket numbers
- Ticket type names
- Ticket definition IDs
- Individual ticket data

❌ **PDF/Documents:**
- Ticket PDFs
- Invoice PDFs
- Receipt URLs

---

## Recommended Data Pipeline

### Primary Data Source

**Use:** Orders API (`GET /events/v1/orders`)

**Provides:**
- 1,354 orders
- Order numbers
- Event/Contact relationships
- Transaction IDs
- Payment methods

### Enrichment Sources

1. **Guests API** - Add guest type and attendance data
   - Join on: `orderNumber`
   - Adds: `guestType`, `attendanceStatus`, `createdDate`

2. **Contacts API** - Add buyer names and emails
   - Join on: `contactId`
   - Adds: `firstName`, `lastName`, `email`, `phone`

3. **Events API** - Add event details
   - Join on: `eventId`
   - Adds: Event title, date, location, etc.

### Data Joins

```
Orders (1,354)
  ├─→ JOIN Contacts ON contactId → Get buyer name/email
  ├─→ JOIN Events ON eventId → Get event details
  └─→ JOIN Guests ON orderNumber → Get guest type + attendance
```

---

## Missing Data - Potential Sources

### For Pricing Information

**Option 1:** Ticket Definitions API
- Endpoint: May exist at `/events/v1/ticket-definitions` or `/events/v3/ticket-definitions`
- Could provide: Base ticket prices by type
- Limitation: Won't show actual paid amounts or discounts

**Option 2:** eCommerce Transactions API
- Endpoint: `GET /ecom/v1/orders/{orderId}/transactions`
- Tested: Returns 404 with event order numbers
- Conclusion: Event orders not in eCommerce system

**Option 3:** Manual Mapping
- Create lookup table: Ticket type → Price
- Source: Export from Wix dashboard or manual entry
- Limitation: Doesn't capture discounts or dynamic pricing

### For Ticket Details

Currently no working API endpoint provides:
- Individual ticket numbers
- Ticket type assignments
- Ticket-level check-in status

The `tickets` array in both Orders and Guests APIs is empty.

---

## API Endpoint Summary

### Working Endpoints

```
GET /events/v1/orders
├─ Params: limit, offset
├─ Returns: 1,354 orders
└─ Pagination: total/offset/limit format

GET /events/v1/events/{eventId}/orders/{orderNumber}
├─ Params: None (path params only)
├─ Returns: Single order + calendarLinks
└─ Requires: eventId AND orderNumber

POST /events/v2/guests/query
├─ Params: query object with fieldsets, filter, paging
├─ Returns: 2,871 guests
└─ Pagination: pagingMetadata format (no total field)

POST /contacts/v4/contacts/query
├─ Params: filter, paging
├─ Returns: 1,363 contacts
└─ Pagination: pagingMetadata format with total

POST /events/v3/events/query
├─ Params: query object with filter, paging, sort
├─ Returns: 111 events
└─ Pagination: pagingMetadata format with total
```

### Non-Working Endpoints

```
GET /events/v1/tickets
├─ Returns: 1,630 tickets
└─ Issue: All data fields empty (even with increased permissions)

POST /ecom/v1/orders/search
├─ Returns: 0 orders
└─ Issue: Event orders not in eCommerce system

POST /events/v1/orders/query
└─ Returns: 404 Not Found

GET /events/v1/events/{eventId}/orders
└─ Returns: 404 Not Found
```

---

## Next Steps

### Immediate Implementation

1. **Create Orders API Wrapper**
   - File: `src/wix_api/orders.py`
   - Methods: `list_orders()`, `get_order()`, `get_all_orders()`
   - Pagination: Use `total/offset/limit` format (same as Tickets)

2. **Create Orders Transformer**
   - File: `src/transformers/orders.py`
   - Extract: Order numbers, IDs, transaction data, payment methods
   - Join: With Contacts for names, with Events for details

3. **Add to Test Script**
   - Fetch all 1,354 orders
   - Enrich with Contacts and Events data
   - Export to CSV

### Future Investigation

1. **Ticket Definitions API**
   - Search for endpoint to get ticket pricing templates
   - May provide base prices by ticket type

2. **API Permissions**
   - Investigate why `tickets`, `firstName`, `email` fields are empty
   - May require additional permission scopes

3. **Alternative Data Sources**
   - Check if dashboard export provides financial data
   - Investigate Wix Payments or Billing APIs

---

**Last Updated:** October 18, 2025
**API Permissions:** Increased (as of test date)
**Test Environment:** Production Wix site
