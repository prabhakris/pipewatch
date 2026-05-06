"""Configuration loader for pipewatch pipelines and alert rules."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PipelineConfig:
    name: str
    interval_seconds: int = 60
    min_samples: int = 10
    alert_rules: list[dict[str, Any]] = field(default_factory=list)
    notifiers: list[dict[str, Any]] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "interval_seconds": self.interval_seconds,
            "min_samples": self.min_samples,
            "alert_rules": self.alert_rules,
            "notifiers": self.notifiers,
            "tags": self.tags,
        }


@dataclass
class WatchConfig:
    pipelines: list[PipelineConfig] = field(default_factory=list)
    global_tags: dict[str, str] = field(default_factory=dict)

    def get_pipeline(self, name: str) -> PipelineConfig | None:
        for p in self.pipelines:
            if p.name == name:
                return p
        return None


def _parse_pipeline(raw: dict[str, Any]) -> PipelineConfig:
    return PipelineConfig(
        name=raw["name"],
        interval_seconds=int(raw.get("interval_seconds", 60)),
        min_samples=int(raw.get("min_samples", 10)),
        alert_rules=raw.get("alert_rules", []),
        notifiers=raw.get("notifiers", []),
        tags=raw.get("tags", {}),
    )


def load_config(path: str | Path) -> WatchConfig:
    """Load a WatchConfig from a JSON file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)
    pipelines = [_parse_pipeline(p) for p in raw.get("pipelines", [])]
    return WatchConfig(
        pipelines=pipelines,
        global_tags=raw.get("global_tags", {}),
    )


def load_config_from_dict(raw: dict[str, Any]) -> WatchConfig:
    """Load a WatchConfig from an already-parsed dict (useful in tests)."""
    pipelines = [_parse_pipeline(p) for p in raw.get("pipelines", [])]
    return WatchConfig(
        pipelines=pipelines,
        global_tags=raw.get("global_tags", {}),
    )
