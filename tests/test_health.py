"""Tests for pipewatch.health module."""
import pytest
from pipewatch.metrics import PipelineMetric
from pipewatch.alerts import Alert
from pipewatch.anomaly import AnomalyResult
from pipewatch.health import compute_health, HealthReport, _status_from_score


def make_metric(
    pipeline_id="pipe-1",
    total_records=1000,
    failed_records=0,
    duration_seconds=100.0,
):
    return PipelineMetric(
        pipeline_id=pipeline_id,
        total_records=total_records,
        failed_records=failed_records,
        duration_seconds=duration_seconds,
    )


def make_alert(pipeline_id="pipe-1", rule_name="test_rule", message="alert"):
    return Alert(pipeline_id=pipeline_id, rule_name=rule_name, message=message)


def make_anomaly(pipeline_id="pipe-1", metric_name="failure_rate", value=0.1, z_score=3.5):
    return AnomalyResult(
        pipeline_id=pipeline_id,
        metric_name=metric_name,
        value=value,
        mean=0.01,
        std_dev=0.005,
        z_score=z_score,
    )


class TestStatusFromScore:
    def test_healthy(self):
        assert _status_from_score(1.0) == "healthy"
        assert _status_from_score(0.75) == "healthy"

    def test_degraded(self):
        assert _status_from_score(0.74) == "degraded"
        assert _status_from_score(0.40) == "degraded"

    def test_critical(self):
        assert _status_from_score(0.39) == "critical"
        assert _status_from_score(0.0) == "critical"


class TestComputeHealth:
    def test_perfect_health_no_issues(self):
        metric = make_metric(failed_records=0)
        report = compute_health(metric)
        assert report.score == 1.0
        assert report.status == "healthy"
        assert report.reasons == []

    def test_high_failure_rate_reduces_score(self):
        metric = make_metric(total_records=100, failed_records=30)
        report = compute_health(metric)
        assert report.score < 1.0
        assert any("failure rate" in r.lower() for r in report.reasons)

    def test_alerts_reduce_score(self):
        metric = make_metric()
        alerts = [make_alert(), make_alert()]
        report = compute_health(metric, alerts=alerts)
        assert report.score < 1.0
        assert any("alert" in r.lower() for r in report.reasons)

    def test_anomalies_reduce_score(self):
        metric = make_metric()
        anomalies = [make_anomaly()]
        report = compute_health(metric, anomalies=anomalies)
        assert report.score < 1.0
        assert any("anomaly" in r.lower() for r in report.reasons)

    def test_score_clamped_to_zero(self):
        metric = make_metric(total_records=100, failed_records=100)
        alerts = [make_alert() for _ in range(10)]
        anomalies = [make_anomaly() for _ in range(10)]
        report = compute_health(metric, alerts=alerts, anomalies=anomalies)
        assert report.score >= 0.0
        assert report.status == "critical"

    def test_to_dict_has_required_keys(self):
        metric = make_metric()
        report = compute_health(metric)
        d = report.to_dict()
        assert "pipeline_id" in d
        assert "score" in d
        assert "status" in d
        assert "reasons" in d

    def test_pipeline_id_propagated(self):
        metric = make_metric(pipeline_id="etl-orders")
        report = compute_health(metric)
        assert report.pipeline_id == "etl-orders"

    def test_low_throughput_reduces_score(self):
        metric = make_metric(total_records=1, duration_seconds=100.0)
        report = compute_health(metric)
        assert report.score < 1.0
        assert any("throughput" in r.lower() for r in report.reasons)
