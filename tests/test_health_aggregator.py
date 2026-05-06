"""Tests for pipewatch.health_aggregator."""

from __future__ import annotations

import pytest

from pipewatch.health import HealthReport
from pipewatch.health_aggregator import AggregatedHealth


def make_report(score: float) -> HealthReport:
    """Create a minimal HealthReport with the given score."""
    if score >= 0.8:
        status = "healthy"
    elif score >= 0.5:
        status = "degraded"
    else:
        status = "critical"
    return HealthReport(score=score, status=status, alerts=[], anomalies=[])


class TestAggregatedHealth:
    def test_empty_average_score_is_one(self):
        agg = AggregatedHealth()
        assert agg.average_score == 1.0

    def test_empty_overall_status_is_healthy(self):
        agg = AggregatedHealth()
        assert agg.overall_status == "healthy"

    def test_average_score_single_pipeline(self):
        agg = AggregatedHealth()
        agg.update("pipe_a", make_report(0.6))
        assert agg.average_score == pytest.approx(0.6)

    def test_average_score_multiple_pipelines(self):
        agg = AggregatedHealth()
        agg.update("pipe_a", make_report(0.8))
        agg.update("pipe_b", make_report(0.4))
        assert agg.average_score == pytest.approx(0.6)

    def test_overall_status_worst_wins(self):
        agg = AggregatedHealth()
        agg.update("pipe_a", make_report(0.9))  # healthy
        agg.update("pipe_b", make_report(0.3))  # critical
        assert agg.overall_status == "critical"

    def test_overall_status_degraded_beats_healthy(self):
        agg = AggregatedHealth()
        agg.update("pipe_a", make_report(0.9))  # healthy
        agg.update("pipe_b", make_report(0.6))  # degraded
        assert agg.overall_status == "degraded"

    def test_pipelines_by_status(self):
        agg = AggregatedHealth()
        agg.update("pipe_a", make_report(0.9))
        agg.update("pipe_b", make_report(0.3))
        agg.update("pipe_c", make_report(0.85))
        healthy = agg.pipelines_by_status("healthy")
        assert set(healthy) == {"pipe_a", "pipe_c"}

    def test_get_returns_report(self):
        agg = AggregatedHealth()
        report = make_report(0.7)
        agg.update("pipe_a", report)
        assert agg.get("pipe_a") is report

    def test_get_returns_none_for_missing(self):
        agg = AggregatedHealth()
        assert agg.get("nonexistent") is None

    def test_remove_pipeline(self):
        agg = AggregatedHealth()
        agg.update("pipe_a", make_report(0.5))
        agg.remove("pipe_a")
        assert agg.get("pipe_a") is None
        assert len(agg.reports) == 0

    def test_remove_nonexistent_does_not_raise(self):
        agg = AggregatedHealth()
        agg.remove("ghost")  # should not raise

    def test_to_dict_keys(self):
        agg = AggregatedHealth()
        agg.update("pipe_a", make_report(0.9))
        result = agg.to_dict()
        assert set(result.keys()) == {
            "average_score",
            "overall_status",
            "pipeline_count",
            "pipelines",
        }

    def test_to_dict_pipeline_count(self):
        agg = AggregatedHealth()
        agg.update("pipe_a", make_report(0.9))
        agg.update("pipe_b", make_report(0.4))
        assert agg.to_dict()["pipeline_count"] == 2
