"""Tests for pipewatch.alert_correlator."""
from __future__ import annotations

import datetime

import pytest

from pipewatch.alerts import Alert
from pipewatch.alert_correlator import AlertCorrelator, CorrelationGroup


def _make_alert(
    pipeline_id: str = "pipe-1",
    rule_name: str = "high_failure",
    offset_seconds: int = 0,
) -> Alert:
    return Alert(
        pipeline_id=pipeline_id,
        rule_name=rule_name,
        message="triggered",
        severity="warning",
        triggered_at=datetime.datetime(2024, 6, 1, 10, 0, 0)
        + datetime.timedelta(seconds=offset_seconds),
    )


class TestCorrelationGroup:
    def test_count_empty(self):
        g = CorrelationGroup(pipeline_id="p", rule_name="r")
        assert g.count == 0

    def test_first_and_last_seen_none_when_empty(self):
        g = CorrelationGroup(pipeline_id="p", rule_name="r")
        assert g.first_seen is None
        assert g.last_seen is None

    def test_first_last_seen_single_alert(self):
        g = CorrelationGroup(pipeline_id="p", rule_name="r")
        a = _make_alert()
        g.add(a)
        assert g.first_seen == a.triggered_at
        assert g.last_seen == a.triggered_at

    def test_first_last_seen_multiple_alerts(self):
        g = CorrelationGroup(pipeline_id="p", rule_name="r")
        g.add(_make_alert(offset_seconds=0))
        g.add(_make_alert(offset_seconds=100))
        g.add(_make_alert(offset_seconds=50))
        assert g.first_seen < g.last_seen

    def test_to_dict_contains_keys(self):
        g = CorrelationGroup(pipeline_id="p", rule_name="r")
        d = g.to_dict()
        for key in ("pipeline_id", "rule_name", "count", "first_seen", "last_seen"):
            assert key in d


class TestAlertCorrelator:
    def test_add_creates_group(self):
        c = AlertCorrelator(window_seconds=300)
        c.add(_make_alert())
        assert len(c.groups()) == 1

    def test_same_key_merges_into_one_group(self):
        c = AlertCorrelator(window_seconds=300)
        c.add(_make_alert())
        c.add(_make_alert())
        assert len(c.groups()) == 1
        assert c.groups()[0].count == 2

    def test_different_rules_create_separate_groups(self):
        c = AlertCorrelator(window_seconds=300)
        c.add(_make_alert(rule_name="r1"))
        c.add(_make_alert(rule_name="r2"))
        assert len(c.groups()) == 2

    def test_different_pipelines_create_separate_groups(self):
        c = AlertCorrelator(window_seconds=300)
        c.add(_make_alert(pipeline_id="p1"))
        c.add(_make_alert(pipeline_id="p2"))
        assert len(c.groups()) == 2

    def test_evicts_stale_groups(self):
        c = AlertCorrelator(window_seconds=60)
        old_alert = _make_alert(offset_seconds=0)
        c.add(old_alert)
        assert len(c.groups()) == 1
        # New alert is 120s later — old group should be evicted
        new_alert = _make_alert(pipeline_id="pipe-2", offset_seconds=120)
        c.add(new_alert)
        assert len(c.groups()) == 1
        assert c.groups()[0].pipeline_id == "pipe-2"

    def test_reset_clears_all_groups(self):
        c = AlertCorrelator(window_seconds=300)
        c.add(_make_alert())
        c.reset()
        assert c.groups() == []

    def test_add_returns_group(self):
        c = AlertCorrelator(window_seconds=300)
        g = c.add(_make_alert())
        assert isinstance(g, CorrelationGroup)
        assert g.count == 1
