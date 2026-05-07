"""Tests for pipewatch.dashboard."""

from __future__ import annotations

import pytest

from pipewatch.dashboard import DashboardRow, build_rows, render_dashboard
from pipewatch.health import HealthReport
from pipewatch.health_aggregator import AggregatedHealth


def make_report(pipeline_id: str, status: str, score: float,
                alerts=None, anomalies=None) -> HealthReport:
    return HealthReport(
        pipeline_id=pipeline_id,
        status=status,
        score=score,
        alerts=alerts or [],
        anomalies=anomalies or [],
    )


def make_aggregated(*reports: HealthReport) -> AggregatedHealth:
    agg = AggregatedHealth()
    for r in reports:
        agg.reports[r.pipeline_id] = r
    return agg


class TestDashboardRow:
    def test_render_no_color_contains_pipeline_id(self):
        row = DashboardRow("etl-main", "healthy", 0.95, 0, 0)
        rendered = row.render(colorize=False)
        assert "etl-main" in rendered

    def test_render_no_color_contains_score(self):
        row = DashboardRow("etl-main", "healthy", 0.95, 0, 0)
        rendered = row.render(colorize=False)
        assert "0.95" in rendered

    def test_render_no_color_contains_alert_count(self):
        row = DashboardRow("etl-main", "degraded", 0.60, 3, 1)
        rendered = row.render(colorize=False)
        assert "alerts=3" in rendered
        assert "anomalies=1" in rendered

    def test_render_with_color_contains_escape_codes(self):
        row = DashboardRow("etl-main", "unhealthy", 0.20, 5, 2)
        rendered = row.render(colorize=True)
        assert "\033[" in rendered

    def test_render_healthy_icon(self):
        row = DashboardRow("pipe", "healthy", 1.0, 0, 0)
        rendered = row.render(colorize=False)
        assert "[✓]" in rendered

    def test_render_unhealthy_icon(self):
        row = DashboardRow("pipe", "unhealthy", 0.1, 2, 0)
        rendered = row.render(colorize=False)
        assert "[✗]" in rendered


class TestBuildRows:
    def test_empty_aggregated_returns_empty_list(self):
        agg = make_aggregated()
        assert build_rows(agg) == []

    def test_rows_sorted_by_score_ascending(self):
        agg = make_aggregated(
            make_report("a", "healthy", 0.9),
            make_report("b", "unhealthy", 0.2),
            make_report("c", "degraded", 0.6),
        )
        rows = build_rows(agg)
        scores = [r.score for r in rows]
        assert scores == sorted(scores)

    def test_row_fields_populated_correctly(self):
        from pipewatch.alerts import Alert
        alert = Alert(rule_name="high_fail", pipeline_id="p1",
                      metric_value=0.5, threshold=0.3, message="fail")
        agg = make_aggregated(make_report("p1", "degraded", 0.55, alerts=[alert]))
        rows = build_rows(agg)
        assert len(rows) == 1
        assert rows[0].alert_count == 1
        assert rows[0].pipeline_id == "p1"


class TestRenderDashboard:
    def test_contains_title(self):
        agg = make_aggregated()
        output = render_dashboard(agg, title="My Dashboard", colorize=False)
        assert "My Dashboard" in output

    def test_contains_overall_status(self):
        agg = make_aggregated(make_report("p", "healthy", 1.0))
        output = render_dashboard(agg, colorize=False)
        assert "HEALTHY" in output

    def test_no_pipelines_message(self):
        agg = make_aggregated()
        output = render_dashboard(agg, colorize=False)
        assert "No pipelines tracked" in output

    def test_pipeline_id_appears_in_output(self):
        agg = make_aggregated(make_report("my-pipeline", "healthy", 0.9))
        output = render_dashboard(agg, colorize=False)
        assert "my-pipeline" in output
