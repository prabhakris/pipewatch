"""Tests for pipewatch alert rules and evaluation logic."""

from datetime import datetime

import pytest

from pipewatch.metrics import PipelineMetric
from pipewatch.alerts import (
    Alert,
    AlertRule,
    HIGH_FAILURE_RATE_RULE,
    LOW_THROUGHPUT_RULE,
    DEFAULT_RULES,
    evaluate_rules,
)


def make_metric(
    pipeline_name="test_pipe",
    total_records=100,
    failed_records=0,
    duration_seconds=10.0,
) -> PipelineMetric:
    return PipelineMetric(
        pipeline_name=pipeline_name,
        total_records=total_records,
        failed_records=failed_records,
        duration_seconds=duration_seconds,
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
    )


class TestAlertRule:
    def test_rule_not_triggered(self):
        metric = make_metric(failed_records=5)  # 5% failure rate
        alert = HIGH_FAILURE_RATE_RULE.evaluate(metric)
        assert alert is None

    def test_rule_triggered_returns_alert(self):
        metric = make_metric(failed_records=20)  # 20% failure rate
        alert = HIGH_FAILURE_RATE_RULE.evaluate(metric)
        assert alert is not None
        assert alert.rule_name == "high_failure_rate"
        assert alert.severity == "critical"
        assert alert.pipeline == "test_pipe"

    def test_custom_rule(self):
        rule = AlertRule(
            name="no_records",
            description="Pipeline processed zero records",
            check=lambda m: m.total_records == 0,
            severity="info",
        )
        alert = rule.evaluate(make_metric(total_records=0))
        assert alert is not None
        assert alert.severity == "info"


class TestAlert:
    def test_to_dict(self):
        alert = Alert(
            rule_name="high_failure_rate",
            severity="critical",
            pipeline="etl_pipe",
            message="Failure rate exceeded 10%",
            triggered_at=datetime(2024, 1, 1, 12, 0, 0),
        )
        d = alert.to_dict()
        assert d["rule"] == "high_failure_rate"
        assert d["severity"] == "critical"
        assert d["pipeline"] == "etl_pipe"
        assert "triggered_at" in d


class TestEvaluateRules:
    def test_no_alerts_healthy_metric(self):
        metric = make_metric(total_records=200, failed_records=1, duration_seconds=10.0)
        alerts = evaluate_rules(metric)
        assert alerts == []

    def test_multiple_alerts_triggered(self):
        # High failure rate AND low throughput
        metric = make_metric(total_records=10, failed_records=5, duration_seconds=20.0)
        alerts = evaluate_rules(metric)
        rule_names = {a.rule_name for a in alerts}
        assert "high_failure_rate" in rule_names
        assert "low_throughput" in rule_names

    def test_custom_rules_override_defaults(self):
        rule = AlertRule(
            name="always_alert",
            description="Always fires",
            check=lambda m: True,
            severity="info",
        )
        alerts = evaluate_rules(make_metric(), rules=[rule])
        assert len(alerts) == 1
        assert alerts[0].rule_name == "always_alert"

    def test_zero_duration_skips_throughput_rule(self):
        metric = make_metric(total_records=100, failed_records=0, duration_seconds=0)
        alerts = evaluate_rules(metric, rules=[LOW_THROUGHPUT_RULE])
        assert alerts == []
