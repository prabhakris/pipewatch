"""Integration tests for alert_correlator + correlation_reporter together."""
from __future__ import annotations

import datetime

from pipewatch.alerts import Alert
from pipewatch.alert_correlator import AlertCorrelator
from pipewatch.correlation_reporter import build_report


def _alert(pipeline_id: str, rule_name: str, offset: int = 0) -> Alert:
    return Alert(
        pipeline_id=pipeline_id,
        rule_name=rule_name,
        message="triggered",
        severity="critical",
        triggered_at=datetime.datetime(2024, 6, 1, 9, 0, 0)
        + datetime.timedelta(seconds=offset),
    )


def test_report_reflects_correlator_state():
    c = AlertCorrelator(window_seconds=300)
    for _ in range(3):
        c.add(_alert("etl-main", "high_failure"))
    c.add(_alert("etl-secondary", "low_throughput"))

    report = build_report(c)
    assert report.total_alerts == 4
    assert len(report.groups) == 2


def test_hot_pipelines_integration():
    c = AlertCorrelator(window_seconds=300)
    c.add(_alert("pipe-x", "rule-a"))
    c.add(_alert("pipe-x", "rule-a"))  # same group, count=2
    c.add(_alert("pipe-x", "rule-b"))  # different group, same pipeline

    report = build_report(c)
    assert "pipe-x" in report.hot_pipelines


def test_render_text_integration():
    c = AlertCorrelator(window_seconds=300)
    c.add(_alert("pipe-render", "latency_spike"))
    report = build_report(c)
    text = report.render_text()
    assert "pipe-render" in text
    assert "latency_spike" in text
    assert "Correlation Report" in text


def test_to_dict_integration():
    c = AlertCorrelator(window_seconds=300)
    c.add(_alert("pipe-1", "r1"))
    d = build_report(c).to_dict()
    assert d["total_alerts"] == 1
    assert len(d["groups"]) == 1
    assert d["groups"][0]["pipeline_id"] == "pipe-1"
