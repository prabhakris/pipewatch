"""Tests for pipewatch.correlation_reporter."""
from __future__ import annotations

import datetime
from unittest.mock import MagicMock

import pytest

from pipewatch.alerts import Alert
from pipewatch.alert_correlator import AlertCorrelator
from pipewatch.correlation_reporter import CorrelationReport, CorrelationGroup, build_report


def _make_alert(pipeline_id: str = "pipe-1", rule_name: str = "high_failure") -> Alert:
    return Alert(
        pipeline_id=pipeline_id,
        rule_name=rule_name,
        message=f"{rule_name} triggered",
        severity="warning",
        triggered_at=datetime.datetime(2024, 1, 1, 12, 0, 0),
    )


class TestCorrelationReport:
    def _report(self, *groups):
        return CorrelationReport(groups=list(groups))

    def _group(self, pipeline_id="pipe-1", rule_name="r", alerts=None):
        g = CorrelationGroup(pipeline_id=pipeline_id, rule_name=rule_name)
        for a in (alerts or []):
            g.add(a)
        return g

    def test_total_alerts_empty(self):
        assert self._report().total_alerts == 0

    def test_total_alerts_sums_groups(self):
        g1 = self._group(alerts=[_make_alert()])
        g2 = self._group(pipeline_id="pipe-2", alerts=[_make_alert(), _make_alert()])
        assert self._report(g1, g2).total_alerts == 3

    def test_hot_pipelines_empty_when_no_repeats(self):
        g1 = self._group("pipe-1", "r1", [_make_alert()])
        g2 = self._group("pipe-2", "r2", [_make_alert()])
        assert self._report(g1, g2).hot_pipelines == []

    def test_hot_pipelines_detected(self):
        g1 = self._group("pipe-1", "r1", [_make_alert(), _make_alert()])
        g2 = self._group("pipe-1", "r2", [_make_alert()])
        report = self._report(g1, g2)
        assert "pipe-1" in report.hot_pipelines

    def test_to_dict_contains_keys(self):
        report = self._report()
        d = report.to_dict()
        assert "total_alerts" in d
        assert "hot_pipelines" in d
        assert "groups" in d

    def test_render_text_contains_header(self):
        report = self._report()
        text = report.render_text()
        assert "Correlation Report" in text

    def test_render_text_contains_pipeline_id(self):
        g = self._group("pipe-42", "slow_throughput", [_make_alert()])
        text = self._report(g).render_text()
        assert "pipe-42" in text
        assert "slow_throughput" in text

    def test_render_text_shows_hot_pipelines(self):
        g1 = self._group("pipe-1", "r1", [_make_alert(), _make_alert()])
        g2 = self._group("pipe-1", "r2", [_make_alert()])
        text = self._report(g1, g2).render_text()
        assert "Hot pipelines" in text
        assert "pipe-1" in text


def test_build_report_from_correlator():
    correlator = AlertCorrelator(window_seconds=60)
    a1 = _make_alert("pipe-1", "high_failure")
    a2 = _make_alert("pipe-2", "low_throughput")
    correlator.add(a1)
    correlator.add(a2)
    report = build_report(correlator)
    assert report.total_alerts == 2
    assert len(report.groups) == 2


def test_build_report_empty_correlator():
    correlator = AlertCorrelator(window_seconds=60)
    report = build_report(correlator)
    assert report.total_alerts == 0
    assert report.groups == []
