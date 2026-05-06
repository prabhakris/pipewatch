"""Scheduler for periodically running pipeline monitors."""

import time
import logging
import threading
from typing import Callable, Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ScheduledJob:
    """Represents a scheduled monitoring job."""
    name: str
    interval_seconds: float
    callback: Callable[[], None]
    enabled: bool = True
    last_run: Optional[float] = None
    run_count: int = 0
    error_count: int = 0

    def is_due(self, now: float) -> bool:
        """Return True if the job is due to run."""
        if not self.enabled:
            return False
        if self.last_run is None:
            return True
        return (now - self.last_run) >= self.interval_seconds


class PipelineScheduler:
    """Runs registered pipeline monitoring jobs on a fixed interval."""

    def __init__(self, tick_interval: float = 1.0) -> None:
        self._jobs: Dict[str, ScheduledJob] = {}
        self._tick_interval = tick_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def register(self, name: str, interval_seconds: float, callback: Callable[[], None]) -> None:
        """Register a new monitoring job."""
        if name in self._jobs:
            raise ValueError(f"Job '{name}' is already registered.")
        self._jobs[name] = ScheduledJob(
            name=name,
            interval_seconds=interval_seconds,
            callback=callback,
        )
        logger.debug("Registered job '%s' every %.1fs", name, interval_seconds)

    def unregister(self, name: str) -> None:
        """Remove a job by name."""
        self._jobs.pop(name, None)

    def _tick(self) -> None:
        now = time.monotonic()
        for job in list(self._jobs.values()):
            if job.is_due(now):
                try:
                    job.callback()
                    job.run_count += 1
                except Exception as exc:  # noqa: BLE001
                    job.error_count += 1
                    logger.error("Job '%s' raised an error: %s", job.name, exc)
                finally:
                    job.last_run = time.monotonic()

    def _run_loop(self) -> None:
        while self._running:
            self._tick()
            time.sleep(self._tick_interval)

    def start(self) -> None:
        """Start the scheduler in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="pipewatch-scheduler")
        self._thread.start()
        logger.info("Scheduler started with %d job(s).", len(self._jobs))

    def stop(self) -> None:
        """Stop the scheduler gracefully."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=self._tick_interval * 2)
        logger.info("Scheduler stopped.")

    def job_stats(self) -> Dict[str, dict]:
        """Return run statistics for all registered jobs."""
        return {
            name: {"run_count": j.run_count, "error_count": j.error_count, "enabled": j.enabled}
            for name, j in self._jobs.items()
        }
