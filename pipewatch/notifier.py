"""Notification dispatch module for pipewatch alerts."""

from __future__ import annotations

import logging
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from typing import List, Optional

from pipewatch.alerts import Alert

logger = logging.getLogger(__name__)


class NotificationChannel(ABC):
    """Abstract base class for notification channels."""

    @abstractmethod
    def send(self, alert: Alert) -> bool:
        """Send a notification for the given alert. Returns True on success."""


@dataclass
class LogChannel(NotificationChannel):
    """Logs alerts using Python's logging module."""

    level: str = "WARNING"

    def send(self, alert: Alert) -> bool:
        log_fn = getattr(logger, self.level.lower(), logger.warning)
        log_fn(
            "[pipewatch] Alert fired: rule=%s pipeline=%s value=%.4f message=%s",
            alert.rule_name,
            alert.pipeline_id,
            alert.value,
            alert.message,
        )
        return True


@dataclass
class EmailChannel(NotificationChannel):
    """Sends alert notifications via SMTP email."""

    recipients: List[str]
    sender: str
    smtp_host: str = "localhost"
    smtp_port: int = 25
    subject_prefix: str = "[pipewatch]"

    def send(self, alert: Alert) -> bool:
        subject = f"{self.subject_prefix} Alert: {alert.rule_name} on {alert.pipeline_id}"
        body = (
            f"Rule     : {alert.rule_name}\n"
            f"Pipeline : {alert.pipeline_id}\n"
            f"Value    : {alert.value:.4f}\n"
            f"Message  : {alert.message}\n"
            f"Fired at : {alert.fired_at}\n"
        )
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = ", ".join(self.recipients)
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.sendmail(self.sender, self.recipients, msg.as_string())
            logger.info("Email alert sent for rule '%s'.", alert.rule_name)
            return True
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to send email alert: %s", exc)
            return False


@dataclass
class Notifier:
    """Dispatches alerts to one or more notification channels."""

    channels: List[NotificationChannel] = field(default_factory=list)

    def add_channel(self, channel: NotificationChannel) -> None:
        self.channels.append(channel)

    def dispatch(self, alerts: List[Alert]) -> dict:
        """Send all alerts through every registered channel.

        Returns a summary dict with success/failure counts per channel.
        """
        summary: dict = {}
        for alert in alerts:
            for channel in self.channels:
                key = type(channel).__name__
                result = channel.send(alert)
                counts = summary.setdefault(key, {"success": 0, "failure": 0})
                if result:
                    counts["success"] += 1
                else:
                    counts["failure"] += 1
        return summary
