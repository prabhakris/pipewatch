"""Unit tests for pipewatch.metrics module."""

import pytest
from pipewatch.metrics import MetricsCollector, PipelineMetric


def make_metric(
    pipeline_name="etl_orders",
    stage="transform",
    records_processed=100,
    records_failed=5,
    duration_seconds=10.0,
) -> PipelineMetric:
    return PipelineMetric(
        pipeline_name=pipeline_name,
        stage=stage,
        records_processed=records_processed,
        records_failed=records_failed,
        duration_seconds=duration_seconds,
    )


class TestPipelineMetric:
    def test_failure_rate_normal(self):
        m = make_metric(records_processed=95, records_failed=5)
        assert m.failure_rate == pytest.approx(5 / 100)

    def test_failure_rate_zero_records(self):
        m = make_metric(records_processed=0, records_failed=0)
        assert m.failure_rate == 0.0

    def test_throughput_normal(self):
        m = make_metric(records_processed=200, duration_seconds=4.0)
        assert m.throughput == pytest.approx(50.0)

    def test_throughput_zero_duration(self):
        m = make_metric(records_processed=100, duration_seconds=0.0)
        assert m.throughput == 0.0

    def test_to_dict_keys(self):
        m = make_metric()
        d = m.to_dict()
        expected_keys = {
            "pipeline_name", "stage", "records_processed",
            "records_failed", "duration_seconds", "failure_rate",
            "throughput", "timestamp",
        }
        assert set(d.keys()) == expected_keys


class TestMetricsCollector:
    def test_record_and_latest(self):
        collector = MetricsCollector()
        m = make_metric()
        collector.record(m)
        assert collector.latest("etl_orders") is m

    def test_latest_returns_most_recent(self):
        collector = MetricsCollector()
        m1 = make_metric(records_processed=10)
        m2 = make_metric(records_processed=20)
        collector.record(m1)
        collector.record(m2)
        assert collector.latest("etl_orders").records_processed == 20

    def test_latest_unknown_pipeline_returns_none(self):
        collector = MetricsCollector()
        assert collector.latest("nonexistent") is None

    def test_latest_filters_by_stage(self):
        collector = MetricsCollector()
        collector.record(make_metric(stage="extract", records_processed=1))
        collector.record(make_metric(stage="load", records_processed=2))
        result = collector.latest("etl_orders", stage="extract")
        assert result.records_processed == 1

    def test_max_history_eviction(self):
        collector = MetricsCollector(max_history=3)
        for i in range(5):
            collector.record(make_metric(records_processed=i))
        assert len(collector.all_metrics()) == 3

    def test_clear(self):
        collector = MetricsCollector()
        collector.record(make_metric())
        collector.clear()
        assert collector.all_metrics() == []
