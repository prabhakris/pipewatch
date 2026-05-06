"""Tests for pipewatch.anomaly module."""

import pytest
from pipewatch.anomaly import AnomalyDetector, AnomalyResult
from pipewatch.metrics import PipelineMetric
from datetime import datetime


def make_metric(pipeline_name="test_pipe", records=100, failed=5, duration=10.0):
    return PipelineMetric(
        pipeline_name=pipeline_name,
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        records_processed=records,
        records_failed=failed,
        duration_seconds=duration,
    )


class TestAnomalyDetector:
    def test_returns_none_below_min_samples(self):
        detector = AnomalyDetector(min_samples=5)
        metric = make_metric()
        for _ in range(4):
            result = detector.detect(metric, "failure_rate")
        assert result is None

    def test_returns_result_at_min_samples(self):
        detector = AnomalyDetector(min_samples=5)
        metric = make_metric()
        result = None
        for _ in range(5):
            result = detector.detect(metric, "failure_rate")
        assert isinstance(result, AnomalyResult)

    def test_no_anomaly_for_stable_values(self):
        detector = AnomalyDetector(min_samples=5, z_score_threshold=2.5)
        metrics = [make_metric(failed=5) for _ in range(5)]
        result = None
        for m in metrics:
            result = detector.detect(m, "failure_rate")
        assert result is not None
        assert result.is_anomaly is False

    def test_anomaly_detected_for_spike(self):
        detector = AnomalyDetector(min_samples=5, z_score_threshold=2.0)
        stable = [make_metric(failed=1) for _ in range(4)]
        spike = make_metric(failed=90)
        for m in stable:
            detector.detect(m, "failure_rate")
        result = detector.detect(spike, "failure_rate")
        assert result is not None
        assert result.is_anomaly is True

    def test_invalid_metric_name_raises(self):
        detector = AnomalyDetector(min_samples=3)
        metric = make_metric()
        with pytest.raises(ValueError, match="Unknown metric"):
            detector.detect(metric, "nonexistent_metric")

    def test_clear_resets_history(self):
        detector = AnomalyDetector(min_samples=3)
        metric = make_metric()
        for _ in range(3):
            detector.detect(metric, "failure_rate")
        detector.clear()
        result = detector.detect(metric, "failure_rate")
        assert result is None

    def test_to_dict_contains_expected_keys(self):
        detector = AnomalyDetector(min_samples=3)
        metric = make_metric()
        result = None
        for _ in range(3):
            result = detector.detect(metric, "failure_rate")
        assert result is not None
        d = result.to_dict()
        for key in ("pipeline_name", "metric_name", "value", "mean", "std_dev", "z_score", "is_anomaly", "threshold"):
            assert key in d
