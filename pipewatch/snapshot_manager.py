"""High-level manager that wires SnapshotStore into the pipeline runner loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from pipewatch.health import HealthReport, compute_health
from pipewatch.pipeline_runner import RunReport
from pipewatch.snapshot import PipelineSnapshot, SnapshotStore


@dataclass
class SnapshotManager:
    """Wraps a SnapshotStore and provides convenience methods for the agent loop."""

    persist_path: str | Path | None = None
    _store: SnapshotStore = field(default_factory=SnapshotStore, init=False)

    def __post_init__(self) -> None:
        if self.persist_path is not None:
            self._store.load(self.persist_path)

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def ingest(self, run_report: RunReport) -> PipelineSnapshot:
        """Convert a RunReport to a HealthReport, snapshot it, and optionally persist."""
        health = compute_health(
            pipeline_id=run_report.pipeline_id,
            metric=run_report.metric,
            alerts=run_report.alerts,
            anomalies=run_report.anomalies,
        )
        snap = self._store.record(run_report.pipeline_id, health)
        if self.persist_path is not None:
            self._store.save(self.persist_path)
        return snap

    def latest(self, pipeline_id: str) -> PipelineSnapshot | None:
        """Return the most recent snapshot for *pipeline_id*."""
        return self._store.latest(pipeline_id)

    def history(self, pipeline_id: str) -> list[PipelineSnapshot]:
        """Return all recorded snapshots for *pipeline_id*."""
        return self._store.all_for(pipeline_id)

    def trend(
        self,
        pipeline_id: str,
        window: int = 5,
        key: str = "score",
        extractor: Callable[[PipelineSnapshot], float] | None = None,
    ) -> list[float]:
        """Return the last *window* values of *key* from the health dict."""
        snaps = self._store.all_for(pipeline_id)[-window:]
        if extractor is not None:
            return [extractor(s) for s in snaps]
        return [s.health.get(key, 0.0) for s in snaps]

    def reset(self) -> None:
        """Clear all in-memory snapshots (does not delete the persist file)."""
        self._store.clear()
