"""Aggregates health reports across multiple pipelines."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pipewatch.health import HealthReport


@dataclass
class AggregatedHealth:
    reports: List[HealthReport] = field(default_factory=list)

    @property
    def average_score(self) -> float:
        if not self.reports:
            return 1.0
        return round(sum(r.score for r in self.reports) / len(self.reports), 4)

    @property
    def overall_status(self) -> str:
        if not self.reports:
            return "healthy"
        statuses = {r.status for r in self.reports}
        if "critical" in statuses:
            return "critical"
        if "degraded" in statuses:
            return "degraded"
        return "healthy"

    def pipelines_by_status(self, status: str) -> List[str]:
        return [r.pipeline_id for r in self.reports if r.status == status]

    def get(self, pipeline_id: str) -> Optional[HealthReport]:
        for r in self.reports:
            if r.pipeline_id == pipeline_id:
                return r
        return None

    def to_dict(self) -> dict:
        return {
            "average_score": self.average_score,
            "overall_status": self.overall_status,
            "pipeline_count": len(self.reports),
            "critical": self.pipelines_by_status("critical"),
            "degraded": self.pipelines_by_status("degraded"),
            "healthy": self.pipelines_by_status("healthy"),
            "reports": [r.to_dict() for r in self.reports],
        }


class HealthAggregator:
    """Collects and aggregates HealthReport objects across pipelines."""

    def __init__(self) -> None:
        self._reports: Dict[str, HealthReport] = {}

    def update(self, report: HealthReport) -> None:
        """Insert or replace the health report for a pipeline."""
        self._reports[report.pipeline_id] = report

    def aggregate(self) -> AggregatedHealth:
        """Return an AggregatedHealth snapshot of all tracked pipelines."""
        return AggregatedHealth(reports=list(self._reports.values()))

    def reset(self) -> None:
        self._reports.clear()
