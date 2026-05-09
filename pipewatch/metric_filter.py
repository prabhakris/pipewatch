"""Filtering utilities for PipelineMetric collections."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from pipewatch.metrics import PipelineMetric


@dataclass
class MetricFilter:
    """Composable filter for PipelineMetric lists.

    Filters are ANDed together: a metric must satisfy every
    configured predicate to pass through.
    """

    pipeline_ids: Optional[List[str]] = None
    min_records: Optional[int] = None
    max_failure_rate: Optional[float] = None
    min_throughput: Optional[float] = None
    custom: List[Callable[[PipelineMetric], bool]] = field(default_factory=list)

    def matches(self, metric: PipelineMetric) -> bool:
        """Return True if *metric* satisfies all configured predicates."""
        if self.pipeline_ids is not None:
            if metric.pipeline_id not in self.pipeline_ids:
                return False

        if self.min_records is not None:
            if metric.total_records < self.min_records:
                return False

        if self.max_failure_rate is not None:
            rate = metric.failure_rate()
            if rate > self.max_failure_rate:
                return False

        if self.min_throughput is not None:
            tp = metric.throughput()
            if tp < self.min_throughput:
                return False

        for predicate in self.custom:
            if not predicate(metric):
                return False

        return True

    def apply(self, metrics: List[PipelineMetric]) -> List[PipelineMetric]:
        """Return a new list containing only metrics that pass the filter."""
        return [m for m in metrics if self.matches(m)]
