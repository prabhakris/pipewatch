"""Rate limiter for suppressing repeated alerts within a cooldown window."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple


@dataclass
class RateLimiter:
    """Suppresses duplicate alerts for the same (pipeline_id, rule_name) pair
    within a configurable cooldown period.

    Args:
        cooldown_seconds: Minimum seconds between repeated alerts for the same key.
    """

    cooldown_seconds: float = 300.0
    _last_fired: Dict[Tuple[str, str], datetime] = field(
        default_factory=dict, init=False, repr=False
    )

    def is_suppressed(self, pipeline_id: str, rule_name: str) -> bool:
        """Return True if the alert should be suppressed (cooldown not yet elapsed)."""
        key = (pipeline_id, rule_name)
        last = self._last_fired.get(key)
        if last is None:
            return False
        elapsed = (datetime.utcnow() - last).total_seconds()
        return elapsed < self.cooldown_seconds

    def record(self, pipeline_id: str, rule_name: str) -> None:
        """Record that an alert was fired for the given key at the current time."""
        self._last_fired[(pipeline_id, rule_name)] = datetime.utcnow()

    def last_fired_at(
        self, pipeline_id: str, rule_name: str
    ) -> Optional[datetime]:
        """Return the datetime the alert last fired, or None if never."""
        return self._last_fired.get((pipeline_id, rule_name))

    def reset(self, pipeline_id: Optional[str] = None, rule_name: Optional[str] = None) -> None:
        """Clear cooldown state.  If both args given, clears only that key.
        If only pipeline_id given, clears all rules for that pipeline.
        If neither given, clears everything.
        """
        if pipeline_id is not None and rule_name is not None:
            self._last_fired.pop((pipeline_id, rule_name), None)
        elif pipeline_id is not None:
            keys_to_remove = [k for k in self._last_fired if k[0] == pipeline_id]
            for k in keys_to_remove:
                del self._last_fired[k]
        else:
            self._last_fired.clear()
