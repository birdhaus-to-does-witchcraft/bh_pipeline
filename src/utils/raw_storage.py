"""
Raw JSON storage utility for the bronze layer of the data lake.

Persists unmodified API responses to a date-partitioned directory structure
that downstream tools (DuckDB, Spark, pandas) can query as a Hive-style table.
"""

import json
import logging
from pathlib import Path
from typing import Any, List

logger = logging.getLogger(__name__)


def dump_raw(
    entity_name: str,
    data: List[Any],
    run_timestamp: str,
    raw_root: Path,
) -> Path:
    """
    Write raw API data to date-partitioned JSON file.

    Output path:
        <raw_root>/<entity_name>/year=YYYY/month=MM/day=DD/snapshot_<run_timestamp>.json

    Args:
        entity_name: Lowercase entity slug (e.g. "events", "members")
        data: Raw list of records as returned by the API wrappers
        run_timestamp: Run timestamp in YYYYMMDD_HHMMSS format
        raw_root: Root directory for raw bronze data (e.g. project_root/data/raw)

    Returns:
        Path to the written JSON file.
    """
    if len(run_timestamp) < 8:
        raise ValueError(f"run_timestamp must be in YYYYMMDD_HHMMSS format, got: {run_timestamp}")

    year = run_timestamp[0:4]
    month = run_timestamp[4:6]
    day = run_timestamp[6:8]

    target_dir = raw_root / entity_name / f"year={year}" / f"month={month}" / f"day={day}"
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / f"snapshot_{run_timestamp}.json"

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    logger.info(f"Wrote {len(data)} raw {entity_name} records to {target_path}")
    return target_path
