"""Tests for pipewatch.audit_middleware."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from pipewatch.alerts import Alert
from pipewatch.anomaly import AnomalyResult
from pipewatch.audit_log import AuditLog
from pipewatch.audit_middleware import AuditedRunner
from pipewatch.metrics import PipelineMetric
from pipewatch.pipeline_runner import RunReport


def make_metric(pipeline_id: str = "pipe-1") -> PipelineMetric:
    return PipelineMetric(
        pipeline_id=pipeline_id,
        total_records=200,
        failed_records=5,
        duration_seconds=10.0,
        timestamp=datetime(2024, 3, 1, tzinfo=timezone.utc),
    )


def _make_runner(alerts=None, anomalies=None) -> MagicMock:
    report = RunReport(
        metric=make_metric(),
        alerts=alerts or [],
        anomalies=anomalies or [],
    )
    runner = MagicMock()
    runner.run.return_value = report
    return runner


class TestAuditedRunner:
    def test_run_returns_report(self):
        runner = _make_runner()
        log = AuditLog()
        audited = AuditedRunner(runner=runner, audit_log=log)
        report = audited.run(make_metric())
        assert isinstance(report, RunReport)

    def test_emits_run_started_and_completed(self):
        runner = _make_runner()
        log = AuditLog()
        audited = AuditedRunner(runner=runner, audit_log=log)
        audited.run(make_metric())
        events = [e.event for e in log.entries()]
        assert "run_started" in events
        assert "run_completed" in events

    def test_run_count_increments(self):
        runner = _make_runner()
        log = AuditLog()
        audited = AuditedRunner(runner=runner, audit_log=log)
        audited.run(make_metric())
        audited.run(make_metric())
        assert audited._run_count == 2

    def test_alert_fired_event_emitted(self):
        alert = Alert(
            rule_name="high_failure_rate",
            message="Failure rate too high",
            severity="warning",
            pipeline_id="pipe-1",
        )
        runner = _make_runner(alerts=[alert])
        log = AuditLog()
        audited = AuditedRunner(runner=runner, audit_log=log)
        audited.run(make_metric())
        events = [e.event for e in log.entries()]
        assert "alert_fired" in events

    def test_anomaly_detected_event_emitted(self):
        anomaly = AnomalyResult(
            pipeline_id="pipe-1",
            metric_name="throughput",
            value=5.0,
            mean=50.0,
            std=2.0,
            z_score=22.5,
            is_anomaly=True,
        )
        runner = _make_runner(anomalies=[anomaly])
        log = AuditLog()
        audited = AuditedRunner(runner=runner, audit_log=log)
        audited.run(make_metric())
        events = [e.event for e in log.entries()]
        assert "anomaly_detected" in events

    def test_entries_scoped_to_pipeline(self):
        runner = _make_runner()
        log = AuditLog()
        audited = AuditedRunner(runner=runner, audit_log=log)
        audited.run(make_metric(pipeline_id="pipe-A"))
        audited.run(make_metric(pipeline_id="pipe-B"))
        assert len(log.entries(pipeline_id="pipe-A")) >= 2
        assert len(log.entries(pipeline_id="pipe-B")) >= 2
