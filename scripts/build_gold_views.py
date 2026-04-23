"""
Rebuild gold-layer views from existing silver CSVs (no API calls).

Useful for:
- Backfilling the gold layer for a snapshot taken before the gold step existed
- Iterating on gold-layer schema without re-running the full extraction
- Local experimentation against the latest data already on disk

Currently builds:
- attendance_fact_<timestamp>.csv  (one row per attendee, all dims joined)
- payments_fact_<timestamp>.csv    (one row per payment, event/member dims joined)

Usage:
    python scripts/build_gold_views.py
    python scripts/build_gold_views.py --snapshot 20260422_205516
    python scripts/build_gold_views.py --processed-dir /path/to/processed
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import pandas as pd

from transformers.attendance_fact import AttendanceFactTransformer
from transformers.payments_fact import PaymentsFactTransformer
from transformers.base import BaseTransformer
from transformers.guests import GuestsTransformer

SNAPSHOT_RE = re.compile(r"_(\d{8}_\d{6})\.csv$")


def _list_snapshots(processed_dir: Path) -> List[str]:
    """Return all snapshot timestamps present in the processed dir, newest first."""
    snapshots = set()
    for f in processed_dir.glob("*.csv"):
        m = SNAPSHOT_RE.search(f.name)
        if m:
            snapshots.add(m.group(1))
    return sorted(snapshots, reverse=True)


def _read_csv_or_empty(path: Path) -> List[Dict[str, Any]]:
    """
    Read a silver CSV back into a list of dicts.

    We let pandas infer dtypes so booleans come back as actual True/False
    (not the strings "True"/"False" which would be silently truthy under
    plain bool()), then scrub all NaN values to None so downstream code
    can treat missing values uniformly without `isnan` checks.
    """
    if not path.exists():
        return []
    df = pd.read_csv(path)
    records = df.to_dict(orient="records")
    for row in records:
        for k, v in list(row.items()):
            # Catches np.nan (float), pd.NaT, and pd.NA across dtypes
            if v is None or (isinstance(v, float) and v != v) or pd.isna(v):
                row[k] = None
    return records


def _read_raw_contacts_or_empty(raw_dir: Path, snapshot: str) -> List[Dict[str, Any]]:
    """Find the contacts bronze JSON for a given snapshot, if it exists."""
    matches = list(raw_dir.glob(f"contacts/year=*/month=*/day=*/snapshot_{snapshot}.json"))
    if not matches:
        return []
    with open(matches[0], encoding="utf-8") as f:
        return json.load(f)


def build_for_snapshot(
    snapshot: str,
    processed_dir: Path,
    raw_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> Path:
    """Build attendance_fact from the silver CSVs of a single snapshot."""
    output_dir = output_dir or processed_dir

    print(f"Building gold views for snapshot {snapshot}")
    print(f"  Reading silver from: {processed_dir}")

    transformed_guests = _read_csv_or_empty(processed_dir / f"guests_{snapshot}.csv")
    transformed_events = _read_csv_or_empty(processed_dir / f"events_{snapshot}.csv")
    transformed_contacts = _read_csv_or_empty(processed_dir / f"contacts_{snapshot}.csv")
    transformed_members = _read_csv_or_empty(processed_dir / f"members_{snapshot}.csv")
    transformed_defs = _read_csv_or_empty(processed_dir / f"ticket_definitions_{snapshot}.csv")
    transformed_tickets = _read_csv_or_empty(processed_dir / f"tickets_{snapshot}.csv")
    transformed_summaries = _read_csv_or_empty(processed_dir / f"order_summaries_{snapshot}.csv")
    transformed_payments = _read_csv_or_empty(processed_dir / f"payments_{snapshot}.csv")
    transformed_event_orders = _read_csv_or_empty(processed_dir / f"event_orders_{snapshot}.csv")

    print(
        f"  Loaded: {len(transformed_guests)} guests, {len(transformed_events)} events, "
        f"{len(transformed_contacts)} contacts, {len(transformed_members)} members, "
        f"{len(transformed_defs)} ticket_defs, {len(transformed_tickets)} tickets, "
        f"{len(transformed_summaries)} order_summaries, "
        f"{len(transformed_payments)} payments, {len(transformed_event_orders)} event_orders"
    )

    # If raw contacts are still on disk, retroactively enrich the guest rows
    # with name/email/phone (the silver guests CSV from older snapshots may
    # have been written before that join existed).
    if raw_dir and transformed_guests:
        raw_contacts = _read_raw_contacts_or_empty(raw_dir, snapshot)
        if raw_contacts:
            print(f"  Enriching guests with {len(raw_contacts)} raw contacts...")
            transformed_guests = GuestsTransformer.enrich_with_contact_data(
                transformed_guests, raw_contacts
            )

    if transformed_guests:
        rows = AttendanceFactTransformer.build(
            transformed_guests=transformed_guests,
            transformed_events=transformed_events,
            transformed_contacts=transformed_contacts,
            transformed_members=transformed_members,
            transformed_ticket_definitions=transformed_defs,
            transformed_tickets=transformed_tickets,
            transformed_order_summaries=transformed_summaries,
            transformed_payments=transformed_payments,
        )
        attendance_path = output_dir / f"attendance_fact_{snapshot}.csv"
        BaseTransformer.save_to_csv(rows, str(attendance_path))
        print(f"  Wrote {len(rows)} attendee rows -> {attendance_path.name}")
    else:
        attendance_path = None
        print("  Skipping attendance_fact (no guests CSV for snapshot)")

    if transformed_payments:
        payment_rows = PaymentsFactTransformer.build(
            transformed_payments=transformed_payments,
            transformed_event_orders=transformed_event_orders,
            transformed_events=transformed_events,
            transformed_contacts=transformed_contacts,
            transformed_members=transformed_members,
            transformed_order_summaries=transformed_summaries,
        )
        payments_path = output_dir / f"payments_fact_{snapshot}.csv"
        BaseTransformer.save_to_csv(payment_rows, str(payments_path))
        print(f"  Wrote {len(payment_rows)} payment rows -> {payments_path.name}")
    else:
        payments_path = None
        print("  Skipping payments_fact (no payments CSV for snapshot)")

    if not attendance_path and not payments_path:
        raise SystemExit(
            f"Neither guests nor payments CSV present for snapshot {snapshot} - "
            "nothing to build"
        )
    return attendance_path or payments_path


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot",
        help="Snapshot timestamp to build (e.g. 20260422_205516). Defaults to latest.",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=project_root / "data" / "processed",
        help="Directory containing silver CSVs",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=project_root / "data" / "raw",
        help="Bronze JSON directory (used to retroactively enrich guests with contacts)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Where to write the gold CSV (default: same as processed-dir)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Build for every snapshot found in processed-dir",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if not args.processed_dir.exists():
        raise SystemExit(f"Processed dir not found: {args.processed_dir}")

    snapshots = _list_snapshots(args.processed_dir)
    if not snapshots:
        raise SystemExit(f"No snapshot CSVs found in {args.processed_dir}")

    if args.all:
        targets = snapshots
    elif args.snapshot:
        if args.snapshot not in snapshots:
            raise SystemExit(
                f"Snapshot {args.snapshot} not found. Available: {', '.join(snapshots[:5])}..."
            )
        targets = [args.snapshot]
    else:
        targets = [snapshots[0]]
        print(f"No --snapshot given; using latest: {targets[0]}")

    for snap in targets:
        build_for_snapshot(snap, args.processed_dir, args.raw_dir, args.output_dir)


if __name__ == "__main__":
    main()
