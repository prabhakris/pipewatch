"""Middleware that wraps PipelineRunner to emit audit log entries."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from pipewatch.audit_log import AuditEntry, AuditLog
from pipewatch.metrics import PipelineMetric
from pipewatch.pipeline_runner import PipelineRunner, RunReport


@dataclass
class AuditedRunner:
    """Wraps a PipelineRunner and records lifecycle events to an AuditLog."""

    runner: PipelineRunner
    audit_log: AuditLog
    _run_count: int = field(default=0, init=False)

    def run(self, metric: PipelineMetric) -> RunReport:
        """Execute the runner and emit audit entries for the run."""
        self.audit_log.record(
            AuditEntry(
                pipeline_id=metric.pipeline_id,
                event="run_started",
                details={"run_number": self._run_count + 1},
            )
        )

        report = self.runner.run(metric)
        self._run_count += 1

        details: dict = {
            "run_number": self._run_count,
            "has_issues": report.has_issues(),
            "alert_count": len(report.alerts),
            "anomaly_count": len(report.anomalies),
        }

        self.audit_log.record(
            AuditEntry(
                pipeline_id=metric.pipeline_id,
                event="run_completed",
                details=details,
            )
        )

        for alert in report.alerts:
            self.audit_log.record(
                AuditEntry(
                    pipeline_id=metric.pipeline_id,
                    event="alert_fired",
                    details={"rule": alert.rule_name, "message": alert.message},
                )
            )

        for anomaly in report.anomalies:
            self.audit_log.record(
                AuditEntry(
                    pipeline_id=metric.pipeline_id,
                    event="anomaly_detected",
                    details=anomaly.to_dict(),
                )
            )

        return report
