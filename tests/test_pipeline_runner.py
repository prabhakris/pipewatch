"""Tests for PipelineRunner and RunReport."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from pipewatch.alerts import AlertRule
from pipewatch.metrics import PipelineMetric
from pipewatch.pipeline_runner import PipelineRunner, RunReport


def make_metric(
    pipeline_id: str = "etl_orders",
    total_records: int = 1000,
    failed_records: int = 0,
    duration_seconds: float = 60.0,
) -> PipelineMetric:
    return PipelineMetric(
        pipeline_id=pipeline_id,
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        total_records=total_records,
        failed_records=failed_records,
        duration_seconds=duration_seconds,
    )


class TestRunReport:
    def test_has_issues_false_when_empty(self):
        report = RunReport(metric=make_metric())
        assert report.has_issues() is False

    def test_has_issues_true_with_alerts(self):
        fake_alert = MagicMock()
        report = RunReport(metric=make_metric(), alerts=[fake_alert])
        assert report.has_issues() is True

    def test_to_dict_contains_keys(self):
        report = RunReport(metric=make_metric())
        d = report.to_dict()
        assert "metric" in d
        assert "alerts" in d
        assert "anomalies" in d
        assert d["has_issues"] is False


class TestPipelineRunner:
    def test_observe_returns_run_report(self):
        runner = PipelineRunner()
        report = runner.observe(make_metric())
        assert isinstance(report, RunReport)

    def test_no_alerts_when_no_rules(self):
        runner = PipelineRunner()
        report = runner.observe(make_metric(failed_records=500))
        assert report.alerts == []

    def test_alert_triggered_by_rule(self):
        rule = AlertRule(
            name="high_failure",
            metric_name="failure_rate",
            threshold=0.1,
            comparator="gt",
        )
        runner = PipelineRunner(rules=[rule])
        report = runner.observe(make_metric(total_records=100, failed_records=50))
        assert len(report.alerts) == 1

    def test_no_anomalies_below_min_samples(self):
        runner = PipelineRunner()
        report = runner.observe(make_metric())
        assert report.anomalies == []

    def test_notify_called_when_alert_present(self):
        rule = AlertRule(
            name="high_failure",
            metric_name="failure_rate",
            threshold=0.1,
            comparator="gt",
        )
        mock_channel = MagicMock()
        runner = PipelineRunner(rules=[rule], channels=[mock_channel])
        runner.observe(make_metric(total_records=100, failed_records=50))
        mock_channel.send.assert_called_once()

    def test_reset_clears_registry(self):
        runner = PipelineRunner()
        for i in range(5):
            runner.observe(make_metric(total_records=100 + i))
        runner.reset()
        # After reset, anomaly detection starts fresh (no samples)
        report = runner.observe(make_metric())
        assert report.anomalies == []
