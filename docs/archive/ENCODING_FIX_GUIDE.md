# Encoding Fix Guide

## Problem

When opening CSV files in Excel, you see odd characters like:
- `â€"` instead of `–` (EN DASH)
- `â€™` instead of `'` (RIGHT SINGLE QUOTATION MARK/apostrophe)
- `â€˜` instead of `'` (LEFT SINGLE QUOTATION MARK)
- `Weâ€™ll` instead of `We'll`
- `Torontoâ€™s` instead of `Toronto's`

**Root Cause:** Excel opens CSV files as Windows-1252 encoding by default, but the Wix API returns UTF-8 text with special Unicode characters (smart quotes, en dashes, em dashes, etc.).

---

## Solution Implemented

The `EventsTransformer` now has **3 encoding options**:

### 1. UTF-8 with BOM ✅ (RECOMMENDED - DEFAULT)

**Default behavior** - Works perfectly with Excel and preserves all original characters.

```python
EventsTransformer.save_to_csv(events, 'events.csv')
# or explicitly:
EventsTransformer.save_to_csv(events, 'events.csv', encoding='utf-8-sig')
```

**What it does:**
- Adds a UTF-8 BOM (Byte Order Mark) to the file
- Excel recognizes the BOM and opens the file with UTF-8 encoding
- All special characters display correctly
- No data loss

**Result:**
- `We'll` displays as `We'll`
- `12:00–1:45` displays as `12:00–1:45`
- All smart quotes, dashes preserved

---

### 2. Standard UTF-8 (No BOM)

Use if you need standard UTF-8 without BOM.

```python
EventsTransformer.save_to_csv(events, 'events.csv', encoding='utf-8')
```

**What it does:**
- Standard UTF-8 encoding
- No BOM marker

**Issue:**
- Excel may display `â€"` characters
- But data is correct! (Just display issue in Excel)
- Works fine in other tools (Python, pandas, etc.)

---

### 3. ASCII-Only (Replace Special Characters)

Use if you need pure ASCII compatibility.

```python
EventsTransformer.save_to_csv(events, 'events.csv', encoding='ascii')
```

**What it does:**
- Replaces all special Unicode characters with ASCII equivalents:
  - `–` (EN DASH) → `-` (hyphen)
  - `—` (EM DASH) → `-` (hyphen)
  - `'` (SMART QUOTE) → `'` (apostrophe)
  - `"` (SMART DOUBLE QUOTE) → `"` (quote)
  - `…` (ELLIPSIS) → `...` (three periods)

**Result:**
- `We'll` → `We'll` (smart quote replaced with regular apostrophe)
- `12:00–1:45` → `12:00-1:45` (en dash replaced with hyphen)
- 100% ASCII compatible
- Minor visual changes, but fully readable

---

## Character Replacements (ASCII mode)

When using `encoding='ascii'`, these replacements happen:

| Unicode Character | Name | ASCII Replacement |
|-------------------|------|-------------------|
| `–` (U+2013) | EN DASH | `-` |
| `—` (U+2014) | EM DASH | `-` |
| `'` (U+2018) | LEFT SINGLE QUOTATION MARK | `'` |
| `'` (U+2019) | RIGHT SINGLE QUOTATION MARK | `'` |
| `"` (U+201C) | LEFT DOUBLE QUOTATION MARK | `"` |
| `"` (U+201D) | RIGHT DOUBLE QUOTATION MARK | `"` |
| `…` (U+2026) | HORIZONTAL ELLIPSIS | `...` |
| ` ` (U+00A0) | NO-BREAK SPACE | ` ` |

---

## Examples

### Before (encoding issues in Excel)

```
formatted_date_time: October 12, 2025, 12:00â€"1:45 p.m.
description_full: Weâ€™ll explore a few different applications...
```

### After with UTF-8 BOM (recommended)

```
formatted_date_time: October 12, 2025, 12:00–1:45 p.m.
description_full: We'll explore a few different applications...
```

### After with ASCII

```
formatted_date_time: October 12, 2025, 12:00-1:45 p.m.
description_full: We'll explore a few different applications...
```

---

## Testing

Run the encoding test to compare all three options:

```bash
python scripts/test_encoding_fix.py
```

This creates 3 CSV files:
1. `events_utf8_bom_*.csv` - UTF-8 with BOM (recommended)
2. `events_utf8_*.csv` - Standard UTF-8
3. `events_ascii_*.csv` - ASCII-only

Open each in Excel to see the difference!

---

## Recommendation

**Use the default (UTF-8 with BOM):**

```python
from transformers.events import EventsTransformer

# This is now the default - no need to specify encoding
EventsTransformer.save_to_csv(events, 'events.csv')
```

**Benefits:**
- ✅ Works perfectly in Excel
- ✅ Preserves all original characters
- ✅ No data loss
- ✅ No visual changes

**When to use ASCII:**
- You need pure ASCII compatibility
- Working with legacy systems that don't support UTF-8
- You prefer simple hyphens over fancy dashes

---

## Technical Details

### What is a BOM?

BOM (Byte Order Mark) is a special marker `\xef\xbb\xbf` (UTF-8 encoded `\ufeff`) at the start of a text file that indicates:
1. The file is UTF-8 encoded
2. The byte order (not needed for UTF-8, but signals encoding)

Excel recognizes this marker and automatically uses UTF-8 encoding to read the file.

### Why does the issue happen?

1. Wix API returns JSON with UTF-8 text
2. Text includes Unicode characters like EN DASH (U+2013)
3. We save to CSV with UTF-8 encoding
4. Excel opens CSV without BOM → assumes Windows-1252
5. UTF-8 bytes decoded as Windows-1252 → gibberish

### The fix:

1. Add BOM to CSV file (`encoding='utf-8-sig'`)
2. Excel sees BOM → uses UTF-8 encoding
3. Characters display correctly ✓

---

## Files Modified

1. **`src/transformers/events.py`**
   - Changed default encoding to `'utf-8-sig'`
   - Added `_clean_special_characters()` method
   - Added support for `encoding` parameter

2. **`scripts/test_encoding_fix.py`**
   - New test script to compare encoding options
   - Creates sample files with all 3 encodings

---

## Quick Reference

```python
# Recommended (default)
EventsTransformer.save_to_csv(events, 'events.csv')

# Explicit UTF-8 with BOM
EventsTransformer.save_to_csv(events, 'events.csv', encoding='utf-8-sig')

# Standard UTF-8 (no BOM)
EventsTransformer.save_to_csv(events, 'events.csv', encoding='utf-8')

# ASCII-only (replace special chars)
EventsTransformer.save_to_csv(events, 'events.csv', encoding='ascii')
```

---

## Troubleshooting

**Q: I still see `â€"` in Excel**
- Make sure you're using `encoding='utf-8-sig'` (or no encoding parameter, as it's now the default)
- Close and reopen Excel after regenerating the CSV

**Q: I want to keep the fancy dashes but Excel shows them wrong**
- Use `encoding='utf-8-sig'` (default)
- The BOM tells Excel to use UTF-8

**Q: I don't care about fancy dashes, just want it to work**
- Use `encoding='ascii'`
- All special characters will be replaced with simple ASCII

**Q: Does this affect the data quality?**
- UTF-8 with BOM: No data loss, perfect preservation
- ASCII: Minor visual changes only (– becomes -, ' becomes ')
