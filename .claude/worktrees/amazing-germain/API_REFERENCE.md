# Wix API Reference

Technical reference for the Wix REST API endpoints used by this pipeline. All endpoint paths, methods, and parameters are documented from the actual wrapper code in `src/wix_api/`.

## Authentication

All requests include these headers (set by `WixAPIClient` in `src/wix_api/client.py`):

```
Authorization: <WIX_API_KEY>
Content-Type: application/json
Accept: application/json
wix-account-id: <WIX_ACCOUNT_ID>    (optional)
wix-site-id: <WIX_SITE_ID>          (optional)
```

The client uses `requests.Session` with connection pooling for all requests.

## Rate Limiting and Retries

### Rate Limiting

Enforced by `pyrate-limiter` (with a fallback `RateLimiter` class):

- **Default limit**: 100 requests per 60 seconds
- **429 handling**: Reads the `Retry-After` header and sleeps for the specified duration. Falls back to 60 seconds if no header is present.
- Configured via `RATE_LIMIT_MAX_CALLS` and `RATE_LIMIT_PERIOD` environment variables.

### Retry Logic

Two layers of retry protection:

1. **Connection-level** (`urllib3.Retry` on the session adapter):
   - 3 retries on connection errors
   - Exponential backoff (factor=1)
   - Retries on status codes: 500, 502, 503, 504
   - Allowed methods: HEAD, GET, OPTIONS, POST

2. **Application-level** (`tenacity` decorator on `_request()`):
   - 3 attempts (configurable via `RETRY_MAX_ATTEMPTS`)
   - Exponential backoff: 4-10 second range (configurable via `RETRY_MIN_WAIT`, `RETRY_MAX_WAIT`)
   - Retries on: `RequestException`, `Timeout`, `ConnectionError`
   - Retryable HTTP status codes: 429, 500, 502, 503, 504

### Custom Exceptions

Defined in `src/utils/retry.py`:

| Exception | Parent | Meaning |
|---|---|---|
| `APIError` | `Exception` | Base API error |
| `AuthenticationError` | `APIError` | 401 response (invalid API key) |
| `RateLimitError` | `RetryableError` | 429 response (rate limit exceeded) |
| `RetryableError` | `Exception` | Base for errors that should trigger retry |

## Pagination

The pipeline uses `paginate_query()` from `src/utils/pagination.py` -- a generic offset-based pagination helper that works across all query endpoints.

**How it works:**

1. Calls the query function with `limit` and `offset` parameters
2. Extracts items from the response using a configurable `response_key` (e.g., `"events"`, `"guests"`)
3. Checks for more pages via:
   - `pagingMetadata.total` or top-level `total` field
   - Partial page detection (fewer items than `limit` means last page)
   - `pagingMetadata.hasNext` boolean
4. Increments offset and repeats until all data is retrieved

**Per-endpoint page sizes:**

| Endpoint | Max per page | Page size used |
|---|---|---|
| Events V3 | ~100 | 100 |
| Guests V2 | 100 | 100 |
| Contacts V4 | 1,000 | 1,000 |
| Orders V1 | 400 | 400 |
| Tickets V1 | 100 | 100 |
| RSVP V2 | 100 | 100 |

---

## Events API V3

**Wrapper**: `src/wix_api/events.py` -- `EventsAPI` class
**Base path**: `/events/v3/events`
**Docs**: https://dev.wix.com/docs/rest/business-solutions/events/events-v3/introduction

### Query Events

```
POST /events/v3/events/query
```

The primary endpoint for retrieving events. Uses a POST body with a `query` wrapper object.

**Request body:**

```json
{
  "query": {
    "paging": { "limit": 100, "offset": 0 },
    "filter": { "status": ["UPCOMING"] },
    "sort": [{ "fieldName": "scheduling.config.startDate", "order": "DESC" }],
    "fieldsets": ["DETAILS", "TEXTS"]
  }
}
```

**Parameters:**
- `limit` -- Items per page (max ~100)
- `offset` -- Pagination offset
- `filter` -- Filter criteria (e.g., `{"status": ["PUBLISHED"]}`)
- `sort` -- Sort order
- `fieldsets` -- Include `"TEXTS"` for full description content in bulk queries

**Response key**: `events`

### Get Event

```
GET /events/v3/events/{eventId}
```

Returns full event details for a single event. Individual queries include complete descriptions (unlike bulk queries which may return empty description nodes).

### Get Event by Slug

```
GET /events/v3/events/by-slug/{slug}
```

### List Events by Category

```
GET /events/v3/events/by-category/{categoryId}
```

**Query params**: `limit`, `offset`

### Create Event

```
POST /events/v3/events
```

### Update Event

```
PATCH /events/v3/events/{eventId}
```

### Clone Event

```
POST /events/v3/events/{eventId}/clone
```

### Publish / Cancel Event

```
POST /events/v3/events/{eventId}/publish
POST /events/v3/events/{eventId}/cancel
```

### Bulk Cancel / Delete Events

```
POST /events/v3/events/cancel     (body: {"filter": {...}})
POST /events/v3/events/delete     (body: {"filter": {...}})
```

### Delete Event

```
DELETE /events/v3/events/{eventId}
```

### Count Events by Status

```
POST /events/v3/events/count-by-status
```

### Helper: Get All Events

`EventsAPI.get_all_events()` uses `paginate_query()` to retrieve all events across pages. Supports optional `enrich_descriptions=True` to re-fetch each event individually for complete description content (works around a Wix API quirk where bulk queries return empty description nodes).

---

## Event Guests API V2

**Wrapper**: `src/wix_api/guests.py` -- `GuestsAPI` class
**Base path**: `/events/v2/guests`
**Docs**: https://dev.wix.com/docs/rest/business-solutions/events/event-guests/introduction

### Query Guests

```
POST /events/v2/guests/query
```

**Important**: Must include `fieldsets: ["GUEST_DETAILS"]` to get full guest data (name, email, phone, check-in status). Without this fieldset, the response contains only minimal guest information.

**Request body:**

```json
{
  "query": {
    "paging": { "limit": 100, "offset": 0 },
    "filter": { "eventId": "event-123" },
    "fieldsets": ["GUEST_DETAILS"]
  }
}
```

**Response key**: `guests`

### Get Guest

```
GET /events/v2/guests/{guestId}
```

**Query params**: `fieldsets=GUEST_DETAILS`

### Guest Types

- `RSVP` -- Invited guest, no ticket necessary
- `BUYER` -- The guest who bought the tickets
- `TICKET_HOLDER` -- The guest for whom the ticket was bought

### Check-in Statuses

- `CHECKED_IN`
- `NOT_CHECKED_IN`
- `PENDING`

### Helpers

- `get_all_guests_for_event(event_id)` -- All guests for one event
- `get_all_guests()` -- All guests across all events

---

## Contacts API V4

**Wrapper**: `src/wix_api/contacts.py` -- `ContactsAPI` class
**Base path**: `/contacts/v4/contacts`
**Docs**: https://dev.wix.com/api/rest/contacts/contacts/contacts-v4

**PII Note**: Contact data contains personally identifiable information (emails, phones, addresses). Handle according to privacy regulations.

### List Contacts

```
GET /contacts/v4/contacts
```

**Query params**: `paging.limit` (max 1000), `paging.offset`

**Response key**: `contacts`

Uses GET with query parameters (not POST like Events/Guests).

### Get Contact

```
GET /contacts/v4/contacts/{contactId}
```

### Create Contact

```
POST /contacts/v4/contacts
```

Requires at least one of: name, phone, or email.

### Bulk Update Contacts

```
POST /contacts/v4/bulk/contacts/update
```

### Bulk Delete Contacts

```
POST /contacts/v4/bulk/contacts/delete
```

### Merge Contacts

```
POST /contacts/v4/contacts/merge
```

Merges source contacts into a target contact. Supports `preview: true` to preview without executing.

### Helpers

- `get_all_contacts()` -- Paginated retrieval of all contacts (1000 per page)
- `search_contacts_by_email(email)` -- Filter contacts by email address
- `search_contacts_by_phone(phone)` -- Filter contacts by phone number

---

## Event Orders API V1

**Wrapper**: `src/wix_api/orders.py` -- `OrdersAPI` class
**Base path**: `/events/v1/orders`
**Docs**: https://dev.wix.com/api/rest/wix-events/wix-events/order

This API provides two distinct capabilities: listing individual orders and retrieving sales summaries.

### List Orders

```
GET /events/v1/orders
```

**Query params**: `limit` (max 400), `offset`

Returns individual order records across all events. Uses a different pagination format than other APIs -- response includes top-level `total`, `offset`, and `limit` fields instead of `pagingMetadata`.

**Response key**: `orders`

### Get Individual Order

```
GET /events/v1/events/{eventId}/orders/{orderNumber}
```

Returns full order details including calendar links.

### Get Sales Summary

```
GET /events/v1/orders/summary
```

**Query params**: `eventId` (optional -- omit for all events)

Returns aggregate sales data:
- `total` -- Total sales amount (including fees)
- `revenue` -- Net revenue (after Wix fees)
- `totalOrders` -- Number of orders
- `totalTickets` -- Number of tickets sold

**Response key**: `sales` (array)

### Order Statuses

- `NA_ORDER_STATUS` -- Not applicable / unknown
- `INITIATED` -- Order initiated
- `PENDING` -- Payment pending
- `OFFLINE_PENDING` -- Offline payment pending
- `PAID` -- Payment completed
- `CONFIRMED` -- Order confirmed

### Helpers

- `get_all_orders()` -- Paginated retrieval (400 per page)
- `get_summary_by_event(event_id)` -- Sales summary for one event

---

## Tickets API V1

**Wrapper**: `src/wix_api/tickets.py` -- `TicketsAPI` class
**Base path**: `/events/v1/tickets`
**Docs**: https://dev.wix.com/docs/rest/business-solutions/events/events-v1/ticket/list-tickets

Returns individual sold tickets with buyer and payment data. This is distinct from ticket definitions (templates) and guest records.

### List Tickets

```
GET /events/v1/tickets
```

**Query params**: `eventId` (optional), `limit` (max 100), `offset`

Uses GET with query parameters.

**Response key**: `tickets`

### Get Ticket

```
GET /events/v1/tickets/{ticketNumber}
```

### Ticket Order Statuses

- `NA_ORDER_STATUS`
- `PENDING`
- `PAID`
- `OFFLINE_PENDING`
- `DECLINED`
- `FREE`

### Helpers

- `get_all_tickets()` -- All tickets with pagination
- `get_tickets_by_event(event_id)` -- All tickets for one event

---

## eCommerce Transactions API V1

**Wrapper**: `src/wix_api/transactions.py` -- `TransactionsAPI` class
**Base path**: `/ecom/v1/orders`
**Docs**: https://dev.wix.com/docs/rest/business-solutions/e-commerce/orders/order-transactions/introduction

Manages payment and refund transaction records for orders.

### List Transactions for Order

```
GET /ecom/v1/orders/{orderId}/transactions
```

### List Transactions for Multiple Orders

```
POST /ecom/v1/orders/transactions/list
```

**Body**: `{"orderIds": ["order-1", "order-2"]}`

### Add Payments

```
POST /ecom/v1/orders/{orderId}/transactions/payments
```

Max 50 payment records per call.

### Update Payment Status

```
PATCH /ecom/v1/orders/{orderId}/transactions/{transactionId}/status
```

### Bulk Update Payment Statuses

```
POST /ecom/v1/orders/transactions/statuses/bulk-update
```

### Transaction Statuses

`PENDING`, `COMPLETED`, `FAILED`, `CANCELLED`, `REFUNDED`, `PARTIALLY_REFUNDED`, `CHARGEBACK`, `CHARGEBACK_REVERSED`

### Transaction Types

`PAYMENT`, `REFUND`, `CHARGEBACK`, `AUTHORIZATION`

### Helpers

- `get_all_transactions_for_orders(order_ids, batch_size=50)` -- Batched retrieval for large order lists

---

## RSVP API V2

**Wrapper**: `src/wix_api/rsvp.py` -- `RSVPAPI` class
**Base path**: `/events/v2/rsvps`
**Docs**: https://dev.wix.com/docs/rest/business-solutions/events/rsvp-v2/introduction

Manages RSVP responses, check-ins, and guest lists for RSVP-type events.

### Query RSVPs

```
POST /events/v2/rsvps/query
```

**Request body:**

```json
{
  "paging": { "limit": 100, "offset": 0 },
  "filter": { "eventId": "event-123", "rsvpStatus": "YES" }
}
```

**Response key**: `rsvps`

### Search RSVPs

```
POST /events/v2/rsvps/search
```

Advanced search with aggregations support.

### Count RSVPs

```
POST /events/v2/rsvps/count
```

### Get / Create / Update / Delete RSVP

```
GET    /events/v2/rsvps/{rsvpId}
POST   /events/v2/rsvps
PATCH  /events/v2/rsvps/{rsvpId}
DELETE /events/v2/rsvps/{rsvpId}
```

### Bulk Update / Delete

```
POST /events/v2/rsvps/bulk-update
POST /events/v2/rsvps/bulk-delete
```

### Check-in / Cancel Check-in

```
POST /events/v2/rsvps/{rsvpId}/check-in
POST /events/v2/rsvps/{rsvpId}/cancel-check-in
```

### RSVP Summary

```
GET /events/v2/rsvps/summary
```

### RSVP Statuses

`YES`, `NO`, `WAITING`, `PENDING`

### Helpers

- `get_all_rsvps_for_event(event_id)` -- Paginated retrieval for one event

---

## Known Limitations

These limitations were discovered during development and are documented here for reference:

1. **Tickets API returns empty price fields**: The Tickets API (`GET /events/v1/tickets`) returns ticket records but pricing fields are often empty. Use the Orders Summary API for reliable sales data instead.

2. **eCommerce Orders API returns 0 results for events**: The eCommerce Orders API (`/ecom/v1/orders`) does not include event ticket orders. Use the Event Orders API (`/events/v1/orders`) instead.

3. **No individual ticket-type linkage**: While ticket definition pricing is available, there is no reliable way to determine which specific ticket type (e.g., "Early Bird" vs. "General Admission") each buyer purchased from the Orders or Tickets APIs.

4. **Bulk event queries may have empty descriptions**: When querying events in bulk via `/events/v3/events/query`, some events return empty description nodes. The `enrich_descriptions=True` option on `get_all_events()` works around this by re-fetching each event individually.

5. **Guest details require explicit fieldset**: The Guests API returns minimal data by default. The `GUEST_DETAILS` fieldset must be requested to get name, email, phone, and check-in status. Even with this fieldset, name/email are often empty and must be enriched via the Contacts API join.
