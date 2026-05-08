"""Alert digest: groups and summarises alerts over a time window."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from pipewatch.alerts import Alert


@dataclass
class DigestEntry:
    """Aggregated count for a single (pipeline_id, rule_name) pair."""

    pipeline_id: str
    rule_name: str
    count: int
    first_seen: datetime
    last_seen: datetime
    sample: Alert  # most-recent alert for context

    def to_dict(self) -> dict:
        return {
            "pipeline_id": self.pipeline_id,
            "rule_name": self.rule_name,
            "count": self.count,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "sample": self.sample.to_dict(),
        }


@dataclass
class AlertDigest:
    """Collects alerts and produces a grouped digest summary."""

    window_seconds: float = 300.0
    _alerts: List[Alert] = field(default_factory=list, init=False, repr=False)

    def add(self, alert: Alert) -> None:
        """Add an alert to the digest buffer."""
        self._alerts.append(alert)

    def _cutoff(self, now: Optional[datetime] = None) -> datetime:
        now = now or datetime.now(timezone.utc)
        from datetime import timedelta
        return now - timedelta(seconds=self.window_seconds)

    def summarise(self, now: Optional[datetime] = None) -> List[DigestEntry]:
        """Return digest entries for alerts within the current window."""
        cutoff = self._cutoff(now)
        grouped: Dict[tuple, List[Alert]] = {}
        for alert in self._alerts:
            ts = datetime.fromisoformat(alert.triggered_at)
            if ts < cutoff:
                continue
            key = (alert.pipeline_id, alert.rule_name)
            grouped.setdefault(key, []).append(alert)

        entries: List[DigestEntry] = []
        for (pipeline_id, rule_name), alerts in grouped.items():
            timestamps = [datetime.fromisoformat(a.triggered_at) for a in alerts]
            entries.append(
                DigestEntry(
                    pipeline_id=pipeline_id,
                    rule_name=rule_name,
                    count=len(alerts),
                    first_seen=min(timestamps),
                    last_seen=max(timestamps),
                    sample=alerts[-1],
                )
            )
        return entries

    def flush(self) -> None:
        """Clear all buffered alerts."""
        self._alerts.clear()
