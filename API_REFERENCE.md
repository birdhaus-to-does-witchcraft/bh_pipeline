# Wix API Reference

**Last Updated:** 2025-10-18
**Purpose:** Quick reference for Wix REST API endpoints used in this pipeline

---

## Authentication

All API requests require these headers:

```http
Authorization: <API_KEY>
wix-account-id: <ACCOUNT_ID>
wix-site-id: <SITE_ID>
Content-Type: application/json
```

**Configuration:** Credentials stored in `.env` file (see README.md for setup)

---

## Rate Limiting

- **Limit:** 100 requests per 60 seconds (default)
- **Implementation:** Automatic rate limiting via `pyrate-limiter`
- **Retry Logic:** Exponential backoff with `tenacity`
- **Configuration:** Adjust in `config/pipeline_config.yaml` if needed

---

## Pagination

All query endpoints use similar pagination structure:

**Request:**
```json
{
  "paging": {
    "limit": 100,
    "offset": 0
  }
}
```

**Response:**
```json
{
  "pagingMetadata": {
    "count": 100,
    "offset": 0,
    "total": 1363,
    "hasNext": true
  }
}
```

**Note:** Some APIs (like Guests V2) don't return `total` field. The pagination utility handles both cases.

---

## API Endpoints

### 1. Events API V3

**Base URL:** `https://www.wixapis.com/events/v3`
**Docs:** https://dev.wix.com/docs/rest/business-solutions/events/events-v3/introduction

**Key Endpoints:**
- `POST /events/v3/events/query` - Query events with filtering and pagination
- `GET /events/v3/events/{eventId}` - Get event details by ID

**Query Example:**
```json
{
  "paging": {"limit": 100, "offset": 0},
  "filter": {"status": ["PUBLISHED"]},
  "sort": [{"fieldName": "scheduling.config.startDate", "order": "ASC"}]
}
```

**Important:**
- V1 API was removed November 6, 2024 - always use V3
- Must include `paging` in request to get results
- Response has nested structure (e.g., `scheduling.config.startDate`)

---

### 2. Event Guests API V2

**Base URL:** `https://www.wixapis.com/events/v2`
**Docs:** https://dev.wix.com/docs/rest/business-solutions/events/event-guests/introduction

**Key Endpoints:**
- `POST /events/v2/guests/query` - Query all guests (limit: 100 default)
- `GET /events/v2/guests/{guestId}` - Get individual guest details

**Query Example:**
```json
{
  "fieldsets": ["GUEST_DETAILS"],
  "filter": {"eventId": "event-123"},
  "paging": {"limit": 100, "offset": 0}
}
```

**CRITICAL:** Must include `fieldsets: ["GUEST_DETAILS"]` to get full guest information

**Guest Data Enrichment:**
- Guests API does NOT return names/emails directly
- Each guest has a `contactId` field
- Use Contacts API to enrich with name/email data
- See `GuestsTransformer.enrich_with_contact_data()` method

---

### 3. Contacts API V4

**Base URL:** `https://www.wixapis.com/contacts/v4`
**Docs:** https://dev.wix.com/api/rest/contacts/contacts/contacts-v4

**Key Endpoints:**
- `GET /contacts/v4/contacts` - List contacts (up to 1,000)
- `GET /contacts/v4/contacts/{id}` - Get contact by ID

**Query Example:**
```json
{
  "filter": {
    "lastActivity.activityDate": {"$gte": "2025-01-01T00:00:00Z"}
  },
  "paging": {"limit": 100, "offset": 0}
}
```

**PII Handling:**
- Contains email, phone, address (sensitive data)
- Use `contact_id` as identifier where possible
- See Privacy & Security section below

---

### 4. eCommerce Orders API V1

**Base URL:** `https://www.wixapis.com/ecom/v1`
**Docs:** https://dev.wix.com/docs/rest/business-solutions/e-commerce/orders/introduction

**Key Endpoints:**
- `POST /ecom/v1/orders/search` - Search orders with filters
- `GET /ecom/v1/orders/{orderId}` - Get order by ID

**Search Request Format:**
```json
{
  "search": {
    "paging": {"limit": 100}
  }
}
```

**Note:** Request body must wrap pagination in `search` object.

---

### 5. Order Transactions API V1

**Base URL:** `https://www.wixapis.com/ecom/v1`
**Docs:** https://dev.wix.com/docs/rest/business-solutions/e-commerce/orders/order-transactions/introduction

**Key Endpoints:**
- `POST /ecom/v1/orders/transactions/list` - List transactions for multiple orders
- `GET /ecom/v1/orders/{orderId}/transactions` - List transactions for single order

**Use Case:** Track payments, refunds, transaction status

---

### 6. Tickets API V1

**Status:** ⚠️ Limited Data Available

**Endpoint:** `GET /events/v1/tickets`

**Issue:** API returns 1,620 ticket count but all data fields are empty (likely permission restrictions)

**Recommendation:** Use Guests API instead for ticket/order data
- Guests API includes `orderNumber`, `guestType`, `attendanceStatus`
- Can be enriched with buyer names via Contacts API
- See TICKETS_VS_GUESTS_ANALYSIS.md in docs/archive/ for full analysis

---

## Data Recommendations

### For Event Data
✅ Use Events V3 API
✅ Access: event details, scheduling, location, pricing, categories

### For Ticket/Payment Data
✅ Use Guests API (not Tickets API)
✅ Each guest record includes `orderNumber` (payment identifier)
✅ Enrich with Contacts API for buyer names/emails

### For Customer Data
✅ Use Contacts API
✅ Link via `contactId` field in Guests
✅ Handle PII responsibly

---

## Privacy & Security

### PII Data Handling

**Contains PII:**
- Contacts API: email, phone, address
- Guests API (enriched): name, email

**Best Practices:**
1. Store raw data with restricted access
2. Use `contact_id` instead of email in analytics
3. Comply with PIPEDA (Canada) / GDPR (if applicable)
4. Implement data retention policies
5. Encrypt sensitive data at rest

### Credentials Management
- API keys in `.env` (gitignored)
- Never commit credentials to version control
- Rotate API keys periodically
- Use separate keys for dev/prod

---

## Common Issues

### 404 Not Found
- Check endpoint path is complete (e.g., `/events/v3/events/query`)
- Verify API version (V1 may be deprecated)

### 400 Bad Request
- Check `account_id` matches `site_id`
- Verify request body structure (some endpoints require wrappers)

### Empty Response
- Ensure `paging` field is included in request
- For Guests API, include `fieldsets: ["GUEST_DETAILS"]`

### Rate Limiting
- Monitor API stats via MCP server
- Reduce `max_calls` in config if hitting limits
- Pipeline automatically handles retries

---

## API Wrappers

This pipeline provides Python wrappers for each API:

- `EventsAPI` - src/wix_api/events.py
- `GuestsAPI` - src/wix_api/guests.py
- `ContactsAPI` - src/wix_api/contacts.py
- `TransactionsAPI` - src/wix_api/transactions.py

**Usage:**
```python
from wix_api.client import WixAPIClient
from wix_api.events import EventsAPI

client = WixAPIClient.from_env()
events_api = EventsAPI(client)
events = events_api.get_all_events()  # Automatic pagination
```

---

## Reference Links

- **Main Wix API Docs:** https://dev.wix.com/docs/rest
- **Events V3:** https://dev.wix.com/docs/rest/business-solutions/events/events-v3/introduction
- **Guests V2:** https://dev.wix.com/docs/rest/business-solutions/events/event-guests/introduction
- **Contacts V4:** https://dev.wix.com/api/rest/contacts/contacts/contacts-v4
- **eCommerce Orders:** https://dev.wix.com/docs/rest/business-solutions/e-commerce/orders/introduction

---

For historical API analysis and deprecated endpoints, see `docs/archive/WIX_API_IMPLEMENTATION_PLAN.md`
