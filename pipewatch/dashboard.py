"""Simple text-based dashboard for displaying pipeline health summaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from pipewatch.health_aggregator import AggregatedHealth
from pipewatch.snapshot_manager import SnapshotManager


_STATUS_ICON = {
    "healthy": "✓",
    "degraded": "!",
    "unhealthy": "✗",
}

_STATUS_COLOR = {
    "healthy": "\033[92m",
    "degraded": "\033[93m",
    "unhealthy": "\033[91m",
}

_RESET = "\033[0m"


@dataclass
class DashboardRow:
    pipeline_id: str
    status: str
    score: float
    alert_count: int
    anomaly_count: int

    def render(self, colorize: bool = True) -> str:
        icon = _STATUS_ICON.get(self.status, "?")
        line = (
            f"  [{icon}] {self.pipeline_id:<30} "
            f"score={self.score:.2f}  "
            f"alerts={self.alert_count}  "
            f"anomalies={self.anomaly_count}"
        )
        if colorize:
            color = _STATUS_COLOR.get(self.status, "")
            return f"{color}{line}{_RESET}"
        return line


def build_rows(aggregated: AggregatedHealth) -> List[DashboardRow]:
    """Build dashboard rows from an AggregatedHealth snapshot."""
    rows: List[DashboardRow] = []
    for pipeline_id, report in aggregated.reports.items():
        rows.append(
            DashboardRow(
                pipeline_id=pipeline_id,
                status=report.status,
                score=report.score,
                alert_count=len(report.alerts),
                anomaly_count=len(report.anomalies),
            )
        )
    rows.sort(key=lambda r: r.score)
    return rows


def render_dashboard(
    aggregated: AggregatedHealth,
    title: str = "PipeWatch Dashboard",
    colorize: bool = True,
) -> str:
    """Render a full dashboard string from aggregated health data."""
    lines: List[str] = []
    lines.append(f"\n{'=' * 60}")
    lines.append(f"  {title}")
    lines.append(f"  Overall: {aggregated.overall_status().upper()}  "
                 f"Avg Score: {aggregated.average_score():.2f}")
    lines.append(f"{'=' * 60}")

    rows = build_rows(aggregated)
    if not rows:
        lines.append("  No pipelines tracked yet.")
    else:
        for row in rows:
            lines.append(row.render(colorize=colorize))

    lines.append(f"{'=' * 60}\n")
    return "\n".join(lines)
