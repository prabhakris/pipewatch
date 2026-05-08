"""Produces human-readable summaries from correlation groups."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from pipewatch.alert_correlator import AlertCorrelator, CorrelationGroup
from pipewatch.alerts import Alert


@dataclass
class CorrelationReport:
    """Summary of correlated alert groups for a single evaluation pass."""

    groups: List[CorrelationGroup] = field(default_factory=list)

    @property
    def total_alerts(self) -> int:
        return sum(g.count for g in self.groups)

    @property
    def hot_pipelines(self) -> List[str]:
        """Pipeline IDs that appear in more than one group."""
        from collections import Counter
        counts = Counter(g.pipeline_id for g in self.groups)
        return [pid for pid, n in counts.items() if n > 1]

    def to_dict(self) -> dict:
        return {
            "total_alerts": self.total_alerts,
            "group_count": len(self.groups),
            "hot_pipelines": self.hot_pipelines,
            "groups": [g.to_dict() for g in self.groups],
        }

    def render_text(self) -> str:
        if not self.groups:
            return "No correlated alert groups."
        lines = [f"Correlation Report — {len(self.groups)} group(s), {self.total_alerts} alert(s)"]
        for g in self.groups:
            lines.append(
                f"  [{g.pipeline_id}] {g.rule_name}: {g.count} alert(s) "
                f"({g.first_seen} → {g.last_seen})"
            )
        if self.hot_pipelines:
            lines.append(f"  Hot pipelines: {', '.join(self.hot_pipelines)}")
        return "\n".join(lines)


def build_correlation_report(
    alerts: List[Alert],
    window_seconds: int = 300,
) -> CorrelationReport:
    """Correlate a list of alerts and return a CorrelationReport."""
    correlator = AlertCorrelator(window_seconds=window_seconds)
    for alert in alerts:
        correlator.add(alert)
    return CorrelationReport(groups=correlator.groups())
