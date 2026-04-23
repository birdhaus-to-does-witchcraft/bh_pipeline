"""Re-emit silver CSVs from existing bronze JSON (no API calls).

Use this after changing a transformer schema (e.g. adding a new column) so the
silver layer matches the new transformer logic without re-pulling from Wix.

Currently re-emits:
- guests_<timestamp>.csv (with contacts join)
- events_<timestamp>.csv

Usage:
    python scripts/rebuild_silver_views.py
    python scripts/rebuild_silver_views.py --snapshot 20260422_205516
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from transformers.base import BaseTransformer
from transformers.events import EventsTransformer
from transformers.guests import GuestsTransformer

SNAPSHOT_RE = re.compile(r"snapshot_(\d{8}_\d{6})\.json$")


def _list_snapshots(raw_dir: Path) -> List[str]:
    snapshots = set()
    for f in raw_dir.glob("guests/year=*/month=*/day=*/snapshot_*.json"):
        m = SNAPSHOT_RE.search(f.name)
        if m:
            snapshots.add(m.group(1))
    return sorted(snapshots, reverse=True)


def _load_raw(raw_dir: Path, entity: str, snapshot: str) -> List[Dict[str, Any]]:
    matches = list(raw_dir.glob(f"{entity}/year=*/month=*/day=*/snapshot_{snapshot}.json"))
    if not matches:
        return []
    with open(matches[0], encoding="utf-8") as f:
        return json.load(f)


def rebuild_for_snapshot(snapshot: str, raw_dir: Path, processed_dir: Path) -> None:
    print(f"Rebuilding silver CSVs for snapshot {snapshot}")

    # Events (re-emit so primary_category column is dropped, etc.)
    raw_events = _load_raw(raw_dir, "events", snapshot)
    if raw_events:
        ticketing = [e for e in raw_events if e.get("registration", {}).get("type") == "TICKETING"]
        rsvp = [e for e in raw_events if e.get("registration", {}).get("type") == "RSVP"]
        if ticketing:
            transformed = EventsTransformer.transform_events(ticketing)
            out = processed_dir / f"events_{snapshot}.csv"
            BaseTransformer.save_to_csv(transformed, str(out))
            print(f"  events:       {len(transformed)} rows -> {out.name}")
        if rsvp:
            transformed = EventsTransformer.transform_events(rsvp)
            out = processed_dir / f"rsvp_events_{snapshot}.csv"
            BaseTransformer.save_to_csv(transformed, str(out))
            print(f"  rsvp_events:  {len(transformed)} rows -> {out.name}")

    # Guests (re-emit so order_status column is added, plus contacts enrichment)
    raw_guests = _load_raw(raw_dir, "guests", snapshot)
    if raw_guests:
        # Match the production filter: drop guests tied to RSVP-type events
        rsvp_event_ids = {
            e.get("id") for e in raw_events
            if e.get("registration", {}).get("type") == "RSVP"
        }
        ticketing_guests = [g for g in raw_guests if g.get("eventId") not in rsvp_event_ids]
        transformed = GuestsTransformer.transform_guests(ticketing_guests)

        raw_contacts = _load_raw(raw_dir, "contacts", snapshot)
        if raw_contacts:
            transformed = GuestsTransformer.enrich_with_contact_data(
                transformed, raw_contacts
            )
            print(f"  guests enrichment: {len(raw_contacts)} contacts joined")

        out = processed_dir / f"guests_{snapshot}.csv"
        BaseTransformer.save_to_csv(transformed, str(out))
        print(f"  guests:       {len(transformed)} rows -> {out.name}")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", help="Snapshot timestamp (default: latest)")
    parser.add_argument(
        "--raw-dir", type=Path,
        default=project_root / "data" / "raw",
    )
    parser.add_argument(
        "--processed-dir", type=Path,
        default=project_root / "data" / "processed",
    )
    parser.add_argument("--all", action="store_true", help="Rebuild every snapshot found")
    return parser.parse_args()


def main():
    args = parse_args()
    snapshots = _list_snapshots(args.raw_dir)
    if not snapshots:
        raise SystemExit(f"No bronze snapshots found in {args.raw_dir}")

    if args.all:
        targets = snapshots
    elif args.snapshot:
        if args.snapshot not in snapshots:
            raise SystemExit(f"Snapshot {args.snapshot} not found")
        targets = [args.snapshot]
    else:
        targets = [snapshots[0]]
        print(f"No --snapshot given; using latest: {targets[0]}")

    args.processed_dir.mkdir(parents=True, exist_ok=True)
    for snap in targets:
        rebuild_for_snapshot(snap, args.raw_dir, args.processed_dir)


if __name__ == "__main__":
    main()
