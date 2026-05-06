"""Tests for pipewatch.config."""

import json
import pytest
from pathlib import Path

from pipewatch.config import (
    PipelineConfig,
    WatchConfig,
    load_config,
    load_config_from_dict,
)


MINIMAL_RAW = {
    "pipelines": [
        {"name": "etl_daily"},
        {
            "name": "etl_hourly",
            "interval_seconds": 3600,
            "min_samples": 5,
            "alert_rules": [{"metric": "failure_rate", "threshold": 0.1}],
            "notifiers": [{"type": "log"}],
            "tags": {"env": "prod"},
        },
    ],
    "global_tags": {"region": "us-east-1"},
}


class TestPipelineConfig:
    def test_defaults(self):
        cfg = PipelineConfig(name="my_pipe")
        assert cfg.interval_seconds == 60
        assert cfg.min_samples == 10
        assert cfg.alert_rules == []
        assert cfg.notifiers == []
        assert cfg.tags == {}

    def test_to_dict_contains_all_keys(self):
        cfg = PipelineConfig(name="p", tags={"k": "v"})
        d = cfg.to_dict()
        assert d["name"] == "p"
        assert d["tags"] == {"k": "v"}
        assert "interval_seconds" in d
        assert "alert_rules" in d


class TestWatchConfig:
    def test_get_pipeline_found(self):
        cfg = load_config_from_dict(MINIMAL_RAW)
        p = cfg.get_pipeline("etl_daily")
        assert p is not None
        assert p.name == "etl_daily"

    def test_get_pipeline_not_found(self):
        cfg = load_config_from_dict(MINIMAL_RAW)
        assert cfg.get_pipeline("nonexistent") is None

    def test_global_tags(self):
        cfg = load_config_from_dict(MINIMAL_RAW)
        assert cfg.global_tags["region"] == "us-east-1"


class TestLoadConfigFromDict:
    def test_pipeline_count(self):
        cfg = load_config_from_dict(MINIMAL_RAW)
        assert len(cfg.pipelines) == 2

    def test_pipeline_fields(self):
        cfg = load_config_from_dict(MINIMAL_RAW)
        hourly = cfg.get_pipeline("etl_hourly")
        assert hourly.interval_seconds == 3600
        assert hourly.min_samples == 5
        assert hourly.tags == {"env": "prod"}
        assert len(hourly.alert_rules) == 1

    def test_empty_config(self):
        cfg = load_config_from_dict({})
        assert cfg.pipelines == []
        assert cfg.global_tags == {}


class TestLoadConfigFromFile:
    def test_load_valid_file(self, tmp_path: Path):
        cfg_file = tmp_path / "watch.json"
        cfg_file.write_text(json.dumps(MINIMAL_RAW), encoding="utf-8")
        cfg = load_config(cfg_file)
        assert len(cfg.pipelines) == 2

    def test_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "missing.json")

    def test_string_path_accepted(self, tmp_path: Path):
        cfg_file = tmp_path / "watch.json"
        cfg_file.write_text(json.dumps({"pipelines": []}), encoding="utf-8")
        cfg = load_config(str(cfg_file))
        assert cfg.pipelines == []
