# Scripts Summary

## Overview

This document provides a complete guide to all scripts in the `birdhaus_data_pipeline` project after rationalization.

**Rationalization Results**:
- **Before**: 21 scripts (many redundant/overlapping)
- **After**: 11 scripts (48% reduction)
- **New Scripts**: 4 consolidated/production scripts
- **Deleted**: 13 redundant scripts

---

## Script Categories

### Production Scripts (3)

Scripts for actual data extraction in production environments.

#### 1. `pull_all.py` - Full Data Extraction
**Purpose**: Extract ALL data from Wix APIs

**Usage**:
```bash
# Extract all data to default directory (data/processed)
python scripts/pull_all.py

# Extract to custom directory
python scripts/pull_all.py --output-dir /path/to/output

# Via installed command
wix-pull-all
```

**What it extracts**:
- Events (all events with full details)
- Contacts (all contacts)
- Guests (with contact enrichment for names/emails)
- Order Summaries (sales data per event)
- Transactions (orders with payment info)

**Output**: Timestamped CSV files with UTF-8 BOM encoding (Excel-friendly)

---

#### 2. `pull_incremental.py` - Delta Updates
**Purpose**: Pull only new/updated data since last run

**Status**: PLACEHOLDER (needs implementation)

**Planned Usage**:
```bash
python scripts/pull_incremental.py
wix-pull-incremental
```

**Planned Features**:
- Track last extraction timestamp
- Use `updatedDate` filters on APIs
- Merge with existing data
- Efficient for daily/hourly updates

---

#### 3. `backfill_historical.py` - Historical Data Backfill
**Purpose**: One-time extraction for specific date range

**Status**: PLACEHOLDER (needs implementation)

**Planned Usage**:
```bash
python scripts/backfill_historical.py --start-date 2024-01-01 --end-date 2025-01-01
python scripts/backfill_historical.py --start-date 2024-01-01 --end-date 2025-01-01 --entities events,guests
wix-backfill --start-date 2024-01-01 --end-date 2025-01-01
```

---

### Testing Scripts (3)

Scripts for testing and validation.

#### 4. `test_pipeline.py` - Unified Pipeline Testing
**Purpose**: Comprehensive testing of the entire pipeline

**Replaces**: `test_setup.py`, `test_wix_client.py`, `test_phase2.py`

**Usage**:
```bash
# Test everything
python scripts/test_pipeline.py --stage all

# Test only dependencies
python scripts/test_pipeline.py --stage setup

# Test client configuration
python scripts/test_pipeline.py --stage client

# Test API wrappers
python scripts/test_pipeline.py --stage wrappers

# Test transformers
python scripts/test_pipeline.py --stage transformers
```

**Test Stages**:
1. **Setup**: Dependencies (requests, pandas, numpy, etc.) and internal modules
2. **Client**: Configuration loading and API connection
3. **Wrappers**: All API wrapper classes (Events, Guests, Contacts, Orders)
4. **Transformers**: All transformer classes

---

#### 5. `test_all_transformers.py` - Comprehensive Transformer Testing
**Purpose**: Test all transformers with real API data

**Usage**:
```bash
python scripts/test_all_transformers.py
```

**What it tests**:
- Events transformer (119 → 55 fields)
- Contacts transformer (55 → 36 fields)
- Guests transformer with enrichment (12 → 31 fields)
- Order summaries transformer (1 → 12 fields)
- Transactions transformer

**Output**: Timestamped test CSV files in `data/processed/`

---

#### 6. `test_encoding_fix.py` - Encoding Testing
**Purpose**: Test UTF-8 encoding solutions for special characters

**Usage**:
```bash
python scripts/test_encoding_fix.py
```

**What it tests**:
- UTF-8 with BOM (recommended for Excel)
- Standard UTF-8 (no BOM)
- ASCII-only (replaces special chars)

---

### Debugging Scripts (2)

Scripts for debugging API issues.

#### 7. `debug_api.py` - Unified API Debugging
**Purpose**: Debug Wix API endpoints

**Replaces**: `debug_events.py`, `debug_events_fieldsets.py`, `test_endpoints.py`, `test_pagination.py`

**Usage**:
```bash
# Debug events API response
python scripts/debug_api.py --endpoint events --test response

# Test pagination
python scripts/debug_api.py --endpoint guests --test pagination

# Test different fieldsets
python scripts/debug_api.py --endpoint events --test fieldsets

# Test endpoint paths
python scripts/debug_api.py --endpoint events --test endpoints

# Debug other endpoints
python scripts/debug_api.py --endpoint contacts --test response
```

**Supported Endpoints**: `events`, `guests`, `contacts`

**Test Types**: `response`, `pagination`, `fieldsets`, `endpoints`

---

#### 8. `diagnose_guests_issue.py` - Guest API Diagnostic
**Purpose**: Comprehensive diagnostics for guest data issues

**Replaces**: `check_guests_data.py`, `test_guests_api.py`, `test_guests_by_event.py`

**Usage**:
```bash
python scripts/diagnose_guests_issue.py
```

**What it checks**:
- Configuration (API keys, site ID)
- Events API (baseline test)
- Guests API (all guests)
- Guests API (by event)
- Contacts API (alternative data source)
- Provides troubleshooting recommendations

---

### Analysis Scripts (2)

Scripts for data analysis and documentation.

#### 9. `analyze_data_coverage.py` - Field Coverage Analysis
**Purpose**: Show what data is kept vs removed in transformations

**Usage**:
```bash
# Analyze all data types
python scripts/analyze_data_coverage.py --type all

# Analyze specific type
python scripts/analyze_data_coverage.py --type events
python scripts/analyze_data_coverage.py --type guests
python scripts/analyze_data_coverage.py --type contacts
python scripts/analyze_data_coverage.py --type orders
```

**Output**: Detailed breakdown of:
- Raw API fields count
- Transformed fields count
- What data is kept (with categories)
- What data is removed (with reasons)

**Example Results**:
- Events: 119 raw → 55 transformed (64 fields removed)
- Contacts: 55 raw → 36 transformed (19 fields removed)
- Guests: 12 raw → 31 transformed (19 fields added via enrichment)
- Orders: 1 raw → 12 transformed (11 fields added via calculations)

---

#### 10. `show_new_fields.py` - New Fields Documentation
**Purpose**: Document new fields added by transformers

**Usage**:
```bash
python scripts/show_new_fields.py
```

**Shows**:
- Detailed address breakdown (5 new fields)
- Image dimensions (2 new fields)
- Description fields (4 variants)
- Field counts and logic

---

### Utility Scripts (1)

Optional post-processing utilities.

#### 11. `clean_csv.py` - CSV Post-Processing
**Purpose**: OPTIONAL additional cleaning beyond transformers

**Note**: Transformers already do 90% of cleaning. This is for edge cases.

**Usage**:
```bash
# Remove specific columns
python scripts/clean_csv.py input.csv --remove-columns col1,col2,col3

# Keep only specific columns
python scripts/clean_csv.py input.csv --keep-columns id,title,status

# Rename columns
python scripts/clean_csv.py input.csv --rename old_name:new_name,foo:bar

# Filter rows
python scripts/clean_csv.py input.csv --filter "status == 'SCHEDULED'"

# Drop duplicates
python scripts/clean_csv.py input.csv --drop-duplicates

# Remove empty columns
python scripts/clean_csv.py input.csv --drop-empty

# Merge multiple CSVs
python scripts/clean_csv.py file1.csv file2.csv --merge --output merged.csv
```

---

## Data Cleaning Architecture

### The "CSV Cleaning" is Built Into Transformers!

You asked about a script that reduces columns from 100+ to <50. **That functionality is already built into the transformers**, not a separate script.

### Transformer Field Reduction:

| Data Type | Raw Fields | Cleaned Fields | Reduction |
|-----------|------------|----------------|-----------|
| Events | 119 | 55 | 53.8% |
| Contacts | 55 | 36 | 34.5% |
| Guests | 12 | 31 | -158% (enrichment!) |
| Order Summaries | 1 | 12 | -1100% (calculations!) |

### What Transformers Remove:
1. ✗ UI/Template text (confirmation messages, labels)
2. ✗ Form field structures (can be reconstructed if needed)
3. ✗ Rich text formatting nodes (plain text extracted instead)
4. ✗ Nested arrays of objects (flattened or summarized)
5. ✗ Configuration settings (ticket limits, etc.)

### What Transformers Extract:
1. ✓ Core business data
2. ✓ Flattened nested structures
3. ✓ Plain text from rich text
4. ✓ Calculated fields (fees, averages)
5. ✓ Enriched data (guest names from contacts)

### When to Use `clean_csv.py`:
- Remove additional columns not handled by transformers
- Rename columns for specific use cases
- Filter rows based on business logic
- Merge data from multiple sources
- Apply custom transformations

---

## Deleted Scripts (13)

These scripts have been consolidated or replaced:

### Consolidated into `debug_api.py` (4):
- ❌ `debug_events.py`
- ❌ `debug_events_fieldsets.py`
- ❌ `test_endpoints.py`
- ❌ `test_pagination.py`

### Consolidated into `diagnose_guests_issue.py` (3):
- ❌ `check_guests_data.py`
- ❌ `test_guests_api.py`
- ❌ `test_guests_by_event.py`

### Consolidated into `test_pipeline.py` (3):
- ❌ `test_setup.py`
- ❌ `test_wix_client.py`
- ❌ `test_phase2.py`

### Covered by `test_all_transformers.py` (2):
- ❌ `test_transformer.py` (events only)
- ❌ `test_contacts_transformer.py` (contacts only)

### Replaced by transformers + `pull_all.py` (1):
- ❌ `export_events_and_guests.py` (old export script)

---

## Quick Reference

### Common Workflows:

**Initial Setup Testing**:
```bash
# Test everything is working
python scripts/test_pipeline.py --stage all
```

**Production Data Extraction**:
```bash
# Full extraction
python scripts/pull_all.py

# Output goes to: data/processed/
```

**Debugging API Issues**:
```bash
# Debug specific endpoint
python scripts/debug_api.py --endpoint events --test response

# Diagnose guest issues
python scripts/diagnose_guests_issue.py
```

**Data Analysis**:
```bash
# See what data is kept/removed
python scripts/analyze_data_coverage.py --type all

# Test transformers with real data
python scripts/test_all_transformers.py
```

**Optional Post-Processing**:
```bash
# Remove unwanted columns
python scripts/clean_csv.py data.csv --remove-columns col1,col2

# Keep only specific columns
python scripts/clean_csv.py data.csv --keep-columns id,title,status
```

---

## Installation

All scripts are available after installing the package:

```bash
# Install in development mode
pip install -e .

# Installed commands:
wix-pull-all         # scripts/pull_all.py
wix-pull-incremental # scripts/pull_incremental.py
wix-backfill         # scripts/backfill_historical.py
```

---

## Configuration

All scripts use environment variables from `.env` file:

```
WIX_API_KEY=your-api-key
WIX_ACCOUNT_ID=your-account-id
WIX_SITE_ID=your-site-id
WIX_BASE_URL=https://www.wixapis.com
```

See `config/credentials.env.template` for full configuration template.

---

## Summary of Changes

### Before Rationalization (21 scripts):
- Multiple overlapping debug scripts
- Multiple overlapping test scripts
- Multiple overlapping guest diagnostic scripts
- Inconsistent patterns
- Hard to navigate

### After Rationalization (11 scripts):
- ✅ Clear organization by purpose
- ✅ No redundancy
- ✅ Unified interfaces with command-line options
- ✅ Consolidated functionality
- ✅ Production-ready extraction scripts
- ✅ Easy to maintain

### Net Result:
**21 scripts → 11 scripts = 48% reduction in complexity**

---

## Next Steps

### To Implement (Optional):
1. `pull_incremental.py` - Incremental data extraction
2. `backfill_historical.py` - Historical data backfill

### To Use Now:
1. Run `test_pipeline.py --stage all` to verify setup
2. Run `pull_all.py` to extract all data
3. Use `analyze_data_coverage.py` to understand transformations
4. Use `clean_csv.py` for any additional post-processing needs
