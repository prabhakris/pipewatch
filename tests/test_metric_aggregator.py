"""Tests for pipewatch.metric_aggregator."""
from __future__ import annotations

import datetime
from typing import Optional

import pytest

from pipewatch.metric_aggregator import MetricAggregator, MetricSummary
from pipewatch.metrics import PipelineMetric


def make_metric(
    pipeline_id: str = "pipe-1",
    records_processed: int = 100,
    records_failed: int = 0,
    duration_seconds: float = 10.0,
) -> PipelineMetric:
    return PipelineMetric(
        pipeline_id=pipeline_id,
        timestamp=datetime.datetime.utcnow(),
        records_processed=records_processed,
        records_failed=records_failed,
        duration_seconds=duration_seconds,
    )


class TestMetricAggregator:
    def test_summarize_returns_none_when_empty(self):
        agg = MetricAggregator()
        assert agg.summarize("pipe-1") is None

    def test_summarize_single_sample(self):
        agg = MetricAggregator()
        agg.ingest(make_metric(records_processed=100, records_failed=5, duration_seconds=10.0))
        summary = agg.summarize("pipe-1")
        assert summary is not None
        assert summary.samples == 1
        assert summary.mean_failure_rate == pytest.approx(0.05)
        assert summary.stddev_failure_rate == 0.0
        assert summary.mean_throughput == pytest.approx(10.0)
        assert summary.min_throughput == pytest.approx(10.0)
        assert summary.max_throughput == pytest.approx(10.0)

    def test_summarize_multiple_samples_failure_rate(self):
        agg = MetricAggregator()
        agg.ingest(make_metric(records_processed=100, records_failed=0))
        agg.ingest(make_metric(records_processed=100, records_failed=10))
        agg.ingest(make_metric(records_processed=100, records_failed=20))
        summary = agg.summarize("pipe-1")
        assert summary.samples == 3
        assert summary.mean_failure_rate == pytest.approx(0.10)
        assert summary.median_failure_rate == pytest.approx(0.10)
        assert summary.stddev_failure_rate > 0.0

    def test_summarize_throughput_min_max(self):
        agg = MetricAggregator()
        agg.ingest(make_metric(records_processed=100, duration_seconds=5.0))   # 20/s
        agg.ingest(make_metric(records_processed=100, duration_seconds=10.0))  # 10/s
        agg.ingest(make_metric(records_processed=100, duration_seconds=20.0))  # 5/s
        summary = agg.summarize("pipe-1")
        assert summary.min_throughput == pytest.approx(5.0)
        assert summary.max_throughput == pytest.approx(20.0)

    def test_separate_buckets_per_pipeline(self):
        agg = MetricAggregator()
        agg.ingest(make_metric(pipeline_id="pipe-a", records_processed=200))
        agg.ingest(make_metric(pipeline_id="pipe-b", records_processed=50))
        assert agg.summarize("pipe-a").samples == 1
        assert agg.summarize("pipe-b").samples == 1
        assert agg.summarize("pipe-c") is None

    def test_all_summaries_sorted(self):
        agg = MetricAggregator()
        agg.ingest(make_metric(pipeline_id="zzz"))
        agg.ingest(make_metric(pipeline_id="aaa"))
        agg.ingest(make_metric(pipeline_id="mmm"))
        ids = [s.pipeline_id for s in agg.all_summaries()]
        assert ids == ["aaa", "mmm", "zzz"]

    def test_all_summaries_empty(self):
        assert MetricAggregator().all_summaries() == []

    def test_reset_single_pipeline(self):
        agg = MetricAggregator()
        agg.ingest(make_metric(pipeline_id="pipe-1"))
        agg.ingest(make_metric(pipeline_id="pipe-2"))
        agg.reset("pipe-1")
        assert agg.summarize("pipe-1") is None
        assert agg.summarize("pipe-2") is not None

    def test_reset_all(self):
        agg = MetricAggregator()
        agg.ingest(make_metric(pipeline_id="pipe-1"))
        agg.ingest(make_metric(pipeline_id="pipe-2"))
        agg.reset()
        assert agg.all_summaries() == []

    def test_tracked_pipelines(self):
        agg = MetricAggregator()
        agg.ingest(make_metric(pipeline_id="b"))
        agg.ingest(make_metric(pipeline_id="a"))
        assert agg.tracked_pipelines == ["a", "b"]

    def test_to_dict_contains_required_keys(self):
        agg = MetricAggregator()
        agg.ingest(make_metric())
        d = agg.summarize("pipe-1").to_dict()
        required = {
            "pipeline_id", "samples", "mean_failure_rate",
            "median_failure_rate", "stddev_failure_rate",
            "mean_throughput", "min_throughput", "max_throughput",
        }
        assert required.issubset(d.keys())
