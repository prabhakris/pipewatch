"""Generates human-readable reports from correlated alert groups."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from pipewatch.alert_correlator import AlertCorrelator, CorrelationGroup


@dataclass
class CorrelationReport:
    groups: List[CorrelationGroup] = field(default_factory=list)

    @property
    def total_alerts(self) -> int:
        return sum(g.count for g in self.groups)

    @property
    def hot_pipelines(self) -> List[str]:
        """Return pipeline IDs that appear in more than one group."""
        seen: dict[str, int] = {}
        for g in self.groups:
            seen[g.pipeline_id] = seen.get(g.pipeline_id, 0) + g.count
        return [pid for pid, cnt in seen.items() if cnt > 1]

    def to_dict(self) -> dict:
        return {
            "total_alerts": self.total_alerts,
            "hot_pipelines": self.hot_pipelines,
            "groups": [g.to_dict() for g in self.groups],
        }

    def render_text(self) -> str:
        lines = [
            f"Correlation Report — {len(self.groups)} group(s), {self.total_alerts} alert(s) total",
            "-" * 60,
        ]
        for g in self.groups:
            first = g.first_seen.isoformat() if g.first_seen else "n/a"
            last = g.last_seen.isoformat() if g.last_seen else "n/a"
            lines.append(
                f"[{g.pipeline_id}] rule={g.rule_name}  count={g.count}  "
                f"first={first}  last={last}"
            )
        if self.hot_pipelines:
            lines.append("-" * 60)
            lines.append("Hot pipelines: " + ", ".join(self.hot_pipelines))
        return "\n".join(lines)


def build_report(correlator: AlertCorrelator) -> CorrelationReport:
    """Snapshot the current state of a correlator into a CorrelationReport."""
    groups = list(correlator._groups.values())
    return CorrelationReport(groups=groups)
