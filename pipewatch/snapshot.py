"""Snapshot module: captures and persists pipeline state at a point in time."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pipewatch.health import HealthReport


@dataclass
class PipelineSnapshot:
    """Immutable record of a pipeline's health at a specific timestamp."""

    pipeline_id: str
    captured_at: float
    health: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "captured_at": self.captured_at,
            "health": self.health,
        }


@dataclass
class SnapshotStore:
    """In-memory store with optional file persistence for pipeline snapshots."""

    _snapshots: list[PipelineSnapshot] = field(default_factory=list)

    def record(self, pipeline_id: str, report: HealthReport) -> PipelineSnapshot:
        """Capture current health report as a snapshot."""
        snap = PipelineSnapshot(
            pipeline_id=pipeline_id,
            captured_at=time.time(),
            health=report.to_dict(),
        )
        self._snapshots.append(snap)
        return snap

    def latest(self, pipeline_id: str) -> PipelineSnapshot | None:
        """Return the most recent snapshot for a given pipeline."""
        matches = [s for s in self._snapshots if s.pipeline_id == pipeline_id]
        return matches[-1] if matches else None

    def all_for(self, pipeline_id: str) -> list[PipelineSnapshot]:
        """Return all snapshots for a given pipeline in chronological order."""
        return [s for s in self._snapshots if s.pipeline_id == pipeline_id]

    def save(self, path: str | Path) -> None:
        """Persist all snapshots to a JSON Lines file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            for snap in self._snapshots:
                fh.write(json.dumps(snap.to_dict()) + "\n")

    def load(self, path: str | Path) -> None:
        """Load snapshots from a JSON Lines file, appending to current store."""
        path = Path(path)
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                self._snapshots.append(
                    PipelineSnapshot(
                        pipeline_id=data["pipeline_id"],
                        captured_at=data["captured_at"],
                        health=data["health"],
                    )
                )

    def clear(self) -> None:
        """Remove all stored snapshots."""
        self._snapshots.clear()
