"""Sends a formatted alert digest via notification channels."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from pipewatch.alert_digest import AlertDigest, DigestEntry
from pipewatch.notifier import NotificationChannel


def _format_digest(entries: List[DigestEntry]) -> str:
    """Render a digest entry list as a plain-text summary."""
    if not entries:
        return "[pipewatch] Alert digest: no alerts in window."
    lines = [f"[pipewatch] Alert digest — {len(entries)} group(s):\n"]
    for e in entries:
        lines.append(
            f"  • {e.pipeline_id} / {e.rule_name}: "
            f"{e.count} alert(s) "
            f"(last value={e.sample.metric_value:.4f}, "
            f"threshold={e.sample.threshold:.4f})"
        )
    return "\n".join(lines)


@dataclass
class DigestNotifier:
    """Sends a digest summary to one or more notification channels."""

    digest: AlertDigest
    channels: List[NotificationChannel] = field(default_factory=list)

    def add_channel(self, channel: NotificationChannel) -> None:
        self.channels.append(channel)

    def send_digest(self, flush_after: bool = True) -> List[bool]:
        """Summarise the current digest and dispatch to all channels.

        Returns a list of send-success booleans, one per channel.
        If flush_after is True the digest buffer is cleared afterwards.
        """
        entries = self.digest.summarise()
        message = _format_digest(entries)
        results = [ch.send(subject="pipewatch digest", body=message) for ch in self.channels]
        if flush_after:
            self.digest.flush()
        return results
