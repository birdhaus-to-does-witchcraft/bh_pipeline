"""
Run manifest utility for pipeline observability.

Tracks per-entity extraction stats (row counts, file paths, durations, errors)
and writes a single JSON manifest file per pipeline run.
"""

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class EntityStats:
    """Per-entity extraction statistics."""
    status: str = "pending"
    row_count: int = 0
    raw_path: Optional[str] = None
    csv_path: Optional[str] = None
    extra_paths: Dict[str, str] = field(default_factory=dict)
    duration_ms: int = 0
    error: Optional[str] = None


class RunManifest:
    """
    Accumulates per-entity stats during a pipeline run and writes a JSON manifest.

    Usage:
        >>> manifest = RunManifest("20260113_142022", output_dir)
        >>> with manifest.timer("events") as timer:
        ...     # ... do work ...
        ...     timer.record(status="success", row_count=47, csv_path=str(path))
        >>> manifest.save()
    """

    def __init__(self, run_timestamp: str, output_dir: Path):
        self.run_timestamp = run_timestamp
        self.output_dir = output_dir
        self.start_time = datetime.now(timezone.utc)
        self.entities: Dict[str, EntityStats] = {}

    def record(
        self,
        entity: str,
        *,
        status: str,
        row_count: int = 0,
        raw_path: Optional[Path] = None,
        csv_path: Optional[Path] = None,
        extra_paths: Optional[Dict[str, Path]] = None,
        duration_ms: int = 0,
        error: Optional[str] = None,
    ):
        """Record stats for one entity."""
        self.entities[entity] = EntityStats(
            status=status,
            row_count=row_count,
            raw_path=str(raw_path) if raw_path else None,
            csv_path=str(csv_path) if csv_path else None,
            extra_paths={k: str(v) for k, v in (extra_paths or {}).items()},
            duration_ms=duration_ms,
            error=error,
        )

    def timer(self, entity: str) -> "EntityTimer":
        """Context manager that auto-records duration for an entity."""
        return EntityTimer(self, entity)

    def save(self) -> Path:
        """Write the manifest to data/processed/manifest_<run_timestamp>.json."""
        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - self.start_time).total_seconds() * 1000)
        total_records = sum(e.row_count for e in self.entities.values())

        successful = sum(1 for e in self.entities.values() if e.status == "success")
        failed = sum(1 for e in self.entities.values() if e.status == "failed")
        skipped = sum(1 for e in self.entities.values() if e.status == "skipped")

        manifest_data = {
            "snapshot_id": self.run_timestamp,
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_ms": duration_ms,
            "total_records": total_records,
            "summary": {
                "successful": successful,
                "failed": failed,
                "skipped": skipped,
                "total_entities": len(self.entities),
            },
            "entities": {name: asdict(stats) for name, stats in self.entities.items()},
        }

        manifest_path = self.output_dir / f"manifest_{self.run_timestamp}.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)

        logger.info(
            f"Wrote manifest to {manifest_path} "
            f"({successful}/{len(self.entities)} successful, {total_records} total records, "
            f"{duration_ms}ms)"
        )
        return manifest_path


class EntityTimer:
    """Context manager that measures duration and records to a manifest."""

    def __init__(self, manifest: RunManifest, entity: str):
        self.manifest = manifest
        self.entity = entity
        self._start: float = 0.0
        self._recorded = False

    def __enter__(self) -> "EntityTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._recorded:
            duration_ms = int((time.perf_counter() - self._start) * 1000)
            if exc_type is not None:
                self.manifest.record(
                    self.entity,
                    status="failed",
                    duration_ms=duration_ms,
                    error=f"{exc_type.__name__}: {exc_val}",
                )
            else:
                self.manifest.record(
                    self.entity,
                    status="skipped",
                    duration_ms=duration_ms,
                )
        return False

    def record(
        self,
        *,
        status: str = "success",
        row_count: int = 0,
        raw_path: Optional[Path] = None,
        csv_path: Optional[Path] = None,
        extra_paths: Optional[Dict[str, Path]] = None,
        error: Optional[str] = None,
    ):
        """Record entity stats. Auto-computes duration."""
        duration_ms = int((time.perf_counter() - self._start) * 1000)
        self.manifest.record(
            self.entity,
            status=status,
            row_count=row_count,
            raw_path=raw_path,
            csv_path=csv_path,
            extra_paths=extra_paths,
            duration_ms=duration_ms,
            error=error,
        )
        self._recorded = True
