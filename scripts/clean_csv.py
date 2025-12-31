""""
Optional CSV post-processing script.

NOTE: The transformers already do most data cleaning:
- Events: 119 → 55 fields (removes UI templates, form configs, rich text formatting)
- Contacts: 55 → 36 fields (removes extended fields, member data)
- Guests: 12 → 31 enriched fields (adds contact data)
- Order Summaries: 1 → 12 calculated fields (adds fees, averages)

This script provides ADDITIONAL cleaning if needed:
- Remove specific columns
- Rename columns
- Filter rows based on criteria
- Merge multiple CSVs
- Apply custom transformations

Usage:
    # Remove specific columns
    python scripts/clean_csv.py input.csv --remove-columns col1,col2,col3

    # Keep only specific columns
    python scripts/clean_csv.py input.csv --keep-columns id,title,status

    # Rename columns
    python scripts/clean_csv.py input.csv --rename old_name:new_name,foo:bar

    # Filter rows
    python scripts/clean_csv.py input.csv --filter "status == 'SCHEDULED'"

    # Merge multiple CSVs
    python scripts/clean_csv.py file1.csv file2.csv --merge --output merged.csv
"""

import sys
import argparse
import pandas as pd
from pathlib import Path

def remove_columns(df, columns_to_remove):
    """Remove specified columns from dataframe."""
    columns_to_remove = [c.strip() for c in columns_to_remove.split(',')]
    existing_columns = [c for c in columns_to_remove if c in df.columns]

    if not existing_columns:
        print(f"  Warning: None of the specified columns exist in the CSV")
        return df

    print(f"  Removing {len(existing_columns)} columns: {', '.join(existing_columns)}")
    return df.drop(columns=existing_columns)


def keep_columns(df, columns_to_keep):
    """Keep only specified columns."""
    columns_to_keep = [c.strip() for c in columns_to_keep.split(',')]
    existing_columns = [c for c in columns_to_keep if c in df.columns]

    if not existing_columns:
        print(f"  Error: None of the specified columns exist in the CSV")
        return df

    missing = set(columns_to_keep) - set(existing_columns)
    if missing:
        print(f"  Warning: These columns don't exist: {', '.join(missing)}")

    print(f"  Keeping {len(existing_columns)} columns: {', '.join(existing_columns)}")
    return df[existing_columns]


def rename_columns(df, rename_map):
    """Rename columns based on mapping."""
    rename_pairs = [pair.strip().split(':') for pair in rename_map.split(',')]
    rename_dict = {old: new for old, new in rename_pairs}

    existing_renames = {old: new for old, new in rename_dict.items() if old in df.columns}

    if not existing_renames:
        print(f"  Warning: None of the columns to rename exist in the CSV")
        return df

    print(f"  Renaming {len(existing_renames)} columns:")
    for old, new in existing_renames.items():
        print(f"    {old} → {new}")

    return df.rename(columns=existing_renames)


def filter_rows(df, filter_expression):
    """Filter rows based on pandas query expression."""
    try:
        filtered_df = df.query(filter_expression)
        removed = len(df) - len(filtered_df)
        print(f"  Filter: '{filter_expression}'")
        print(f"  Kept {len(filtered_df)} rows, removed {removed} rows")
        return filtered_df
    except Exception as e:
        print(f"  Error applying filter: {e}")
        return df


def merge_csvs(file_paths):
    """Merge multiple CSV files."""
    dfs = []
    for file_path in file_paths:
        print(f"  Loading: {file_path.name}")
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        print(f"    {len(df)} rows, {len(df.columns)} columns")
        dfs.append(df)

    merged = pd.concat(dfs, ignore_index=True)
    print(f"\n  Merged result: {len(merged)} rows, {len(merged.columns)} columns")
    return merged


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Clean and post-process CSV files from transformers"
    )
    parser.add_argument(
        'input_files',
        nargs='+',
        type=str,
        help='Input CSV file(s) to process'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output file path (default: input_cleaned.csv)'
    )
    parser.add_argument(
        '--remove-columns',
        type=str,
        help='Comma-separated list of columns to remove'
    )
    parser.add_argument(
        '--keep-columns',
        type=str,
        help='Comma-separated list of columns to keep (removes all others)'
    )
    parser.add_argument(
        '--rename',
        type=str,
        help='Rename columns: old1:new1,old2:new2'
    )
    parser.add_argument(
        '--filter',
        type=str,
        help='Pandas query to filter rows (e.g., "status == \'SCHEDULED\'")'
    )
    parser.add_argument(
        '--merge',
        action='store_true',
        help='Merge multiple CSV files'
    )
    parser.add_argument(
        '--drop-duplicates',
        action='store_true',
        help='Remove duplicate rows'
    )
    parser.add_argument(
        '--drop-empty',
        action='store_true',
        help='Remove columns that are completely empty'
    )

    return parser.parse_args()


def main():
    """Main execution."""
    args = parse_args()

    print("=" * 80)
    print("CSV POST-PROCESSING")
    print("=" * 80)

    # Load input files
    input_paths = [Path(f) for f in args.input_files]

    for path in input_paths:
        if not path.exists():
            print(f"\n✗ Error: File not found: {path}")
            return 1

    # Process
    try:
        if args.merge and len(input_paths) > 1:
            print(f"\nMerging {len(input_paths)} files...")
            df = merge_csvs(input_paths)
        else:
            if len(input_paths) > 1:
                print("\n  Warning: Multiple files provided but --merge not specified")
                print("  Processing only the first file\n")

            input_path = input_paths[0]
            print(f"\nLoading: {input_path.name}")
            df = pd.read_csv(input_path, encoding='utf-8-sig')
            print(f"  {len(df)} rows, {len(df.columns)} columns")

        print(f"\nOriginal data:")
        print(f"  Rows: {len(df)}")
        print(f"  Columns: {len(df.columns)}")

        # Apply transformations
        print("\nApplying transformations...")

        if args.drop_empty:
            before = len(df.columns)
            df = df.dropna(axis=1, how='all')
            removed = before - len(df.columns)
            if removed > 0:
                print(f"  Removed {removed} completely empty columns")

        if args.remove_columns:
            df = remove_columns(df, args.remove_columns)

        if args.keep_columns:
            df = keep_columns(df, args.keep_columns)

        if args.rename:
            df = rename_columns(df, args.rename)

        if args.filter:
            df = filter_rows(df, args.filter)

        if args.drop_duplicates:
            before = len(df)
            df = df.drop_duplicates()
            removed = before - len(df)
            if removed > 0:
                print(f"  Removed {removed} duplicate rows")

        # Save output
        if args.output:
            output_path = Path(args.output)
        else:
            input_path = input_paths[0]
            output_path = input_path.parent / f"{input_path.stem}_cleaned{input_path.suffix}"

        print(f"\nSaving to: {output_path.name}")
        df.to_csv(output_path, index=False, encoding='utf-8-sig')

        print(f"\nFinal data:")
        print(f"  Rows: {len(df)}")
        print(f"  Columns: {len(df.columns)}")

        print("\n" + "=" * 80)
        print(f"✓ Processing complete: {output_path}")
        print("=" * 80)

        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
