"""Registry for managing per-pipeline AnomalyDetector instances."""

from typing import Dict, List, Optional, Tuple

from pipewatch.anomaly import AnomalyDetector, AnomalyResult
from pipewatch.metrics import PipelineMetric

# Metrics watched by default
DEFAULT_WATCHED_METRICS: List[str] = ["failure_rate", "throughput"]


class DetectorRegistry:
    """Maintains a pool of AnomalyDetectors keyed by (pipeline, metric)."""

    def __init__(
        self,
        watched_metrics: Optional[List[str]] = None,
        z_score_threshold: float = 2.5,
        min_samples: int = 5,
    ) -> None:
        self.watched_metrics = watched_metrics or DEFAULT_WATCHED_METRICS
        self.z_score_threshold = z_score_threshold
        self.min_samples = min_samples
        self._detectors: Dict[Tuple[str, str], AnomalyDetector] = {}

    def _get_or_create(self, pipeline_name: str, metric_name: str) -> AnomalyDetector:
        key = (pipeline_name, metric_name)
        if key not in self._detectors:
            self._detectors[key] = AnomalyDetector(
                z_score_threshold=self.z_score_threshold,
                min_samples=self.min_samples,
            )
        return self._detectors[key]

    def evaluate(self, metric: PipelineMetric) -> List[AnomalyResult]:
        """Run anomaly detection for all watched metrics on a PipelineMetric.

        Returns a list of AnomalyResult objects (only non-None results).
        """
        results: List[AnomalyResult] = []
        for metric_name in self.watched_metrics:
            detector = self._get_or_create(metric.pipeline_name, metric_name)
            result = detector.detect(metric, metric_name)
            if result is not None:
                results.append(result)
        return results

    def reset(self, pipeline_name: Optional[str] = None) -> None:
        """Clear history for a specific pipeline or all pipelines."""
        if pipeline_name is None:
            for detector in self._detectors.values():
                detector.clear()
        else:
            for (pname, _), detector in self._detectors.items():
                if pname == pipeline_name:
                    detector.clear()
