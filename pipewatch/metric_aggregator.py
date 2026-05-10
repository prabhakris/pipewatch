"""Aggregate metrics across multiple pipeline runs into summary statistics."""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, median, stdev
from typing import Dict, List, Optional

from pipewatch.metrics import PipelineMetric


@dataclass
class MetricSummary:
    """Summary statistics for a single pipeline's metrics over time."""

    pipeline_id: str
    samples: int = 0
    mean_failure_rate: float = 0.0
    median_failure_rate: float = 0.0
    stddev_failure_rate: float = 0.0
    mean_throughput: float = 0.0
    min_throughput: float = 0.0
    max_throughput: float = 0.0

    def to_dict(self) -> dict:
        return {
            "pipeline_id": self.pipeline_id,
            "samples": self.samples,
            "mean_failure_rate": round(self.mean_failure_rate, 6),
            "median_failure_rate": round(self.median_failure_rate, 6),
            "stddev_failure_rate": round(self.stddev_failure_rate, 6),
            "mean_throughput": round(self.mean_throughput, 4),
            "min_throughput": round(self.min_throughput, 4),
            "max_throughput": round(self.max_throughput, 4),
        }


@dataclass
class MetricAggregator:
    """Accumulates PipelineMetric samples and produces per-pipeline summaries."""

    _buckets: Dict[str, List[PipelineMetric]] = field(default_factory=dict, init=False)

    def ingest(self, metric: PipelineMetric) -> None:
        """Add a metric sample to the appropriate pipeline bucket."""
        self._buckets.setdefault(metric.pipeline_id, []).append(metric)

    def summarize(self, pipeline_id: str) -> Optional[MetricSummary]:
        """Return a MetricSummary for *pipeline_id*, or None if no data exists."""
        samples = self._buckets.get(pipeline_id)
        if not samples:
            return None

        failure_rates = [m.failure_rate() for m in samples]
        throughputs = [m.throughput() for m in samples]
        n = len(samples)

        return MetricSummary(
            pipeline_id=pipeline_id,
            samples=n,
            mean_failure_rate=mean(failure_rates),
            median_failure_rate=median(failure_rates),
            stddev_failure_rate=stdev(failure_rates) if n > 1 else 0.0,
            mean_throughput=mean(throughputs),
            min_throughput=min(throughputs),
            max_throughput=max(throughputs),
        )

    def all_summaries(self) -> List[MetricSummary]:
        """Return summaries for every tracked pipeline, sorted by pipeline_id."""
        return [
            s
            for pid in sorted(self._buckets)
            for s in [self.summarize(pid)]
            if s is not None
        ]

    def reset(self, pipeline_id: Optional[str] = None) -> None:
        """Clear data for one pipeline or all pipelines when *pipeline_id* is None."""
        if pipeline_id is None:
            self._buckets.clear()
        else:
            self._buckets.pop(pipeline_id, None)

    @property
    def tracked_pipelines(self) -> List[str]:
        return sorted(self._buckets.keys())
