"""Pipeline runner: orchestrates metric collection, anomaly detection, and alerting."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from pipewatch.alerts import AlertRule, evaluate_rules
from pipewatch.anomaly import AnomalyResult
from pipewatch.detector_registry import DetectorRegistry
from pipewatch.metrics import MetricsCollector, PipelineMetric
from pipewatch.notifier import NotificationChannel

logger = logging.getLogger(__name__)


@dataclass
class RunReport:
    """Aggregated result of a single pipeline observation run."""

    metric: PipelineMetric
    alerts: List[object] = field(default_factory=list)
    anomalies: List[AnomalyResult] = field(default_factory=list)

    def has_issues(self) -> bool:
        return bool(self.alerts or self.anomalies)

    def to_dict(self) -> dict:
        return {
            "metric": self.metric.to_dict(),
            "alerts": [a.to_dict() for a in self.alerts],
            "anomalies": [a.to_dict() for a in self.anomalies],
            "has_issues": self.has_issues(),
        }


class PipelineRunner:
    """Coordinates the full observe → detect → alert → notify cycle."""

    def __init__(
        self,
        rules: Optional[List[AlertRule]] = None,
        channels: Optional[List[NotificationChannel]] = None,
        registry: Optional[DetectorRegistry] = None,
    ) -> None:
        self.rules: List[AlertRule] = rules or []
        self.channels: List[NotificationChannel] = channels or []
        self.registry: DetectorRegistry = registry or DetectorRegistry()
        self._collector = MetricsCollector()

    def observe(self, metric: PipelineMetric) -> RunReport:
        """Process a single metric snapshot and return a RunReport."""
        self._collector.record(metric)

        alerts = evaluate_rules(metric, self.rules)
        anomalies = self.registry.evaluate(metric)

        report = RunReport(metric=metric, alerts=alerts, anomalies=anomalies)

        if report.has_issues():
            self._notify(report)

        logger.debug(
            "Observed pipeline=%s alerts=%d anomalies=%d",
            metric.pipeline_id,
            len(alerts),
            len(anomalies),
        )
        return report

    def _notify(self, report: RunReport) -> None:
        issues = report.alerts + report.anomalies  # type: ignore[operator]
        for issue in issues:
            for channel in self.channels:
                try:
                    channel.send(issue)
                except Exception:  # pragma: no cover
                    logger.exception("Notification failed via %s", channel)

    def observe_many(self, metrics: List[PipelineMetric]) -> List[RunReport]:
        """Process multiple metric snapshots in sequence and return all RunReports.

        Useful for batch ingestion or replaying historical data.
        """
        reports = []
        for metric in metrics:
            reports.append(self.observe(metric))
        return reports

    def summary(self) -> dict:
        """Return a high-level summary of all reports processed so far.

        Includes total observations and counts of runs that had at least one
        alert or anomaly, giving a quick health overview of the pipeline.
        """
        all_metrics = self._collector.all()
        total = len(all_metrics)
        issues_count = sum(
            1
            for m in all_metrics
            if evaluate_rules(m, self.rules) or self.registry.evaluate(m)
        )
        return {
            "total_observations": total,
            "observations_with_issues": issues_count,
            "healthy_ratio": round((total - issues_count) / total, 4) if total else 1.0,
        }
