"""Core metrics collection module for ETL pipeline observability."""

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PipelineMetric:
    """Represents a single metric snapshot for a pipeline stage."""

    pipeline_name: str
    stage: str
    records_processed: int
    records_failed: int
    duration_seconds: float
    timestamp: float = field(default_factory=time.time)

    @property
    def failure_rate(self) -> float:
        """Return the fraction of records that failed (0.0 to 1.0)."""
        total = self.records_processed + self.records_failed
        if total == 0:
            return 0.0
        return self.records_failed / total

    @property
    def throughput(self) -> float:
        """Return records processed per second."""
        if self.duration_seconds <= 0:
            return 0.0
        return self.records_processed / self.duration_seconds

    def to_dict(self) -> dict:
        """Serialize metric to a plain dictionary."""
        return {
            "pipeline_name": self.pipeline_name,
            "stage": self.stage,
            "records_processed": self.records_processed,
            "records_failed": self.records_failed,
            "duration_seconds": self.duration_seconds,
            "failure_rate": round(self.failure_rate, 4),
            "throughput": round(self.throughput, 4),
            "timestamp": self.timestamp,
        }


class MetricsCollector:
    """Accumulates pipeline metrics in memory for inspection and alerting."""

    def __init__(self, max_history: int = 1000) -> None:
        self._history: list[PipelineMetric] = []
        self.max_history = max_history

    def record(self, metric: PipelineMetric) -> None:
        """Add a metric snapshot, evicting oldest if capacity is exceeded."""
        self._history.append(metric)
        if len(self._history) > self.max_history:
            self._history.pop(0)

    def latest(self, pipeline_name: str, stage: Optional[str] = None) -> Optional[PipelineMetric]:
        """Return the most recent metric for the given pipeline (and optional stage)."""
        matches = [
            m for m in reversed(self._history)
            if m.pipeline_name == pipeline_name
            and (stage is None or m.stage == stage)
        ]
        return matches[0] if matches else None

    def all_metrics(self) -> list[dict]:
        """Return all stored metrics as a list of dictionaries."""
        return [m.to_dict() for m in self._history]

    def clear(self) -> None:
        """Remove all stored metrics."""
        self._history.clear()
