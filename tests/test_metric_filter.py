"""Tests for pipewatch.metric_filter."""
from __future__ import annotations

import pytest

from pipewatch.metrics import PipelineMetric
from pipewatch.metric_filter import MetricFilter


def make_metric(
    pipeline_id: str = "pipe-1",
    total_records: int = 100,
    failed_records: int = 0,
    duration_seconds: float = 10.0,
) -> PipelineMetric:
    return PipelineMetric(
        pipeline_id=pipeline_id,
        total_records=total_records,
        failed_records=failed_records,
        duration_seconds=duration_seconds,
    )


class TestMetricFilterMatches:
    def test_empty_filter_matches_everything(self):
        f = MetricFilter()
        assert f.matches(make_metric()) is True

    def test_pipeline_id_whitelist_passes(self):
        f = MetricFilter(pipeline_ids=["pipe-1", "pipe-2"])
        assert f.matches(make_metric(pipeline_id="pipe-1")) is True

    def test_pipeline_id_whitelist_blocks(self):
        f = MetricFilter(pipeline_ids=["pipe-2"])
        assert f.matches(make_metric(pipeline_id="pipe-1")) is False

    def test_min_records_passes(self):
        f = MetricFilter(min_records=50)
        assert f.matches(make_metric(total_records=100)) is True

    def test_min_records_blocks(self):
        f = MetricFilter(min_records=200)
        assert f.matches(make_metric(total_records=100)) is False

    def test_max_failure_rate_passes(self):
        # 5 / 100 = 0.05
        f = MetricFilter(max_failure_rate=0.10)
        assert f.matches(make_metric(total_records=100, failed_records=5)) is True

    def test_max_failure_rate_blocks(self):
        # 20 / 100 = 0.20
        f = MetricFilter(max_failure_rate=0.10)
        assert f.matches(make_metric(total_records=100, failed_records=20)) is False

    def test_min_throughput_passes(self):
        # 100 records / 10 s = 10 rec/s
        f = MetricFilter(min_throughput=5.0)
        assert f.matches(make_metric(total_records=100, duration_seconds=10.0)) is True

    def test_min_throughput_blocks(self):
        f = MetricFilter(min_throughput=20.0)
        assert f.matches(make_metric(total_records=100, duration_seconds=10.0)) is False

    def test_custom_predicate_passes(self):
        f = MetricFilter(custom=[lambda m: m.pipeline_id.startswith("pipe")])
        assert f.matches(make_metric(pipeline_id="pipe-99")) is True

    def test_custom_predicate_blocks(self):
        f = MetricFilter(custom=[lambda m: m.pipeline_id.startswith("etl")])
        assert f.matches(make_metric(pipeline_id="pipe-99")) is False

    def test_multiple_predicates_all_must_pass(self):
        f = MetricFilter(
            pipeline_ids=["pipe-1"],
            min_records=50,
            max_failure_rate=0.10,
        )
        # passes all
        assert f.matches(make_metric(pipeline_id="pipe-1", total_records=100, failed_records=5)) is True
        # fails pipeline_id check
        assert f.matches(make_metric(pipeline_id="pipe-2", total_records=100, failed_records=5)) is False


class TestMetricFilterApply:
    def test_apply_empty_list(self):
        f = MetricFilter(pipeline_ids=["pipe-1"])
        assert f.apply([]) == []

    def test_apply_filters_correctly(self):
        metrics = [
            make_metric(pipeline_id="pipe-1", total_records=100),
            make_metric(pipeline_id="pipe-2", total_records=200),
            make_metric(pipeline_id="pipe-1", total_records=50),
        ]
        f = MetricFilter(pipeline_ids=["pipe-1"])
        result = f.apply(metrics)
        assert len(result) == 2
        assert all(m.pipeline_id == "pipe-1" for m in result)

    def test_apply_returns_new_list(self):
        metrics = [make_metric()]
        f = MetricFilter()
        result = f.apply(metrics)
        assert result is not metrics
