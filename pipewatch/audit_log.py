"""Append-only audit log for recording pipeline run events."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


@dataclass
class AuditEntry:
    pipeline_id: str
    event: str  # e.g. "run_started", "run_completed", "alert_fired", "anomaly_detected"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "pipeline_id": self.pipeline_id,
            "event": self.event,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


class AuditLog:
    """In-memory audit log with optional file persistence."""

    def __init__(self, log_path: Optional[Path] = None) -> None:
        self._entries: List[AuditEntry] = []
        self._log_path = log_path
        if log_path is not None:
            log_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, entry: AuditEntry) -> None:
        """Append an entry to the log and optionally persist it."""
        self._entries.append(entry)
        if self._log_path is not None:
            with self._log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry.to_dict()) + "\n")

    def entries(self, pipeline_id: Optional[str] = None) -> List[AuditEntry]:
        """Return all entries, optionally filtered by pipeline_id."""
        if pipeline_id is None:
            return list(self._entries)
        return [e for e in self._entries if e.pipeline_id == pipeline_id]

    def clear(self) -> None:
        """Remove all in-memory entries (does not truncate the file)."""
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)
