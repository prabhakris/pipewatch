"""Alert rules and notification logic for pipeline anomaly detection."""

from dataclasses import dataclass, field
from typing import Callable, List, Optional
from datetime import datetime

from pipewatch.metrics import PipelineMetric, failure_rate, throughput


@dataclass
class AlertRule:
    """Defines a threshold-based alert rule for a pipeline metric."""

    name: str
    description: str
    check: Callable[[PipelineMetric], bool]
    severity: str = "warning"  # "info", "warning", "critical"

    def evaluate(self, metric: PipelineMetric) -> Optional["Alert"]:
        """Return an Alert if the rule is triggered, otherwise None."""
        if self.check(metric):
            return Alert(
                rule_name=self.name,
                severity=self.severity,
                pipeline=metric.pipeline_name,
                message=self.description,
                triggered_at=datetime.utcnow(),
            )
        return None


@dataclass
class Alert:
    """Represents a triggered alert event."""

    rule_name: str
    severity: str
    pipeline: str
    message: str
    triggered_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "rule": self.rule_name,
            "severity": self.severity,
            "pipeline": self.pipeline,
            "message": self.message,
            "triggered_at": self.triggered_at.isoformat(),
        }


# Built-in default rules
HIGH_FAILURE_RATE_RULE = AlertRule(
    name="high_failure_rate",
    description="Failure rate exceeded 10%",
    check=lambda m: failure_rate(m) > 0.10,
    severity="critical",
)

LOW_THROUGHPUT_RULE = AlertRule(
    name="low_throughput",
    description="Throughput dropped below 1 record/second",
    check=lambda m: m.duration_seconds > 0 and throughput(m) < 1.0,
    severity="warning",
)

DEFAULT_RULES: List[AlertRule] = [HIGH_FAILURE_RATE_RULE, LOW_THROUGHPUT_RULE]


def evaluate_rules(
    metric: PipelineMetric,
    rules: Optional[List[AlertRule]] = None,
) -> List[Alert]:
    """Evaluate all rules against a metric and return triggered alerts."""
    active_rules = rules if rules is not None else DEFAULT_RULES
    alerts = []
    for rule in active_rules:
        alert = rule.evaluate(metric)
        if alert:
            alerts.append(alert)
    return alerts
