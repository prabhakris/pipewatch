"""Groups related alerts into correlation windows."""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pipewatch.alerts import Alert


@dataclass
class CorrelationGroup:
    pipeline_id: str
    rule_name: str
    _alerts: List[Alert] = field(default_factory=list, repr=False)

    def add(self, alert: Alert) -> None:
        self._alerts.append(alert)

    @property
    def count(self) -> int:
        return len(self._alerts)

    @property
    def first_seen(self) -> Optional[datetime.datetime]:
        if not self._alerts:
            return None
        return min(a.triggered_at for a in self._alerts)

    @property
    def last_seen(self) -> Optional[datetime.datetime]:
        if not self._alerts:
            return None
        return max(a.triggered_at for a in self._alerts)

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
    """Correlates alerts by (pipeline_id, rule_name) within a rolling time window."""

    window_seconds: int = 300
    _groups: Dict[tuple, CorrelationGroup] = field(default_factory=dict, repr=False)

    def add(self, alert: Alert) -> CorrelationGroup:
        self._evict(alert.triggered_at)
        key = (alert.pipeline_id, alert.rule_name)
        if key not in self._groups:
            self._groups[key] = CorrelationGroup(
                pipeline_id=alert.pipeline_id,
                rule_name=alert.rule_name,
            )
        self._groups[key].add(alert)
        return self._groups[key]

    def _evict(self, now: datetime.datetime) -> None:
        cutoff = now - datetime.timedelta(seconds=self.window_seconds)
        stale = [
            k
            for k, g in self._groups.items()
            if g.last_seen is not None and g.last_seen < cutoff
        ]
        for k in stale:
            del self._groups[k]

    def groups(self) -> List[CorrelationGroup]:
        return list(self._groups.values())

    def reset(self) -> None:
        self._groups.clear()
