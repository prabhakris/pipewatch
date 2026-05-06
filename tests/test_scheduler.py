"""Tests for pipewatch.scheduler."""

import time
import threading
import pytest
from pipewatch.scheduler import PipelineScheduler, ScheduledJob


# ---------------------------------------------------------------------------
# ScheduledJob unit tests
# ---------------------------------------------------------------------------

class TestScheduledJob:
    def _make_job(self, interval: float = 5.0) -> ScheduledJob:
        return ScheduledJob(name="test", interval_seconds=interval, callback=lambda: None)

    def test_is_due_when_never_run(self):
        job = self._make_job()
        assert job.is_due(time.monotonic()) is True

    def test_not_due_immediately_after_run(self):
        job = self._make_job(interval=60.0)
        job.last_run = time.monotonic()
        assert job.is_due(time.monotonic()) is False

    def test_due_after_interval_elapsed(self):
        job = self._make_job(interval=1.0)
        job.last_run = time.monotonic() - 2.0
        assert job.is_due(time.monotonic()) is True

    def test_disabled_job_never_due(self):
        job = self._make_job()
        job.enabled = False
        assert job.is_due(time.monotonic()) is False


# ---------------------------------------------------------------------------
# PipelineScheduler unit tests
# ---------------------------------------------------------------------------

class TestPipelineScheduler:
    def test_register_and_job_stats(self):
        sched = PipelineScheduler()
        sched.register("pipe_a", 10.0, lambda: None)
        stats = sched.job_stats()
        assert "pipe_a" in stats
        assert stats["pipe_a"]["run_count"] == 0

    def test_duplicate_registration_raises(self):
        sched = PipelineScheduler()
        sched.register("pipe_a", 10.0, lambda: None)
        with pytest.raises(ValueError, match="already registered"):
            sched.register("pipe_a", 5.0, lambda: None)

    def test_unregister_removes_job(self):
        sched = PipelineScheduler()
        sched.register("pipe_a", 10.0, lambda: None)
        sched.unregister("pipe_a")
        assert "pipe_a" not in sched.job_stats()

    def test_unregister_nonexistent_is_safe(self):
        sched = PipelineScheduler()
        sched.unregister("ghost")  # should not raise

    def test_tick_executes_due_jobs(self):
        counter = {"n": 0}

        def increment():
            counter["n"] += 1

        sched = PipelineScheduler()
        sched.register("counter", 0.0, increment)
        sched._tick()
        assert counter["n"] == 1
        assert sched.job_stats()["counter"]["run_count"] == 1

    def test_tick_skips_non_due_jobs(self):
        counter = {"n": 0}
        sched = PipelineScheduler()
        sched.register("counter", 9999.0, lambda: counter.update({"n": counter["n"] + 1}))
        # Mark as recently run so it's not due
        sched._jobs["counter"].last_run = time.monotonic()
        sched._tick()
        assert counter["n"] == 0

    def test_tick_records_errors(self):
        def bad():
            raise RuntimeError("boom")

        sched = PipelineScheduler()
        sched.register("bad_job", 0.0, bad)
        sched._tick()
        assert sched.job_stats()["bad_job"]["error_count"] == 1

    def test_start_and_stop(self):
        event = threading.Event()
        sched = PipelineScheduler(tick_interval=0.05)
        sched.register("signal", 0.0, event.set)
        sched.start()
        triggered = event.wait(timeout=1.0)
        sched.stop()
        assert triggered, "Job was never executed after start()"

    def test_double_start_is_safe(self):
        sched = PipelineScheduler(tick_interval=0.1)
        sched.start()
        sched.start()  # should not raise or spawn extra thread
        sched.stop()
