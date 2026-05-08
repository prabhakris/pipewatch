"""Wraps PipelineRunner to apply escalation policies before routing alerts."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from pipewatch.alert_escalation import AlertEscalator, EscalationPolicy
from pipewatch.alert_router import AlertRouter
from pipewatch.metrics import PipelineMetric
from pipewatch.pipeline_runner import PipelineRunner, RunReport


@dataclass
class EscalationRunner:
    """Delegates to PipelineRunner, then escalates and routes resulting alerts."""

    runner: PipelineRunner
    escalator: AlertEscalator = field(default_factory=AlertEscalator)
    router: AlertRouter = field(default_factory=AlertRouter)

    def add_policy(self, policy: EscalationPolicy) -> None:
        self.escalator.add_policy(policy)

    def run(self, metric: PipelineMetric) -> RunReport:
        report = self.runner.run(metric)

        escalated_alerts = [self.escalator.evaluate(a) for a in report.alerts]

        for alert in escalated_alerts:
            self.router.route(alert)

        return RunReport(
            metric=report.metric,
            alerts=escalated_alerts,
            anomalies=report.anomalies,
        )
