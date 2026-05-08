"""Alert suppression layer combining rate limiting with mute rules."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pipewatch.alerts import Alert
from pipewatch.rate_limiter import RateLimiter


@dataclass
class MuteRule:
    """Suppress alerts for a specific pipeline / rule combination."""

    pipeline_id: str
    rule_name: Optional[str] = None  # None means mute all rules for the pipeline

    def matches(self, alert: Alert) -> bool:
        if alert.pipeline_id != self.pipeline_id:
            return False
        if self.rule_name is None:
            return True
        return alert.rule_name == self.rule_name


@dataclass
class AlertSuppressor:
    """Decide whether an alert should be forwarded to notifiers.

    Suppression occurs when:
    - A matching ``MuteRule`` is active, OR
    - The alert's rate limiter reports the channel as suppressed.
    """

    cooldown_seconds: float = 300.0
    mute_rules: List[MuteRule] = field(default_factory=list)
    _rate_limiter: RateLimiter = field(init=False)

    def __post_init__(self) -> None:
        self._rate_limiter = RateLimiter(cooldown_seconds=self.cooldown_seconds)

    # ------------------------------------------------------------------
    # Mute rule management
    # ------------------------------------------------------------------

    def mute(self, pipeline_id: str, rule_name: Optional[str] = None) -> None:
        """Add a mute rule."""
        self.mute_rules.append(MuteRule(pipeline_id=pipeline_id, rule_name=rule_name))

    def unmute(self, pipeline_id: str, rule_name: Optional[str] = None) -> None:
        """Remove a matching mute rule (first match only)."""
        target = MuteRule(pipeline_id=pipeline_id, rule_name=rule_name)
        for i, rule in enumerate(self.mute_rules):
            if rule.pipeline_id == target.pipeline_id and rule.rule_name == target.rule_name:
                self.mute_rules.pop(i)
                return

    def _is_muted(self, alert: Alert) -> bool:
        return any(r.matches(alert) for r in self.mute_rules)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_suppressed(self, alert: Alert) -> bool:
        """Return True if *alert* should be suppressed (not forwarded)."""
        if self._is_muted(alert):
            return True
        key = f"{alert.pipeline_id}:{alert.rule_name}"
        return self._rate_limiter.is_suppressed(key)

    def record(self, alert: Alert) -> None:
        """Record that *alert* was forwarded; starts the cooldown window."""
        key = f"{alert.pipeline_id}:{alert.rule_name}"
        self._rate_limiter.record(key)

    def filter_alerts(self, alerts: List[Alert]) -> List[Alert]:
        """Return only the alerts that should be forwarded, recording them."""
        forwarded: List[Alert] = []
        for alert in alerts:
            if not self.is_suppressed(alert):
                self.record(alert)
                forwarded.append(alert)
        return forwarded
