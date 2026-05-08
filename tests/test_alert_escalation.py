"""Tests for pipewatch.alert_escalation."""
from datetime import datetime, timezone

import pytest

from pipewatch.alert_escalation import AlertEscalator, EscalationPolicy
from pipewatch.alerts import Alert


def _make_alert(pipeline_id="pipe-1", rule_name="high_failure", severity="warning", value=0.5):
    return Alert(
        pipeline_id=pipeline_id,
        rule_name=rule_name,
        message="failure rate too high",
        severity=severity,
        triggered_at=datetime.now(timezone.utc),
        value=value,
    )


class TestEscalationPolicy:
    def test_to_dict_contains_keys(self):
        p = EscalationPolicy(rule_name="r", threshold_count=2, escalated_severity="critical", window_seconds=60)
        d = p.to_dict()
        assert d["rule_name"] == "r"
        assert d["threshold_count"] == 2
        assert d["escalated_severity"] == "critical"
        assert d["window_seconds"] == 60


class TestAlertEscalator:
    def _escalator_with_policy(self, threshold=3, window=300):
        e = AlertEscalator()
        e.add_policy(EscalationPolicy(
            rule_name="high_failure",
            threshold_count=threshold,
            escalated_severity="critical",
            window_seconds=window,
        ))
        return e

    def test_no_policy_returns_alert_unchanged(self):
        e = AlertEscalator()
        alert = _make_alert()
        result = e.evaluate(alert)
        assert result.severity == "warning"
        assert "ESCALATED" not in result.message

    def test_below_threshold_not_escalated(self):
        e = self._escalator_with_policy(threshold=3)
        alert = _make_alert()
        result = e.evaluate(alert)
        assert "ESCALATED" not in result.message
        result = e.evaluate(alert)
        assert "ESCALATED" not in result.message

    def test_at_threshold_escalates(self):
        e = self._escalator_with_policy(threshold=3)
        alert = _make_alert()
        e.evaluate(alert)
        e.evaluate(alert)
        result = e.evaluate(alert)
        assert result.severity == "critical"
        assert result.message.startswith("[ESCALATED]")

    def test_escalation_persists_after_threshold(self):
        e = self._escalator_with_policy(threshold=2)
        alert = _make_alert()
        e.evaluate(alert)
        e.evaluate(alert)
        result = e.evaluate(alert)
        assert result.severity == "critical"

    def test_different_pipelines_are_independent(self):
        e = self._escalator_with_policy(threshold=2)
        a1 = _make_alert(pipeline_id="pipe-1")
        a2 = _make_alert(pipeline_id="pipe-2")
        e.evaluate(a1)
        e.evaluate(a1)  # pipe-1 escalated
        result2 = e.evaluate(a2)  # pipe-2 first fire
        assert "ESCALATED" not in result2.message

    def test_reset_all_clears_state(self):
        e = self._escalator_with_policy(threshold=2)
        alert = _make_alert()
        e.evaluate(alert)
        e.evaluate(alert)
        e.reset()
        result = e.evaluate(alert)  # first fire after reset
        assert "ESCALATED" not in result.message

    def test_reset_specific_pipeline(self):
        e = self._escalator_with_policy(threshold=2)
        a1 = _make_alert(pipeline_id="pipe-1")
        e.evaluate(a1)
        e.evaluate(a1)  # escalated
        e.reset(pipeline_id="pipe-1")
        result = e.evaluate(a1)
        assert "ESCALATED" not in result.message

    def test_original_alert_pipeline_id_preserved(self):
        e = self._escalator_with_policy(threshold=1)
        alert = _make_alert(pipeline_id="my-pipe")
        result = e.evaluate(alert)
        assert result.pipeline_id == "my-pipe"
