"""Tests for pipewatch.digest_notifier."""
from datetime import datetime, timezone
from typing import List

from pipewatch.alerts import Alert
from pipewatch.alert_digest import AlertDigest
from pipewatch.digest_notifier import DigestNotifier, _format_digest
from pipewatch.notifier import NotificationChannel


class _RecordingChannel(NotificationChannel):
    def __init__(self) -> None:
        self.calls: List[dict] = []

    def send(self, subject: str, body: str) -> bool:  # type: ignore[override]
        self.calls.append({"subject": subject, "body": body})
        return True


def _make_alert(pipeline_id: str = "pipe_a", rule_name: str = "err") -> Alert:
    return Alert(
        pipeline_id=pipeline_id,
        rule_name=rule_name,
        metric_value=0.5,
        threshold=0.1,
        triggered_at=datetime.now(timezone.utc).isoformat(),
    )


class TestFormatDigest:
    def test_empty_entries_returns_no_alerts_message(self):
        msg = _format_digest([])
        assert "no alerts" in msg

    def test_non_empty_contains_pipeline_id(self):
        digest = AlertDigest(window_seconds=60)
        digest.add(_make_alert(pipeline_id="my_pipe"))
        entries = digest.summarise()
        msg = _format_digest(entries)
        assert "my_pipe" in msg

    def test_non_empty_contains_rule_name(self):
        digest = AlertDigest(window_seconds=60)
        digest.add(_make_alert(rule_name="custom_rule"))
        entries = digest.summarise()
        msg = _format_digest(entries)
        assert "custom_rule" in msg


class TestDigestNotifier:
    def _make_notifier(self) -> tuple:
        digest = AlertDigest(window_seconds=60)
        ch = _RecordingChannel()
        notifier = DigestNotifier(digest=digest, channels=[ch])
        return notifier, digest, ch

    def test_send_digest_calls_channel(self):
        notifier, digest, ch = self._make_notifier()
        digest.add(_make_alert())
        notifier.send_digest()
        assert len(ch.calls) == 1

    def test_send_digest_returns_true_per_channel(self):
        notifier, digest, _ = self._make_notifier()
        results = notifier.send_digest()
        assert results == [True]

    def test_flush_after_true_clears_digest(self):
        notifier, digest, _ = self._make_notifier()
        digest.add(_make_alert())
        notifier.send_digest(flush_after=True)
        assert digest.summarise() == []

    def test_flush_after_false_keeps_alerts(self):
        notifier, digest, _ = self._make_notifier()
        digest.add(_make_alert())
        notifier.send_digest(flush_after=False)
        assert len(digest.summarise()) == 1

    def test_multiple_channels_all_receive_message(self):
        digest = AlertDigest(window_seconds=60)
        ch1, ch2 = _RecordingChannel(), _RecordingChannel()
        notifier = DigestNotifier(digest=digest, channels=[ch1, ch2])
        digest.add(_make_alert())
        notifier.send_digest()
        assert len(ch1.calls) == 1
        assert len(ch2.calls) == 1

    def test_add_channel_appends(self):
        digest = AlertDigest(window_seconds=60)
        notifier = DigestNotifier(digest=digest)
        ch = _RecordingChannel()
        notifier.add_channel(ch)
        assert ch in notifier.channels

    def test_subject_contains_pipewatch(self):
        notifier, digest, ch = self._make_notifier()
        digest.add(_make_alert())
        notifier.send_digest()
        assert "pipewatch" in ch.calls[0]["subject"].lower()
