"""Tests for pipewatch.exporter."""

from __future__ import annotations

import json
import csv
import io
from datetime import datetime

import pytest

from pipewatch.metrics import PipelineMetric
from pipewatch.alerts import Alert
from pipewatch.exporter import to_json, to_csv, to_jsonl


def make_metric(
    pipeline_id: str = "pipe-1",
    total_records: int = 100,
    failed_records: int = 5,
    duration_seconds: float = 10.0,
) -> PipelineMetric:
    return PipelineMetric(
        pipeline_id=pipeline_id,
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        total_records=total_records,
        failed_records=failed_records,
        duration_seconds=duration_seconds,
    )


def make_alert(pipeline_id: str = "pipe-1", rule_name: str = "high_failure") -> Alert:
    return Alert(
        pipeline_id=pipeline_id,
        rule_name=rule_name,
        message="Failure rate too high",
        severity="critical",
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
    )


class TestToJson:
    def test_empty_list_returns_empty_array(self):
        result = to_json([])
        assert json.loads(result) == []

    def test_single_metric_serialized(self):
        metric = make_metric()
        result = json.loads(to_json([metric]))
        assert len(result) == 1
        assert result[0]["pipeline_id"] == "pipe-1"

    def test_multiple_metrics(self):
        metrics = [make_metric("pipe-1"), make_metric("pipe-2")]
        result = json.loads(to_json(metrics))
        assert len(result) == 2
        assert {r["pipeline_id"] for r in result} == {"pipe-1", "pipe-2"}

    def test_alert_serialized(self):
        alert = make_alert()
        result = json.loads(to_json([alert]))
        assert result[0]["rule_name"] == "high_failure"
        assert result[0]["severity"] == "critical"

    def test_unsupported_type_raises(self):
        with pytest.raises(TypeError, match="Unsupported export type"):
            to_json([object()])


class TestToCsv:
    def test_empty_list_returns_empty_string(self):
        assert to_csv([]) == ""

    def test_csv_has_header_row(self):
        metrics = [make_metric()]
        result = to_csv(metrics)
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) == 1
        assert "pipeline_id" in rows[0]

    def test_csv_values_correct(self):
        metrics = [make_metric(total_records=200, failed_records=10)]
        result = to_csv(metrics)
        reader = csv.DictReader(io.StringIO(result))
        row = next(reader)
        assert row["total_records"] == "200"
        assert row["failed_records"] == "10"

    def test_multiple_rows(self):
        metrics = [make_metric("pipe-1"), make_metric("pipe-2")]
        result = to_csv(metrics)
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) == 2


class TestToJsonl:
    def test_empty_returns_empty_string(self):
        assert to_jsonl([]) == ""

    def test_each_line_is_valid_json(self):
        items = [make_metric("pipe-1"), make_alert("pipe-2")]
        result = to_jsonl(items)
        lines = result.strip().split("\n")
        assert len(lines) == 2
        for line in lines:
            obj = json.loads(line)
            assert isinstance(obj, dict)

    def test_no_trailing_newline(self):
        result = to_jsonl([make_metric()])
        assert not result.endswith("\n")
