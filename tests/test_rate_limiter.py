"""Tests for pipewatch.rate_limiter."""

from datetime import datetime, timedelta

import pytest

from pipewatch.rate_limiter import RateLimiter


class TestRateLimiter:
    # ------------------------------------------------------------------
    # is_suppressed
    # ------------------------------------------------------------------

    def test_not_suppressed_when_never_fired(self):
        rl = RateLimiter(cooldown_seconds=60)
        assert rl.is_suppressed("pipe_a", "high_failure") is False

    def test_suppressed_immediately_after_record(self):
        rl = RateLimiter(cooldown_seconds=60)
        rl.record("pipe_a", "high_failure")
        assert rl.is_suppressed("pipe_a", "high_failure") is True

    def test_not_suppressed_after_cooldown_elapsed(self):
        rl = RateLimiter(cooldown_seconds=1)
        rl.record("pipe_a", "high_failure")
        # Manually backdate the timestamp to simulate elapsed time
        rl._last_fired[("pipe_a", "high_failure")] = (
            datetime.utcnow() - timedelta(seconds=2)
        )
        assert rl.is_suppressed("pipe_a", "high_failure") is False

    def test_different_rules_are_independent(self):
        rl = RateLimiter(cooldown_seconds=300)
        rl.record("pipe_a", "rule_x")
        assert rl.is_suppressed("pipe_a", "rule_y") is False

    def test_different_pipelines_are_independent(self):
        rl = RateLimiter(cooldown_seconds=300)
        rl.record("pipe_a", "rule_x")
        assert rl.is_suppressed("pipe_b", "rule_x") is False

    # ------------------------------------------------------------------
    # last_fired_at
    # ------------------------------------------------------------------

    def test_last_fired_at_returns_none_when_never_fired(self):
        rl = RateLimiter()
        assert rl.last_fired_at("pipe_a", "rule_x") is None

    def test_last_fired_at_returns_datetime_after_record(self):
        rl = RateLimiter()
        before = datetime.utcnow()
        rl.record("pipe_a", "rule_x")
        after = datetime.utcnow()
        ts = rl.last_fired_at("pipe_a", "rule_x")
        assert ts is not None
        assert before <= ts <= after

    # ------------------------------------------------------------------
    # reset
    # ------------------------------------------------------------------

    def test_reset_all_clears_everything(self):
        rl = RateLimiter()
        rl.record("pipe_a", "rule_x")
        rl.record("pipe_b", "rule_y")
        rl.reset()
        assert rl.last_fired_at("pipe_a", "rule_x") is None
        assert rl.last_fired_at("pipe_b", "rule_y") is None

    def test_reset_by_pipeline_clears_only_that_pipeline(self):
        rl = RateLimiter()
        rl.record("pipe_a", "rule_x")
        rl.record("pipe_b", "rule_y")
        rl.reset(pipeline_id="pipe_a")
        assert rl.last_fired_at("pipe_a", "rule_x") is None
        assert rl.last_fired_at("pipe_b", "rule_y") is not None

    def test_reset_specific_key_clears_only_that_key(self):
        rl = RateLimiter()
        rl.record("pipe_a", "rule_x")
        rl.record("pipe_a", "rule_y")
        rl.reset(pipeline_id="pipe_a", rule_name="rule_x")
        assert rl.last_fired_at("pipe_a", "rule_x") is None
        assert rl.last_fired_at("pipe_a", "rule_y") is not None

    def test_zero_cooldown_never_suppresses(self):
        rl = RateLimiter(cooldown_seconds=0)
        rl.record("pipe_a", "rule_x")
        assert rl.is_suppressed("pipe_a", "rule_x") is False
