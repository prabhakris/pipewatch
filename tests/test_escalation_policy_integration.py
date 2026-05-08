"""Integration-style tests: EscalationPolicy + AlertEscalator end-to-end."""
from datetime import datetime, timezone

from pipewatch.alert_escalation import AlertEscalator, EscalationPolicy
from pipewatch.alerts import Alert


def _alert(rule_name="latency_spike", pipeline_id="etl-main"):
    return Alert(
        pipeline_id=pipeline_id,
        rule_name=rule_name,
        message="latency too high",
        severity="warning",
        triggered_at=datetime.now(timezone.utc),
        value=1.2,
    )


def test_full_escalation_cycle():
    """Three consecutive fires within window should escalate on the third."""
    e = AlertEscalator()
    e.add_policy(EscalationPolicy(
        rule_name="latency_spike",
        threshold_count=3,
        escalated_severity="critical",
        window_seconds=60,
    ))
    a = _alert()
    r1 = e.evaluate(a)
    r2 = e.evaluate(a)
    r3 = e.evaluate(a)
    assert r1.severity == "warning"
    assert r2.severity == "warning"
    assert r3.severity == "critical"
    assert r3.message.startswith("[ESCALATED]")


def test_multiple_rules_independent():
    e = AlertEscalator()
    e.add_policy(EscalationPolicy(rule_name="rule_a", threshold_count=2))
    e.add_policy(EscalationPolicy(rule_name="rule_b", threshold_count=2))

    a = _alert(rule_name="rule_a")
    b = _alert(rule_name="rule_b")

    e.evaluate(a)
    r_a = e.evaluate(a)  # escalated
    r_b = e.evaluate(b)  # rule_b first fire — not escalated

    assert r_a.severity == "critical"
    assert "ESCALATED" not in r_b.message


def test_reset_allows_re_escalation():
    e = AlertEscalator()
    e.add_policy(EscalationPolicy(rule_name="r", threshold_count=2))
    a = _alert(rule_name="r")
    e.evaluate(a)
    e.evaluate(a)  # escalated
    e.reset()
    # After reset, need threshold fires again
    r1 = e.evaluate(a)
    assert "ESCALATED" not in r1.message
    r2 = e.evaluate(a)
    assert r2.severity == "critical"
