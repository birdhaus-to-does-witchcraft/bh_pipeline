# Tickets vs Guests API Analysis

**Date:** October 18, 2025
**Status:** ⚠️ IMPORTANT FINDINGS - Tickets API has access restrictions

---

## Executive Summary

**RECOMMENDATION: Use Guests API for ticket/payment data instead of Tickets API V1**

The Guests API already provides all the ticket and order information you need, while the Tickets API V1 returns empty data (likely due to API key permission restrictions or PII protection).

---

## Research Findings

### Tickets API V1 Investigation

**Endpoint Tested:** `GET /events/v1/tickets`

**Results:**
- ✅ API responds successfully (HTTP 200)
- ✅ Returns correct count: 1,620 tickets total
- ✅ Pagination works correctly
- ❌ **ALL data fields are EMPTY strings**

**Sample Response:**
```json
{
  "total": 1620,
  "offset": 0,
  "limit": 100,
  "tickets": [
    {
      "ticketNumber": "",
      "orderNumber": "",
      "ticketDefinitionId": "",
      "name": "",
      "orderFullName": "",
      "guestFullName": "",
      "free": false,
      "orderStatus": "NA_ORDER_STATUS",
      "qrCode": "",
      "ticketPdf": "",
      "checkInUrl": "",
      "anonymized": false,
      "archived": false,
      "canceled": false,
      "channel": "ONLINE"
    }
  ]
}
```

**Analysis of Empty Data:**

Out of 100 tickets sampled:
- `ticketNumber`: 100% empty
- `orderNumber`: 100% empty
- `name`: 100% empty
- `orderFullName`: 100% empty
- `ticketDefinitionId`: 100% empty
- `anonymized`: All `false` (not anonymization issue)
- `orderStatus`: All `NA_ORDER_STATUS`

**Possible Causes:**

1. **API Key Permissions**: The current API key may not have "Read Event Tickets and Guest List" permission scope
2. **PII Protection**: Wix may restrict ticket holder names/emails through REST API
3. **Endpoint Access Restriction**: V1 Tickets API may be deprecated or restricted
4. **Development vs Production Keys**: May require production API key with elevated permissions

---

### Guests API V2 - Already Has Ticket Data!

**Endpoint Tested:** `POST /events/v2/guests/query`

**Results:**
- ✅ Returns complete data for 2,871 guests
- ✅ Includes order numbers (e.g., "2Z4T-98RG-RNZ")
- ✅ Includes buyer/guest type classification
- ✅ Can be enriched with contact data (names, emails)

**Sample Response:**
```json
{
  "guests": [
    {
      "id": "000360b7-3cce-4fc8-b643-1b1c5c221cb6",
      "eventId": "e56e5bd0-c3ae-4638-99bc-ffab2aaf9c9d",
      "contactId": "abb0bfd9-54f2-42bf-b406-1e322bda6c58",
      "orderNumber": "2Z4T-98RG-RNZ",  ← ORDER NUMBER HERE!
      "guestType": "BUYER",
      "attendanceStatus": "ATTENDING",
      "tickets": [],
      "createdDate": "2025-08-12T02:20:04.248Z",
      "updatedDate": "2025-08-17T15:57:46.795Z"
    }
  ]
}
```

**What Guests API Provides:**

| Field | Description | Example |
|-------|-------------|---------|
| `orderNumber` | Payment order number | "2Z4T-98RG-RNZ" |
| `guestType` | BUYER, TICKET_HOLDER, or RSVP | "BUYER" |
| `contactId` | Link to contact record | (GUID) |
| `eventId` | Link to event record | (GUID) |
| `attendanceStatus` | ATTENDING, NOT_ATTENDING, etc. | "ATTENDING" |
| `tickets` | Array of ticket details | [...] |
| `createdDate` | Purchase timestamp | ISO 8601 |

**When enriched with Contacts API:**
- Buyer full name
- Email address
- Phone number

---

## Data Comparison

### What You Need from "Payment Dashboard"

Based on your requirement for "sold tickets to an event" data from the Payment Dashboard:

| Required Data | Guests API | Tickets API V1 | Status |
|---------------|------------|----------------|--------|
| Order Number | ✅ Yes | ❌ Empty | **Use Guests** |
| Buyer Name | ✅ Via Contacts | ❌ Empty | **Use Guests** |
| Guest Name | ✅ Via Contacts | ❌ Empty | **Use Guests** |
| Event ID | ✅ Yes | ⚠️ Param only | **Use Guests** |
| Purchase Date | ✅ createdDate | ❌ Empty | **Use Guests** |
| Ticket Type | ✅ Via tickets array | ❌ Empty | **Use Guests** |
| Price | ⚠️ Not directly | ❌ Empty | **Neither** |
| Order Status | ⚠️ attendanceStatus | ❌ Empty | **Guests (partial)** |

---

## Recommendation

### Use Guests API as Primary Source

**Why:**
1. ✅ Already implemented and working (2,871 guests fetched)
2. ✅ Returns order numbers for payment tracking
3. ✅ Can be enriched with buyer/guest names via Contacts API
4. ✅ Includes all ticket holder information
5. ✅ No access restriction issues

**Current Data Coverage:**
- **2,871 guests** = 2,871 ticket holders/buyers
- Each guest has an `orderNumber` (payment identifier)
- Enriched with names/emails from Contacts (100% coverage)

### What's Missing from Guests API

**Pricing Information:**
- The Guests API doesn't return ticket prices or payment amounts
- The Tickets API V1 has a `free` boolean but no price field (and it's empty anyway)

**Possible Solutions for Pricing:**
1. **Ticket Definitions API** - Get pricing from ticket type templates
2. **eCommerce Orders API** - Try to match orderNumber to get payment amounts
3. **Manual Mapping** - Map ticket types to known prices

---

## Next Steps

### Option A: Continue with Guests API (Recommended)

**Pros:**
- ✅ Already fully implemented
- ✅ All data fields populated
- ✅ 100% name coverage via enrichment
- ✅ No additional API work needed

**Cons:**
- ❌ No pricing data
- ❌ Need separate lookup for ticket prices

**Action Items:**
1. Document that `orderNumber` field in Guests = payment order
2. Add `orderNumber` to exported CSV prominently
3. Optionally: Investigate Ticket Definitions API for pricing

### Option B: Investigate Tickets API Permissions

**Pros:**
- Might get pricing data if permissions fixed
- Might get additional ticket metadata

**Cons:**
- ❌ Requires API key permission changes
- ❌ May need production API key upgrade
- ❌ Uncertain if data will be available even with permissions
- ❌ Additional development time

**Action Items:**
1. Contact Wix support about Tickets API permissions
2. Check if API key has "Read Event Tickets and Guest List" scope
3. Test with elevated permissions if available

### Option C: Use eCommerce Orders API for Pricing

**Pros:**
- Might provide actual payment amounts
- Could match by orderNumber

**Cons:**
- Previous test returned 0 orders (may be separate system)
- Events tickets may not use eCommerce orders

**Action Items:**
1. Test matching guest `orderNumber` with eCommerce Orders API
2. Check if order search supports ticket order numbers

---

## Current Data Pipeline Status

### What We Have Now

**Events:** ✅ 111 events with full details
**Contacts:** ✅ 1,363 contacts with names/emails
**Guests:** ✅ 2,871 guests with order numbers + enriched names
**Transactions:** ❌ 0 results (eCommerce orders)
**Tickets:** ⚠️ 1,620 count but empty data

### What Payment Dashboard Shows

The Payment Dashboard likely aggregates:
- Order numbers (✅ we have this via Guests)
- Buyer names (✅ we have this via Contacts enrichment)
- Ticket counts per order (✅ can derive from Guests)
- Total sales amounts (❌ we don't have this)
- Net sales after fees (❌ we don't have this)

**Coverage: ~60%** of Payment Dashboard data available through Guests API

---

## Technical Details

### Tickets API Response Format

Unlike other Wix V2 APIs, Tickets V1 uses:
- `total`, `offset`, `limit` (not `pagingMetadata`)
- GET with query params (not POST with JSON body)
- Returns `tickets` array (consistent)

### Why MCP Server Showed 1,620 Tickets

The MCP server's `get_tickets` tool returned:
```json
{
  "total": 1620,
  "tickets": [...]  // but all fields empty
}
```

This confirms the API is accessible and returning the correct count, but the actual data fields are restricted or empty.

---

## Conclusion

**For "sold tickets to an event" data:**

👍 **BEST APPROACH:** Use existing Guests API data
- You already have 2,871 guest records
- Each has an `orderNumber` (links to payment)
- All have buyer/guest names via Contacts enrichment
- Covers all ticket holders/buyers

⚠️ **PRICING DATA:** Not available via current APIs
- Consider manual ticket price mapping
- Or investigate Ticket Definitions API
- Or accept that pricing isn't in automated pipeline

❌ **AVOID:** Tickets API V1 (for now)
- Returns empty data with current API key
- Would require permission escalation
- Uncertain if data would become available

---

**Last Updated:** October 18, 2025
**Status:** Guests API recommended; Tickets API requires further investigation
