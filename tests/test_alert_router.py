"""Tests for pipewatch.alert_router."""
import datetime
import pytest

from pipewatch.alerts import Alert
from pipewatch.alert_router import AlertRouter, RoutingRule
from pipewatch.notifier import NotificationChannel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _RecordingChannel(NotificationChannel):
    """Stub channel that records every alert it receives."""

    def __init__(self):
        self.received: list = []

    def send(self, alert: Alert) -> bool:  # type: ignore[override]
        self.received.append(alert)
        return True


def _make_alert(pipeline_id: str = "pipe-1", severity: str = "warning", rule_name: str = "high_failure") -> Alert:
    return Alert(
        pipeline_id=pipeline_id,
        rule_name=rule_name,
        message="test alert",
        severity=severity,
        triggered_at=datetime.datetime(2024, 1, 1, 12, 0, 0),
    )


# ---------------------------------------------------------------------------
# RoutingRule.matches
# ---------------------------------------------------------------------------

class TestRoutingRuleMatches:
    def test_wildcard_matches_any_alert(self):
        rule = RoutingRule(channels=[])
        assert rule.matches(_make_alert()) is True

    def test_pipeline_filter_matches_correct_pipeline(self):
        rule = RoutingRule(channels=[], pipeline_id="pipe-1")
        assert rule.matches(_make_alert(pipeline_id="pipe-1")) is True

    def test_pipeline_filter_rejects_other_pipeline(self):
        rule = RoutingRule(channels=[], pipeline_id="pipe-2")
        assert rule.matches(_make_alert(pipeline_id="pipe-1")) is False

    def test_severity_filter_matches_correct_severity(self):
        rule = RoutingRule(channels=[], severity="critical")
        assert rule.matches(_make_alert(severity="critical")) is True

    def test_severity_filter_rejects_other_severity(self):
        rule = RoutingRule(channels=[], severity="critical")
        assert rule.matches(_make_alert(severity="warning")) is False

    def test_combined_filter_requires_both_to_match(self):
        rule = RoutingRule(channels=[], pipeline_id="pipe-1", severity="critical")
        assert rule.matches(_make_alert(pipeline_id="pipe-1", severity="warning")) is False
        assert rule.matches(_make_alert(pipeline_id="pipe-1", severity="critical")) is True


# ---------------------------------------------------------------------------
# AlertRouter.route
# ---------------------------------------------------------------------------

class TestAlertRouter:
    def test_route_sends_to_matched_channel(self):
        ch = _RecordingChannel()
        router = AlertRouter(rules=[RoutingRule(channels=[ch], severity="warning")])
        alert = _make_alert(severity="warning")
        results = router.route(alert)
        assert results == [True]
        assert alert in ch.received

    def test_route_uses_fallback_when_no_rule_matches(self):
        ch = _RecordingChannel()
        router = AlertRouter(fallback_channels=[ch])
        alert = _make_alert(severity="critical")
        results = router.route(alert)
        assert results == [True]
        assert alert in ch.received

    def test_route_returns_empty_when_no_channels(self):
        router = AlertRouter()
        assert router.route(_make_alert()) == []

    def test_route_many_returns_dict_keyed_by_rule_name(self):
        ch = _RecordingChannel()
        router = AlertRouter(rules=[RoutingRule(channels=[ch])])
        alerts = [_make_alert(rule_name="r1"), _make_alert(rule_name="r2")]
        result = router.route_many(alerts)
        assert set(result.keys()) == {"r1", "r2"}

    def test_multiple_matching_rules_send_to_all_channels(self):
        ch1, ch2 = _RecordingChannel(), _RecordingChannel()
        router = AlertRouter(rules=[
            RoutingRule(channels=[ch1]),
            RoutingRule(channels=[ch2]),
        ])
        alert = _make_alert()
        router.route(alert)
        assert alert in ch1.received
        assert alert in ch2.received
