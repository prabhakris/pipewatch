"""Tests for pipewatch.audit_log."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pipewatch.audit_log import AuditEntry, AuditLog


def make_entry(pipeline_id: str = "pipe-1", event: str = "run_completed") -> AuditEntry:
    return AuditEntry(
        pipeline_id=pipeline_id,
        event=event,
        timestamp=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        details={"records": 100},
    )


class TestAuditEntry:
    def test_to_dict_contains_required_keys(self):
        entry = make_entry()
        d = entry.to_dict()
        assert "pipeline_id" in d
        assert "event" in d
        assert "timestamp" in d
        assert "details" in d

    def test_to_dict_values(self):
        entry = make_entry(pipeline_id="p1", event="alert_fired")
        d = entry.to_dict()
        assert d["pipeline_id"] == "p1"
        assert d["event"] == "alert_fired"
        assert d["details"] == {"records": 100}

    def test_timestamp_is_iso_string(self):
        entry = make_entry()
        d = entry.to_dict()
        # Should be parseable back to datetime
        parsed = datetime.fromisoformat(d["timestamp"])
        assert parsed.year == 2024


class TestAuditLog:
    def test_empty_log_has_zero_length(self):
        log = AuditLog()
        assert len(log) == 0

    def test_record_increments_length(self):
        log = AuditLog()
        log.record(make_entry())
        assert len(log) == 1

    def test_entries_returns_all(self):
        log = AuditLog()
        log.record(make_entry(pipeline_id="a"))
        log.record(make_entry(pipeline_id="b"))
        assert len(log.entries()) == 2

    def test_entries_filtered_by_pipeline(self):
        log = AuditLog()
        log.record(make_entry(pipeline_id="a"))
        log.record(make_entry(pipeline_id="b"))
        log.record(make_entry(pipeline_id="a"))
        result = log.entries(pipeline_id="a")
        assert len(result) == 2
        assert all(e.pipeline_id == "a" for e in result)

    def test_clear_removes_entries(self):
        log = AuditLog()
        log.record(make_entry())
        log.clear()
        assert len(log) == 0

    def test_persist_to_file(self, tmp_path: Path):
        log_file = tmp_path / "audit" / "events.jsonl"
        log = AuditLog(log_path=log_file)
        log.record(make_entry(pipeline_id="pipe-x", event="run_started"))
        log.record(make_entry(pipeline_id="pipe-x", event="run_completed"))
        assert log_file.exists()
        lines = log_file.read_text().strip().splitlines()
        assert len(lines) == 2
        first = json.loads(lines[0])
        assert first["pipeline_id"] == "pipe-x"
        assert first["event"] == "run_started"

    def test_file_parent_created_automatically(self, tmp_path: Path):
        nested = tmp_path / "deep" / "nested" / "audit.jsonl"
        log = AuditLog(log_path=nested)
        log.record(make_entry())
        assert nested.exists()
