"""Routes alerts to appropriate notification channels based on severity and pipeline."""
from dataclasses import dataclass, field
from typing import List, Optional

from pipewatch.alerts import Alert
from pipewatch.notifier import NotificationChannel


@dataclass
class RoutingRule:
    """Maps a condition to one or more notification channels."""
    channels: List[NotificationChannel]
    pipeline_id: Optional[str] = None  # None means match all pipelines
    severity: Optional[str] = None     # None means match all severities

    def matches(self, alert: Alert) -> bool:
        """Return True if this rule applies to the given alert."""
        if self.pipeline_id is not None and alert.pipeline_id != self.pipeline_id:
            return False
        if self.severity is not None and alert.severity != self.severity:
            return False
        return True


@dataclass
class AlertRouter:
    """Dispatches alerts to channels according to registered routing rules."""
    rules: List[RoutingRule] = field(default_factory=list)
    fallback_channels: List[NotificationChannel] = field(default_factory=list)

    def add_rule(self, rule: RoutingRule) -> None:
        """Register a routing rule."""
        self.rules.append(rule)

    def route(self, alert: Alert) -> List[bool]:
        """Send *alert* to every channel matched by at least one rule.

        Falls back to *fallback_channels* when no rule matches.
        Returns a list of send-result booleans (one per channel call).
        """
        matched_channels: List[NotificationChannel] = []
        for rule in self.rules:
            if rule.matches(alert):
                matched_channels.extend(rule.channels)

        channels_to_use = matched_channels if matched_channels else self.fallback_channels

        results: List[bool] = []
        for channel in channels_to_use:
            results.append(channel.send(alert))
        return results

    def route_many(self, alerts: List[Alert]) -> dict:
        """Route a list of alerts, returning a mapping of alert rule_name -> results."""
        return {alert.rule_name: self.route(alert) for alert in alerts}
