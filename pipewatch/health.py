"""Pipeline health scoring module for pipewatch."""
from dataclasses import dataclass, field
from typing import List, Optional
from pipewatch.metrics import PipelineMetric, failure_rate, throughput
from pipewatch.alerts import Alert
from pipewatch.anomaly import AnomalyResult


HEALTH_THRESHOLDS = {
    "failure_rate": 0.05,   # 5% failure rate degrades health
    "throughput_min": 1.0,  # records/sec below this degrades health
}


@dataclass
class HealthReport:
    pipeline_id: str
    score: float  # 0.0 (critical) to 1.0 (healthy)
    status: str   # "healthy", "degraded", "critical"
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "pipeline_id": self.pipeline_id,
            "score": self.score,
            "status": self.status,
            "reasons": self.reasons,
        }


def _status_from_score(score: float) -> str:
    if score >= 0.75:
        return "healthy"
    elif score >= 0.40:
        return "degraded"
    return "critical"


def compute_health(
    metric: PipelineMetric,
    alerts: Optional[List[Alert]] = None,
    anomalies: Optional[List[AnomalyResult]] = None,
) -> HealthReport:
    """Compute a health score for a pipeline based on metrics, alerts, and anomalies."""
    score = 1.0
    reasons: List[str] = []

    fr = failure_rate(metric)
    if fr > HEALTH_THRESHOLDS["failure_rate"]:
        penalty = min(fr * 4, 0.5)
        score -= penalty
        reasons.append(f"High failure rate: {fr:.1%}")

    tp = throughput(metric)
    if tp < HEALTH_THRESHOLDS["throughput_min"] and metric.duration_seconds > 0:
        score -= 0.2
        reasons.append(f"Low throughput: {tp:.2f} records/sec")

    alert_count = len(alerts) if alerts else 0
    if alert_count > 0:
        penalty = min(alert_count * 0.1, 0.3)
        score -= penalty
        reasons.append(f"{alert_count} active alert(s)")

    anomaly_count = len(anomalies) if anomalies else 0
    if anomaly_count > 0:
        score -= min(anomaly_count * 0.05, 0.2)
        reasons.append(f"{anomaly_count} anomaly detection(s) triggered")

    score = max(0.0, min(1.0, score))
    return HealthReport(
        pipeline_id=metric.pipeline_id,
        score=round(score, 4),
        status=_status_from_score(score),
        reasons=reasons,
    )
