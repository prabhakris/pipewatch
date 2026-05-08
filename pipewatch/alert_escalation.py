"""Alert escalation policy: promote alerts to higher severity after repeated firing."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional

from pipewatch.alerts import Alert


@dataclass
class EscalationPolicy:
    """Defines when and how an alert should be escalated."""
    rule_name: str
    threshold_count: int = 3          # fires before escalation
    escalated_severity: str = "critical"
    window_seconds: float = 300.0     # rolling window to count fires

    def to_dict(self) -> dict:
        return {
            "rule_name": self.rule_name,
            "threshold_count": self.threshold_count,
            "escalated_severity": self.escalated_severity,
            "window_seconds": self.window_seconds,
        }


@dataclass
class EscalationState:
    """Tracks firing history for a single (pipeline, rule) pair."""
    fire_times: list = field(default_factory=list)
    escalated: bool = False


class AlertEscalator:
    """Applies escalation policies to alerts."""

    def __init__(self) -> None:
        self._policies: Dict[str, EscalationPolicy] = {}
        self._states: Dict[str, EscalationState] = {}

    def add_policy(self, policy: EscalationPolicy) -> None:
        self._policies[policy.rule_name] = policy

    def evaluate(self, alert: Alert) -> Alert:
        """Return the alert, possibly with escalated severity."""
        policy = self._policies.get(alert.rule_name)
        if policy is None:
            return alert

        key = f"{alert.pipeline_id}::{alert.rule_name}"
        state = self._states.setdefault(key, EscalationState())

        now = datetime.now(timezone.utc).timestamp()
        cutoff = now - policy.window_seconds
        state.fire_times = [t for t in state.fire_times if t >= cutoff]
        state.fire_times.append(now)

        if len(state.fire_times) >= policy.threshold_count:
            state.escalated = True

        if state.escalated:
            return Alert(
                pipeline_id=alert.pipeline_id,
                rule_name=alert.rule_name,
                message=f"[ESCALATED] {alert.message}",
                severity=policy.escalated_severity,
                triggered_at=alert.triggered_at,
                value=alert.value,
            )
        return alert

    def reset(self, pipeline_id: Optional[str] = None) -> None:
        if pipeline_id is None:
            self._states.clear()
        else:
            self._states = {k: v for k, v in self._states.items()
                            if not k.startswith(f"{pipeline_id}::")}
