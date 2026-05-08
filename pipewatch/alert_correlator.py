"""Alert correlation — groups related alerts by pipeline and rule proximity."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from pipewatch.alerts import Alert


@dataclass
class CorrelationGroup:
    """A cluster of temporally and logically related alerts."""

    pipeline_id: str
    rule_name: str
    alerts: List[Alert] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.alerts)

    @property
    def first_seen(self) -> Optional[datetime]:
        if not self.alerts:
            return None
        return min(a.triggered_at for a in self.alerts)

    @property
    def last_seen(self) -> Optional[datetime]:
        if not self.alerts:
            return None
        return max(a.triggered_at for a in self.alerts)

    def to_dict(self) -> dict:
        return {
            "pipeline_id": self.pipeline_id,
            "rule_name": self.rule_name,
            "count": self.count,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }


@dataclass
class AlertCorrelator:
    """Groups incoming alerts into correlation windows."""

    window_seconds: int = 300  # 5-minute default correlation window
    _groups: Dict[str, CorrelationGroup] = field(default_factory=dict, init=False)

    def _group_key(self, alert: Alert) -> str:
        return f"{alert.pipeline_id}::{alert.rule_name}"

    def _is_within_window(self, group: CorrelationGroup, alert: Alert) -> bool:
        if group.last_seen is None:
            return True
        delta = alert.triggered_at - group.last_seen
        return delta <= timedelta(seconds=self.window_seconds)

    def add(self, alert: Alert) -> CorrelationGroup:
        """Add an alert and return its correlation group."""
        key = self._group_key(alert)
        group = self._groups.get(key)
        if group is None or not self._is_within_window(group, alert):
            group = CorrelationGroup(
                pipeline_id=alert.pipeline_id,
                rule_name=alert.rule_name,
            )
            self._groups[key] = group
        group.alerts.append(alert)
        return group

    def groups(self) -> List[CorrelationGroup]:
        """Return all current correlation groups."""
        return list(self._groups.values())

    def reset(self) -> None:
        self._groups.clear()
