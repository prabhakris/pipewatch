"""Tests for pipewatch.snapshot module."""

import json
import time
from pathlib import Path

import pytest

from pipewatch.health import HealthReport
from pipewatch.snapshot import PipelineSnapshot, SnapshotStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_report(pipeline_id: str = "pipe-1", score: float = 1.0) -> HealthReport:
    return HealthReport(
        pipeline_id=pipeline_id,
        score=score,
        status="healthy" if score >= 0.8 else "degraded",
        alerts=[],
        anomalies=[],
    )


# ---------------------------------------------------------------------------
# PipelineSnapshot
# ---------------------------------------------------------------------------

class TestPipelineSnapshot:
    def test_to_dict_contains_required_keys(self):
        snap = PipelineSnapshot(
            pipeline_id="p1",
            captured_at=1_000_000.0,
            health={"score": 1.0, "status": "healthy"},
        )
        d = snap.to_dict()
        assert d["pipeline_id"] == "p1"
        assert d["captured_at"] == 1_000_000.0
        assert "health" in d


# ---------------------------------------------------------------------------
# SnapshotStore
# ---------------------------------------------------------------------------

class TestSnapshotStore:
    def test_latest_returns_none_when_empty(self):
        store = SnapshotStore()
        assert store.latest("pipe-1") is None

    def test_record_creates_snapshot(self):
        store = SnapshotStore()
        snap = store.record("pipe-1", make_report())
        assert snap.pipeline_id == "pipe-1"
        assert snap.captured_at <= time.time()

    def test_latest_returns_most_recent(self):
        store = SnapshotStore()
        store.record("pipe-1", make_report(score=1.0))
        store.record("pipe-1", make_report(score=0.5))
        latest = store.latest("pipe-1")
        assert latest is not None
        assert latest.health["score"] == pytest.approx(0.5)

    def test_all_for_returns_chronological_list(self):
        store = SnapshotStore()
        store.record("pipe-1", make_report(score=1.0))
        store.record("pipe-1", make_report(score=0.9))
        store.record("pipe-2", make_report(pipeline_id="pipe-2"))
        snaps = store.all_for("pipe-1")
        assert len(snaps) == 2

    def test_clear_removes_all_snapshots(self):
        store = SnapshotStore()
        store.record("pipe-1", make_report())
        store.clear()
        assert store.latest("pipe-1") is None

    def test_save_and_load_roundtrip(self, tmp_path):
        store = SnapshotStore()
        store.record("pipe-1", make_report(score=0.75))
        store.record("pipe-2", make_report(pipeline_id="pipe-2", score=1.0))

        out = tmp_path / "snapshots.jsonl"
        store.save(out)

        new_store = SnapshotStore()
        new_store.load(out)

        assert new_store.latest("pipe-1") is not None
        assert new_store.latest("pipe-2") is not None
        assert new_store.latest("pipe-1").health["score"] == pytest.approx(0.75)

    def test_load_missing_file_is_noop(self, tmp_path):
        store = SnapshotStore()
        store.load(tmp_path / "nonexistent.jsonl")  # should not raise
        assert store.latest("pipe-1") is None
