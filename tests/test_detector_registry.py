"""Tests for pipewatch.detector_registry module."""

from datetime import datetime
from pipewatch.detector_registry import DetectorRegistry
from pipewatch.metrics import PipelineMetric


def make_metric(pipeline_name="pipe_a", records=200, failed=4, duration=8.0):
    return PipelineMetric(
        pipeline_name=pipeline_name,
        timestamp=datetime(2024, 6, 1, 9, 0, 0),
        records_processed=records,
        records_failed=failed,
        duration_seconds=duration,
    )


class TestDetectorRegistry:
    def test_returns_empty_list_before_min_samples(self):
        registry = DetectorRegistry(min_samples=5)
        metric = make_metric()
        results = registry.evaluate(metric)
        assert results == []

    def test_returns_results_after_min_samples(self):
        registry = DetectorRegistry(min_samples=3)
        metric = make_metric()
        results = []
        for _ in range(3):
            results = registry.evaluate(metric)
        assert len(results) == len(registry.watched_metrics)

    def test_separate_detectors_per_pipeline(self):
        registry = DetectorRegistry(min_samples=3)
        for _ in range(3):
            registry.evaluate(make_metric(pipeline_name="pipe_a"))
        # pipe_b has no history yet
        results_b = registry.evaluate(make_metric(pipeline_name="pipe_b"))
        assert results_b == []

    def test_anomaly_flagged_across_registry(self):
        registry = DetectorRegistry(min_samples=5, z_score_threshold=2.0)
        stable = make_metric(failed=1)
        spike = make_metric(failed=95)
        for _ in range(4):
            registry.evaluate(stable)
        results = registry.evaluate(spike)
        anomalies = [r for r in results if r.is_anomaly]
        assert len(anomalies) >= 1

    def test_reset_specific_pipeline(self):
        registry = DetectorRegistry(min_samples=3)
        for _ in range(3):
            registry.evaluate(make_metric(pipeline_name="pipe_a"))
        registry.reset(pipeline_name="pipe_a")
        results = registry.evaluate(make_metric(pipeline_name="pipe_a"))
        assert results == []

    def test_reset_all_pipelines(self):
        registry = DetectorRegistry(min_samples=3)
        for name in ("pipe_a", "pipe_b"):
            for _ in range(3):
                registry.evaluate(make_metric(pipeline_name=name))
        registry.reset()
        for name in ("pipe_a", "pipe_b"):
            results = registry.evaluate(make_metric(pipeline_name=name))
            assert results == []

    def test_custom_watched_metrics(self):
        registry = DetectorRegistry(watched_metrics=["failure_rate"], min_samples=3)
        metric = make_metric()
        results = []
        for _ in range(3):
            results = registry.evaluate(metric)
        assert all(r.metric_name == "failure_rate" for r in results)
