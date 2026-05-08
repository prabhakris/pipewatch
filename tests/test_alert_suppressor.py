"""Tests for pipewatch.alert_suppressor."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest

from pipewatch.alert_suppressor import AlertSuppressor, MuteRule
from pipewatch.alerts import Alert


def make_alert(pipeline_id: str = "pipe-1", rule_name: str = "high_failure") -> Alert:
    return Alert(
        pipeline_id=pipeline_id,
        rule_name=rule_name,
        message=f"{pipeline_id} triggered {rule_name}",
        severity="warning",
        triggered_at=datetime(2024, 1, 1, 12, 0, 0),
    )


# ---------------------------------------------------------------------------
# MuteRule
# ---------------------------------------------------------------------------

class TestMuteRule:
    def test_matches_same_pipeline_no_rule_name(self):
        rule = MuteRule(pipeline_id="pipe-1")
        assert rule.matches(make_alert("pipe-1", "anything")) is True

    def test_not_matches_different_pipeline(self):
        rule = MuteRule(pipeline_id="pipe-2")
        assert rule.matches(make_alert("pipe-1")) is False

    def test_matches_specific_rule_name(self):
        rule = MuteRule(pipeline_id="pipe-1", rule_name="high_failure")
        assert rule.matches(make_alert("pipe-1", "high_failure")) is True

    def test_not_matches_different_rule_name(self):
        rule = MuteRule(pipeline_id="pipe-1", rule_name="low_throughput")
        assert rule.matches(make_alert("pipe-1", "high_failure")) is False


# ---------------------------------------------------------------------------
# AlertSuppressor — mute rules
# ---------------------------------------------------------------------------

class TestAlertSuppressorMuteRules:
    def test_not_suppressed_by_default(self):
        s = AlertSuppressor()
        assert s.is_suppressed(make_alert()) is False

    def test_muted_pipeline_is_suppressed(self):
        s = AlertSuppressor()
        s.mute("pipe-1")
        assert s.is_suppressed(make_alert("pipe-1")) is True

    def test_muted_specific_rule_suppresses_only_that_rule(self):
        s = AlertSuppressor()
        s.mute("pipe-1", rule_name="high_failure")
        assert s.is_suppressed(make_alert("pipe-1", "high_failure")) is True
        assert s.is_suppressed(make_alert("pipe-1", "low_throughput")) is False

    def test_unmute_removes_suppression(self):
        s = AlertSuppressor()
        s.mute("pipe-1")
        s.unmute("pipe-1")
        assert s.is_suppressed(make_alert("pipe-1")) is False

    def test_unmute_nonexistent_is_noop(self):
        s = AlertSuppressor()
        s.unmute("pipe-99")  # should not raise


# ---------------------------------------------------------------------------
# AlertSuppressor — rate limiting
# ---------------------------------------------------------------------------

class TestAlertSuppressorRateLimiting:
    def test_suppressed_after_record(self):
        s = AlertSuppressor(cooldown_seconds=300)
        alert = make_alert()
        s.record(alert)
        assert s.is_suppressed(alert) is True

    def test_not_suppressed_after_cooldown(self):
        s = AlertSuppressor(cooldown_seconds=60)
        alert = make_alert()
        s.record(alert)
        # Advance time past cooldown
        with patch("pipewatch.rate_limiter.time.monotonic", return_value=9999.0):
            assert s.is_suppressed(alert) is False


# ---------------------------------------------------------------------------
# AlertSuppressor — filter_alerts
# ---------------------------------------------------------------------------

class TestFilterAlerts:
    def test_filter_returns_all_when_no_suppression(self):
        s = AlertSuppressor(cooldown_seconds=300)
        alerts = [make_alert("pipe-1"), make_alert("pipe-2")]
        result = s.filter_alerts(alerts)
        assert len(result) == 2

    def test_filter_removes_muted_alert(self):
        s = AlertSuppressor()
        s.mute("pipe-1")
        alerts = [make_alert("pipe-1"), make_alert("pipe-2")]
        result = s.filter_alerts(alerts)
        assert len(result) == 1
        assert result[0].pipeline_id == "pipe-2"

    def test_filter_records_forwarded_alerts(self):
        s = AlertSuppressor(cooldown_seconds=300)
        alert = make_alert("pipe-1")
        s.filter_alerts([alert])
        # Second call within cooldown should suppress
        result = s.filter_alerts([alert])
        assert result == []
