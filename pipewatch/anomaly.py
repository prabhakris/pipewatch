"""Anomaly detection for pipeline metrics using statistical methods."""

from dataclasses import dataclass, field
from typing import List, Optional
from statistics import mean, stdev

from pipewatch.metrics import PipelineMetric


@dataclass
class AnomalyResult:
    """Result of an anomaly detection check."""
    pipeline_name: str
    metric_name: str
    value: float
    mean: float
    std_dev: float
    z_score: float
    is_anomaly: bool
    threshold: float

    def to_dict(self) -> dict:
        return {
            "pipeline_name": self.pipeline_name,
            "metric_name": self.metric_name,
            "value": self.value,
            "mean": round(self.mean, 4),
            "std_dev": round(self.std_dev, 4),
            "z_score": round(self.z_score, 4),
            "is_anomaly": self.is_anomaly,
            "threshold": self.threshold,
        }


@dataclass
class AnomalyDetector:
    """Detects anomalies in pipeline metrics using Z-score analysis."""
    z_score_threshold: float = 2.5
    min_samples: int = 5
    _history: List[float] = field(default_factory=list, repr=False)

    def add_sample(self, value: float) -> None:
        """Add a metric value to the historical sample window."""
        self._history.append(value)

    def clear(self) -> None:
        """Clear historical samples."""
        self._history.clear()

    def detect(self, metric: PipelineMetric, metric_name: str) -> Optional[AnomalyResult]:
        """Evaluate a metric value against historical data.

        Returns an AnomalyResult if enough samples exist, otherwise None.
        """
        value = getattr(metric, metric_name, None)
        if value is None:
            raise ValueError(f"Unknown metric: '{metric_name}'")

        self.add_sample(value)

        if len(self._history) < self.min_samples:
            return None

        mu = mean(self._history)
        sigma = stdev(self._history)

        if sigma == 0:
            z = 0.0
        else:
            z = abs((value - mu) / sigma)

        return AnomalyResult(
            pipeline_name=metric.pipeline_name,
            metric_name=metric_name,
            value=value,
            mean=mu,
            std_dev=sigma,
            z_score=z,
            is_anomaly=z > self.z_score_threshold,
            threshold=self.z_score_threshold,
        )
