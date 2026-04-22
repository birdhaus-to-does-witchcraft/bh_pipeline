# Changelog

**Purpose:** Historical record of major bug fixes and improvements

---

## October 18, 2025

### 🐛 Pagination Fix

**Issue:** Pipeline was only retrieving the first page of results from Wix APIs
- Events: 100 of 111 (missing 11)
- Contacts: 50 of 1,363 (missing 1,313!)
- Guests: 100 of 2,871 (missing 2,771!)

**Root Causes:**
1. Test script making direct API calls instead of using wrapper classes
2. Pagination helper stopping early for APIs without `total` field

**Solution:**
- Updated test scripts to use API wrappers (`EventsAPI`, `ContactsAPI`, `GuestsAPI`)
- Fixed pagination utility to handle APIs that don't return `total` field
- Added detection for partial pages (count < limit = end of data)

**Result:** ✅ Now retrieving ALL records from all APIs
- Events: 111 ✓
- Contacts: 1,363 ✓
- Guests: 2,871 ✓

**Performance Impact:**
- Events: +10% more data
- Contacts: +2,626% more data
- Guests: +2,771% more data

**Files Modified:**
- `src/utils/pagination.py` - Enhanced pagination logic
- `scripts/test_all_transformers.py` - Use API wrappers instead of direct calls

**Reference:** See `docs/archive/PAGINATION_FIX_SUMMARY.md` for full details

---

### 🐛 Guest Name Enrichment Fix

**Issue:** Guest CSV exports had empty name/email fields (all 2,871 guests)

**Root Cause:** Wix Guests API V2 doesn't return `guestDetails` with name/email/phone data

**Discovery:**
- Tried multiple fieldset combinations (`GUEST_DETAILS`, `DETAILS`, `FULL`)
- None returned name data
- Found that each guest has a `contactId` field
- Contacts API DOES return full contact information

**Solution:** Implemented guest enrichment via Contacts API join
1. Created `GuestsTransformer.enrich_with_contact_data()` method
2. Fetches all contacts and builds `contactId → {name, email, phone}` lookup
3. Enriches guest records with contact data
4. Updated test script to automatically enrich before saving

**Implementation:**
```python
# Build contact lookup
contact_lookup = {}
for contact in contacts:
    contact_lookup[contact['id']] = {
        'first_name': ...,
        'last_name': ...,
        'email': ...,
        'phone': ...
    }

# Enrich guests
for guest in transformed_guests:
    if guest['contact_id'] in contact_lookup:
        guest.update(contact_lookup[guest['contact_id']])
```

**Result:**
- Before: 0% of guests had names
- After: 100% of guests have names (2,871 guests enriched)
- 90.3% have last names (reflects underlying contact data completeness)

**API Overhead:** ~43 API calls total (29 for guests + 14 for contacts)

**Files Modified:**
- `src/transformers/guests.py` - Added enrichment method
- `scripts/test_all_transformers.py` - Added enrichment step

**Reference:** See `docs/archive/GUEST_ENRICHMENT_FIX.md` for full details

---

### 🐛 UTF-8 Encoding Fix for Excel

**Issue:** Special characters displaying as gibberish in Excel
- `We'll` → `Weâ€™ll`
- `12:00–1:45` → `12:00â€"1:45`
- `Toronto's` → `Torontoâ€™s`

**Root Cause:**
- Wix API returns UTF-8 text with special Unicode (smart quotes, en dashes)
- Pipeline saved CSV with UTF-8 encoding
- Excel opened CSV assuming Windows-1252 encoding
- UTF-8 bytes decoded as Windows-1252 → gibberish

**Solution:** Add UTF-8 BOM (Byte Order Mark) to CSV files

UTF-8 BOM is a special marker (`\xef\xbb\xbf`) at the start of files that signals UTF-8 encoding. Excel recognizes this and opens files with correct encoding.

**Implementation:**
1. Changed default encoding to `utf-8-sig` (UTF-8 with BOM)
2. Added character cleaning method for optional ASCII mode
3. Provided encoding parameter for flexibility

**Usage:**
```python
# UTF-8 with BOM (default - recommended)
EventsTransformer.save_to_csv(events, 'events.csv')

# ASCII mode (replaces special characters)
EventsTransformer.save_to_csv(events, 'events.csv', encoding='ascii')
```

**Character Replacements (ASCII mode):**
- EN DASH (–) → hyphen (-)
- EM DASH (—) → hyphen (-)
- SMART QUOTES ('') → regular quotes ('')
- ELLIPSIS (…) → three periods (...)

**Result:**
- ✅ Excel opens files correctly with UTF-8 BOM
- ✅ All special characters display properly
- ✅ No data loss
- ✅ Option for pure ASCII if needed

**Files Modified:**
- `src/transformers/base.py` - Added BOM support and character cleaning
- `src/transformers/events.py` - Updated to use base class methods
- All transformer classes - Inherited BOM encoding

**Reference:** See `docs/archive/ENCODING_FIX_GUIDE.md` for full details

---

## Summary

All three fixes implemented on October 18, 2025:

1. **Pagination Fix** - Now retrieving 100% of available data (26x more contacts, 28x more guests)
2. **Guest Enrichment** - 100% of guests now have names/emails (2,871 guests enriched)
3. **UTF-8 BOM** - Excel compatibility fixed, special characters display correctly

**Impact:**
- Complete data retrieval (no missing records)
- Usable guest data (previously all empty)
- Professional CSV exports (no encoding issues)

**Code Quality:**
- Centralized utilities (BaseTransformer for encoding)
- Reusable patterns (enrichment method, pagination helper)
- Comprehensive testing (test_all_transformers.py validates all fixes)

---

For detailed analysis and technical implementation, see archived documentation in `docs/archive/`:
- `PAGINATION_FIX_SUMMARY.md`
- `GUEST_ENRICHMENT_FIX.md`
- `ENCODING_FIX_GUIDE.md`
