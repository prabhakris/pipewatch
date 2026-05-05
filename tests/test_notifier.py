"""Tests for pipewatch.notifier module."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from pipewatch.alerts import Alert
from pipewatch.notifier import EmailChannel, LogChannel, Notifier


def make_alert(
    rule_name: str = "high_failure_rate",
    pipeline_id: str = "etl_orders",
    value: float = 0.35,
    message: str = "failure_rate exceeded threshold",
) -> Alert:
    return Alert(
        rule_name=rule_name,
        pipeline_id=pipeline_id,
        value=value,
        message=message,
        fired_at=datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
    )


class TestLogChannel:
    def test_send_returns_true(self, caplog):
        channel = LogChannel(level="WARNING")
        alert = make_alert()
        import logging

        with caplog.at_level(logging.WARNING, logger="pipewatch.notifier"):
            result = channel.send(alert)
        assert result is True
        assert "high_failure_rate" in caplog.text
        assert "etl_orders" in caplog.text

    def test_send_debug_level(self, caplog):
        channel = LogChannel(level="debug")
        alert = make_alert()
        import logging

        with caplog.at_level(logging.DEBUG, logger="pipewatch.notifier"):
            result = channel.send(alert)
        assert result is True


class TestEmailChannel:
    def _make_channel(self) -> EmailChannel:
        return EmailChannel(
            recipients=["ops@example.com"],
            sender="pipewatch@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
        )

    def test_send_success(self):
        channel = self._make_channel()
        alert = make_alert()
        mock_server = MagicMock()
        with patch("pipewatch.notifier.smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__.return_value = mock_server
            result = channel.send(alert)
        assert result is True
        mock_server.sendmail.assert_called_once()
        args = mock_server.sendmail.call_args[0]
        assert args[0] == "pipewatch@example.com"
        assert args[1] == ["ops@example.com"]
        assert "high_failure_rate" in args[2]

    def test_subject_contains_rule_and_pipeline(self):
        channel = self._make_channel()
        alert = make_alert(rule_name="low_throughput", pipeline_id="etl_users")
        captured = {}
        mock_server = MagicMock()

        def capture_sendmail(sender, recipients, msg_str):
            captured["msg"] = msg_str

        mock_server.sendmail.side_effect = capture_sendmail
        with patch("pipewatch.notifier.smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__.return_value = mock_server
            channel.send(alert)
        assert "low_throughput" in captured["msg"]
        assert "etl_users" in captured["msg"]


class TestNotifier:
    def test_dispatch_empty_alerts_returns_empty_summary(self):
        notifier = Notifier(channels=[LogChannel()])
        summary = notifier.dispatch([])
        assert summary == {}

    def test_dispatch_calls_all_channels(self):
        ch1 = MagicMock(spec=LogChannel)
        ch1.send.return_value = True
        ch1.__class__ = LogChannel
        ch2 = MagicMock(spec=LogChannel)
        ch2.send.return_value = False
        ch2.__class__ = LogChannel
        notifier = Notifier(channels=[ch1, ch2])
        alert = make_alert()
        summary = notifier.dispatch([alert])
        ch1.send.assert_called_once_with(alert)
        ch2.send.assert_called_once_with(alert)
        assert summary["LogChannel"]["success"] == 1
        assert summary["LogChannel"]["failure"] == 1

    def test_add_channel(self):
        notifier = Notifier()
        assert len(notifier.channels) == 0
        notifier.add_channel(LogChannel())
        assert len(notifier.channels) == 1

    def test_dispatch_multiple_alerts(self, caplog):
        import logging

        channel = LogChannel()
        notifier = Notifier(channels=[channel])
        alerts = [make_alert(rule_name=f"rule_{i}") for i in range(3)]
        with caplog.at_level(logging.WARNING, logger="pipewatch.notifier"):
            summary = notifier.dispatch(alerts)
        assert summary["LogChannel"]["success"] == 3
        assert summary["LogChannel"]["failure"] == 0
