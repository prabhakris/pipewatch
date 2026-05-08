"""Tests for pipewatch.alert_digest."""
from datetime import datetime, timedelta, timezone

import pytest

from pipewatch.alerts import Alert
from pipewatch.alert_digest import AlertDigest, DigestEntry


def _make_alert(
    pipeline_id: str = "pipe_a",
    rule_name: str = "high_failure",
    metric_value: float = 0.5,
    offset_seconds: float = 0.0,
) -> Alert:
    ts = datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)
    return Alert(
        pipeline_id=pipeline_id,
        rule_name=rule_name,
        metric_value=metric_value,
        threshold=0.1,
        triggered_at=ts.isoformat(),
    )


class TestAlertDigest:
    def test_empty_digest_returns_no_entries(self):
        digest = AlertDigest(window_seconds=60)
        assert digest.summarise() == []

    def test_single_alert_produces_one_entry(self):
        digest = AlertDigest(window_seconds=60)
        digest.add(_make_alert())
        entries = digest.summarise()
        assert len(entries) == 1
        entry = entries[0]
        assert entry.pipeline_id == "pipe_a"
        assert entry.rule_name == "high_failure"
        assert entry.count == 1

    def test_count_aggregates_same_key(self):
        digest = AlertDigest(window_seconds=60)
        for _ in range(4):
            digest.add(_make_alert())
        entries = digest.summarise()
        assert len(entries) == 1
        assert entries[0].count == 4

    def test_different_rules_produce_separate_entries(self):
        digest = AlertDigest(window_seconds=60)
        digest.add(_make_alert(rule_name="high_failure"))
        digest.add(_make_alert(rule_name="low_throughput"))
        entries = digest.summarise()
        assert len(entries) == 2

    def test_different_pipelines_produce_separate_entries(self):
        digest = AlertDigest(window_seconds=60)
        digest.add(_make_alert(pipeline_id="pipe_a"))
        digest.add(_make_alert(pipeline_id="pipe_b"))
        entries = digest.summarise()
        assert len(entries) == 2

    def test_alerts_outside_window_excluded(self):
        digest = AlertDigest(window_seconds=60)
        digest.add(_make_alert(offset_seconds=-120))  # 2 min old
        entries = digest.summarise()
        assert entries == []

    def test_sample_is_most_recent_alert(self):
        digest = AlertDigest(window_seconds=300)
        a1 = _make_alert(metric_value=0.3, offset_seconds=-10)
        a2 = _make_alert(metric_value=0.9, offset_seconds=0)
        digest.add(a1)
        digest.add(a2)
        entry = digest.summarise()[0]
        assert entry.sample.metric_value == pytest.approx(0.9)

    def test_flush_clears_buffer(self):
        digest = AlertDigest(window_seconds=60)
        digest.add(_make_alert())
        digest.flush()
        assert digest.summarise() == []

    def test_to_dict_contains_required_keys(self):
        digest = AlertDigest(window_seconds=60)
        digest.add(_make_alert())
        entry = digest.summarise()[0]
        d = entry.to_dict()
        for key in ("pipeline_id", "rule_name", "count", "first_seen", "last_seen", "sample"):
            assert key in d

    def test_first_and_last_seen_ordering(self):
        digest = AlertDigest(window_seconds=300)
        early = _make_alert(offset_seconds=-30)
        late = _make_alert(offset_seconds=0)
        digest.add(early)
        digest.add(late)
        entry = digest.summarise()[0]
        assert entry.first_seen < entry.last_seen
