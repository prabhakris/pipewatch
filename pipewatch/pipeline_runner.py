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

    def reset(self) -> None:
        """Clear accumulated state (useful between test runs)."""
        self.registry.reset()
        self._collector = MetricsCollector()
