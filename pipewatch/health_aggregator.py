"""Aggregates health reports across multiple pipelines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pipewatch.health import HealthReport


@dataclass
class AggregatedHealth:
    """Aggregated health summary across all tracked pipelines."""

    reports: Dict[str, HealthReport] = field(default_factory=dict)

    @property
    def average_score(self) -> float:
        """Return mean health score across all pipelines, or 1.0 if none."""
        if not self.reports:
            return 1.0
        return sum(r.score for r in self.reports.values()) / len(self.reports)

    @property
    def overall_status(self) -> str:
        """Return worst status across all pipelines."""
        priority = {"critical": 0, "degraded": 1, "healthy": 2}
        if not self.reports:
            return "healthy"
        statuses = [r.status for r in self.reports.values()]
        return min(statuses, key=lambda s: priority.get(s, 2))

    def pipelines_by_status(self, status: str) -> List[str]:
        """Return list of pipeline names matching the given status."""
        return [
            name
            for name, report in self.reports.items()
            if report.status == status
        ]

    def get(self, pipeline_name: str) -> Optional[HealthReport]:
        """Return the health report for a specific pipeline, or None."""
        return self.reports.get(pipeline_name)

    def update(self, pipeline_name: str, report: HealthReport) -> None:
        """Insert or replace the health report for a pipeline."""
        self.reports[pipeline_name] = report

    def remove(self, pipeline_name: str) -> None:
        """Remove a pipeline from the aggregation."""
        self.reports.pop(pipeline_name, None)

    def to_dict(self) -> dict:
        """Serialise to a plain dictionary."""
        return {
            "average_score": round(self.average_score, 4),
            "overall_status": self.overall_status,
            "pipeline_count": len(self.reports),
            "pipelines": {
                name: report.to_dict()
                for name, report in self.reports.items()
            },
        }
