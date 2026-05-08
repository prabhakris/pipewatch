"""Tests for pipewatch.alert_correlator."""
from datetime import datetime, timedelta

import pytest

from pipewatch.alerts import Alert
from pipewatch.alert_correlator import AlertCorrelator, CorrelationGroup


def _make_alert(
    pipeline_id: str = "pipe_a",
    rule_name: str = "high_failure_rate",
    triggered_at: datetime | None = None,
) -> Alert:
    return Alert(
        pipeline_id=pipeline_id,
        rule_name=rule_name,
        message="test alert",
        triggered_at=triggered_at or datetime(2024, 1, 1, 12, 0, 0),
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
        t = datetime(2024, 6, 1, 10, 0, 0)
        g = CorrelationGroup(pipeline_id="p", rule_name="r", alerts=[_make_alert(triggered_at=t)])
        assert g.first_seen == t
        assert g.last_seen == t

    def test_to_dict_contains_keys(self):
        g = CorrelationGroup(pipeline_id="p", rule_name="r")
        d = g.to_dict()
        for key in ("pipeline_id", "rule_name", "count", "first_seen", "last_seen"):
            assert key in d


class TestAlertCorrelator:
    def test_add_creates_group(self):
        c = AlertCorrelator()
        alert = _make_alert()
        group = c.add(alert)
        assert group.count == 1
        assert group.pipeline_id == "pipe_a"

    def test_same_pipeline_rule_within_window_merged(self):
        c = AlertCorrelator(window_seconds=300)
        t = datetime(2024, 1, 1, 12, 0, 0)
        c.add(_make_alert(triggered_at=t))
        c.add(_make_alert(triggered_at=t + timedelta(seconds=60)))
        assert len(c.groups()) == 1
        assert c.groups()[0].count == 2

    def test_alerts_outside_window_create_new_group(self):
        c = AlertCorrelator(window_seconds=60)
        t = datetime(2024, 1, 1, 12, 0, 0)
        c.add(_make_alert(triggered_at=t))
        c.add(_make_alert(triggered_at=t + timedelta(seconds=120)))
        assert len(c.groups()) == 1  # key is same, group replaced
        assert c.groups()[0].count == 1  # new group has only second alert

    def test_different_pipelines_create_separate_groups(self):
        c = AlertCorrelator()
        t = datetime(2024, 1, 1, 12, 0, 0)
        c.add(_make_alert(pipeline_id="pipe_a", triggered_at=t))
        c.add(_make_alert(pipeline_id="pipe_b", triggered_at=t))
        assert len(c.groups()) == 2

    def test_different_rules_create_separate_groups(self):
        c = AlertCorrelator()
        t = datetime(2024, 1, 1, 12, 0, 0)
        c.add(_make_alert(rule_name="rule_x", triggered_at=t))
        c.add(_make_alert(rule_name="rule_y", triggered_at=t))
        assert len(c.groups()) == 2

    def test_reset_clears_groups(self):
        c = AlertCorrelator()
        c.add(_make_alert())
        c.reset()
        assert c.groups() == []

    def test_groups_returns_list(self):
        c = AlertCorrelator()
        assert isinstance(c.groups(), list)

    def test_first_seen_is_earliest(self):
        c = AlertCorrelator(window_seconds=600)
        t1 = datetime(2024, 1, 1, 12, 0, 0)
        t2 = t1 + timedelta(seconds=30)
        c.add(_make_alert(triggered_at=t2))
        c.add(_make_alert(triggered_at=t1))
        g = c.groups()[0]
        assert g.first_seen == t1
        assert g.last_seen == t2
