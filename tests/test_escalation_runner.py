"""Tests for pipewatch.escalation_runner."""
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from pipewatch.alert_escalation import EscalationPolicy
from pipewatch.alert_router import AlertRouter
from pipewatch.alerts import Alert
from pipewatch.escalation_runner import EscalationRunner
from pipewatch.metrics import PipelineMetric
from pipewatch.pipeline_runner import RunReport


def _make_metric(pipeline_id="pipe-1"):
    return PipelineMetric(
        pipeline_id=pipeline_id,
        records_processed=100,
        records_failed=10,
        duration_seconds=5.0,
        timestamp=datetime.now(timezone.utc),
    )


def _make_alert(pipeline_id="pipe-1", rule_name="r", severity="warning"):
    return Alert(
        pipeline_id=pipeline_id,
        rule_name=rule_name,
        message="test alert",
        severity=severity,
        triggered_at=datetime.now(timezone.utc),
        value=0.5,
    )


def _make_report(alerts=None):
    metric = _make_metric()
    return RunReport(metric=metric, alerts=alerts or [], anomalies=[])


class TestEscalationRunner:
    def _make_runner(self, alerts=None):
        inner = MagicMock()
        inner.run.return_value = _make_report(alerts=alerts or [])
        return EscalationRunner(runner=inner)

    def test_run_returns_report(self):
        er = self._make_runner()
        report = er.run(_make_metric())
        assert isinstance(report, RunReport)

    def test_no_alerts_no_escalation(self):
        er = self._make_runner(alerts=[])
        report = er.run(_make_metric())
        assert report.alerts == []

    def test_alert_without_policy_unchanged(self):
        alert = _make_alert(severity="warning")
        er = self._make_runner(alerts=[alert])
        report = er.run(_make_metric())
        assert report.alerts[0].severity == "warning"
        assert "ESCALATED" not in report.alerts[0].message

    def test_alert_escalated_after_threshold(self):
        er = self._make_runner(alerts=[_make_alert(rule_name="r")])
        er.add_policy(EscalationPolicy(rule_name="r", threshold_count=2))
        metric = _make_metric()
        er.run(metric)          # fire 1
        report = er.run(metric)  # fire 2 → escalate
        assert report.alerts[0].severity == "critical"

    def test_router_receives_escalated_alert(self):
        received = []

        class _Rec:
            def send(self, alert):
                received.append(alert)
                return True

        er = self._make_runner(alerts=[_make_alert(rule_name="r")])
        er.add_policy(EscalationPolicy(rule_name="r", threshold_count=1))
        er.router.add_rule(lambda a: True, _Rec())
        er.run(_make_metric())
        assert len(received) == 1
        assert received[0].severity == "critical"

    def test_anomalies_passed_through(self):
        inner = MagicMock()
        from pipewatch.anomaly import AnomalyResult
        anomaly = AnomalyResult(pipeline_id="pipe-1", metric_name="failure_rate",
                                value=0.9, mean=0.1, std=0.05, z_score=16.0, is_anomaly=True)
        inner.run.return_value = RunReport(metric=_make_metric(), alerts=[], anomalies=[anomaly])
        er = EscalationRunner(runner=inner)
        report = er.run(_make_metric())
        assert len(report.anomalies) == 1
